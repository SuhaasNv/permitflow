# ADR-017: Every upload is scanned by ClamAV in quarantine before anyone can open it

Date: 10 October 2026. Story: US-099 (wave 3 of v0.5.0). Status: accepted, built behind a switch (`SCAN_MODE`, default `off` = today's behaviour); not switched on in any deployed environment. Related: ADR-015 (object storage; the quarantine is a key prefix on either backend), ADR-016 (the worker; the scan is the first step of a check), US-101 (the stored `scanner_fail_mode`), T4 in the threat model.

## Context

An uploaded file is checked for its extension, its magic bytes and its size (T4), and an image is re-written without metadata. Nothing looks inside a PDF, a text file or an image for malware, and an officer opens the file on a device that holds licensing records. A PDF can carry a script that runs when it is opened, a launch action, or an embedded executable. US-099 asks that a malicious file never reaches an officer's device, that the operator is told, that the team is alerted, and that a scanner that is down never lets a file through.

## Constraints

- A switch whose default is today's behaviour: with `SCAN_MODE=off` every existing test and flow is unchanged.
- No new application dependency. ClamAV is a service, spoken to over a socket.
- The scan runs before text extraction and before any model call (ADR-016: the worker's first step), so an infected file's text never reaches OpenAI.
- Fail closed, and tunable only in the safe direction (the stored `scanner_fail_mode` setting from US-101, whose "open" value is refused in production).
- Works on both storage backends and in both verification modes.

## Options considered

### A: scan on upload, synchronously, in the request
Simple: the file is clean or the upload fails. But a scan of a 10 MB file plus a cold ClamAV can hold a request for seconds, and an outage becomes an upload outage for documents, which can wait.

### B: scan in the verification step (inline or worker), with a quarantine prefix (chosen for documents)
The upload is stored under `quarantine/<key>` with `scan_state = scanning`. The first step of the check reads it, asks clamd, and either copies it to its normal key (`clean`) or leaves it where it is (`infected`). A downloader sees the state, not the key. An outage leaves the file `scanning` and the check `unavailable: scanner_unavailable`. Costs one copy of the file per upload and a state column.

### C: scan in the object store (bucket event, Lambda)
Not available on a Railway bucket and not on local disk.

### D: a sidecar that scans on a shared volume
Couples storage to one volume; breaks ADR-015.

## Decision

**B for documents, and A (inside the request) for clarification attachments.** An attachment has no queue and no check; it is a small file, at most three per answer, and the operator is looking at the screen. It is stored under `quarantine/`, scanned in the same request, released on a clean verdict, kept quarantined on an infected one (the row stays so the operator sees it and removes it; the request answers 422 `file_infected`), and refused with 503 `scanner_unavailable` with nothing kept when the scanner gives no verdict.

- **Switch.** `SCAN_MODE=off|enforce`, default `off`. `scan_state` is NULL for everything stored with the scan off or before it existed; NULL and `clean` are served, `scanning` and `infected` are not. Turning `enforce` on does not touch old files.
- **Client.** `infra/clamd.py`: the `zINSTREAM` command over TCP, 64 KiB chunks, a socket timeout (`CLAMD_TIMEOUT_SECONDS`, 30), standard library only. A refused connection, a timeout, an `ERROR` reply or an unexpected reply is a `ScannerError`; it is never read as clean.
- **States and codes.** Document and attachment `scan_state`: `scanning`, `clean`, `infected` (or null). An infected document ends its check `unreadable` with `error_reason = file_infected`, which the operator API already serves. A download of an infected file is 403 `file_infected` (operator message "This file was blocked by the security check. Upload a different copy."; officer and administrator "This file was blocked by the security check and cannot be opened."); of a file still `scanning` it is 409 `file_scanning`.
- **Fail closed, and what the stored setting means.** The scanner being down never marks a file clean, never sends it to the AI, never serves it. `scanner_fail_mode = closed` (the default): the check ends `unavailable: scanner_unavailable`, and in `worker` mode the reaper queues it again after 60 s, up to three claims; then it stays held until a person re-runs it, and Telegram says so. `open` (refused in production): the file is held in the same way but nothing retries it by itself. The old description of `open` ("lets it through") is replaced: no value serves an unscanned file, the setting chooses between automatic retry and waiting for a person.
- **PDF active content.** A PDF with `/OpenAction` or `/AA` together with `/JavaScript` or `/JS`, or with `/Launch`, or with `/EmbeddedFile(s)` gets `active_content = true` (names written with `#xx` escapes are decoded first). It is a flag the officer's case view serves; it does not block the file. Reason: these constructs are also in ordinary form PDFs and signed documents, and a block would refuse legitimate licensing paperwork; the control that stops the dangerous ones is the scan and the viewer's own settings. This is a byte scan, not a parser, so objects packed in compressed object streams are not seen; upgrade path: walk the objects with pypdf.
- **Infected: audit and alert.** Audit `document.infected` (or `clarification.attachment_infected`), a metric `permitflow_scans_total{result}`, and one Telegram message with the case reference and the scanner's signature name, never a file name, a person or a business.
- **ClamAV.** `clamav/clamav:1.5.4-debian` (multi-arch) as a Compose service with a health check, on the private network only (no published port). It needs about 1.5 GB of memory and a few minutes to load signatures.

## Consequences

- An upload costs one extra read and one copy (quarantine to normal key) in `enforce` mode, and the document's `stored_key` changes once, when it is released.
- A scanner outage holds documents (their checks wait) and refuses clarification attachments; applications can still be submitted (AI and scan results are advisory for submission; see the open point below).
- While the administrator has paused the AI, the worker claims nothing, so the scan waits too (the scan lives inside the run).
- Orphans under `quarantine/` are never served; a failed delete is logged and left.

## Open points (not built)

- Submission is not blocked by an infected or unscanned document; the officer sees the state and cannot open the file. Blocking submission is a product decision (it changes the operator's flow).
- A signature database that is hours old is the scanner's own staleness; `freshclam` runs inside the image. An alert on a stale database is not built.
- No rescan of `clean` files when signatures update.

## What would make us revisit this

- A bucket that can scan on write (then C).
- More than a few hundred uploads an hour (then a pool of clamd instances, or a scan queue separate from the AI queue so a pause does not hold scans).
- A requirement to block submission on an unscanned file.

## Links

US-099, US-098, US-101; `docs/06-security/THREAT_MODEL.md` T4; `docs/09-operations/OPERATIONS.md` (Virus scan).
