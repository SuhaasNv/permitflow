"""What each automatic check cost and who ran it (US-100).

Recording: `record_usage` adds the `ai_usage` row to the session that stores the run's result, so the row
and the result commit together or not at all (inline and worker alike). `publish` runs after that commit:
the Prometheus counters and, when the administrator switched it on, the Telegram line; neither can fail a
check. Reading: the administrator's filtered page with totals and today's numbers against the daily cap,
and the same rows as a streamed, formula-safe CSV.

A run that never reached the provider (over a quota, the AI paused, unreadable file, provider not
configured) still gets its row, with zero tokens, zero cost and its outcome. Cost is
`tokens x the price of the model at the time the result was stored`; a model with no price row costs 0 and
is logged, so a missing price shows up as a warning, not a failed check.
"""

import csv
import io
import logging
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import metrics
from app.core.errors import BadRequest
from app.core.settings import get_settings
from app.domain.admin import singapore_day_window
from app.domain.ai_usage import (
    CSV_COLUMNS,
    DOCUMENT_TYPE_LABELS,
    OUTCOME_LABELS,
    bounded_label,
    check_message,
    cost_usd,
    csv_cell,
    pseudonym,
)
from app.domain.site_visit import today_in_singapore
from app.infra import notifier
from app.infra.db import session_factory
from app.models import AiUsage, Document, VerificationRun
from app.models.enums import VerificationStatus
from app.repositories.ai_usage import AiUsageRepository, UsageFilters, UsageRow, UsageTotals
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository
from app.schemas.ai_usage import AiUsageOut, AiUsageRowOut, AiUsageTodayOut, AiUsageTotalsOut
from app.services.admin_feed import decode_cursor, encode_cursor
from app.services.platform_settings import live
from app.services.quotas import NOT_COUNTED_REASONS

logger = logging.getLogger("permitflow.ai_usage")

MAX_LIMIT = 100
# The export is bounded: this many rows, each statement within this time.
CSV_MAX_ROWS = 100_000
CSV_STATEMENT_TIMEOUT = "60s"
CSV_CUT_NOTICE = (
    "Export cut at {rows} rows. "
    "Narrow it with from, to, user_id, application_id or reference and export again."
)


def record_usage(
    db: Session,
    *,
    run: VerificationRun,
    doc: Document,
    outcome: VerificationStatus,
    provider: str,
    model: str | None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: int = 0,
) -> AiUsage:
    """Add the usage row of a run to `db`; the caller commits it with the run's result. A run has one row:
    when an earlier attempt (a scan hold that was queued again) already wrote it, that row takes the latest
    outcome, provider, model, latency and price, and the tokens and cost of this attempt are added to what
    it holds, so nothing billed earlier is lost. The value returned is always this attempt's own numbers
    (for `publish`, so the counters never count earlier tokens twice); on a repeat it is not stored."""
    repo = AiUsageRepository(db)
    now = datetime.now(UTC)
    # The price in force when the check ran: when it started, or when it was created if it never started.
    ran_at = run.started_at or run.created_at or now
    cost = Decimal(0)
    price_id: uuid.UUID | None = None
    if model and (input_tokens or output_tokens):
        price = repo.price_at(model, ran_at)
        if price is None:
            logger.warning("ai_price_missing", extra={"extra_fields": {"model": model}})
        else:
            cost = cost_usd(input_tokens, output_tokens, price.input_per_million, price.output_per_million)
            price_id = price.id
    attempt = AiUsage(
        run_id=run.id,
        document_id=run.document_id,
        application_id=doc.application_id,
        user_id=run.requested_by,
        document_type=doc.document_type.value,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
        price_id=price_id,
        latency_ms=latency_ms,
        outcome=outcome.value,
        created_at=now,
    )
    row = repo.for_run(run.id)
    if row is None:
        return repo.add(attempt)
    row.provider, row.model, row.latency_ms, row.outcome = provider, model, latency_ms, outcome.value
    row.price_id = price_id or row.price_id
    row.input_tokens += input_tokens
    row.output_tokens += output_tokens
    row.cost_usd += cost
    return attempt


def record_refused(db: Session, run: VerificationRun, doc: Document) -> AiUsage | None:
    """A run stored already finished at creation (over a quota, or the AI paused): it never reaches the
    provider, so it has a row of zeros and its outcome. A pending run is recorded when its result is. The
    caller commits, then calls `publish` with the row: nothing is counted for a rolled-back transaction."""
    if run.status == VerificationStatus.PENDING:
        return None
    return record_usage(db, run=run, doc=doc, outcome=run.status, provider=run.provider, model=None)


def record_ended_runs(db: Session, run_ids: list[uuid.UUID]) -> list[AiUsage]:
    """Rows for runs ended by the system without a result (dead, interrupted): no tokens are known. A run
    that already has its row is skipped, so a sweep can never trip the unique key and abort the reaper."""
    rows: list[AiUsage] = []
    done = AiUsageRepository(db).recorded(run_ids)
    for run_id in (i for i in run_ids if i not in done):
        run = db.get(VerificationRun, run_id)
        doc = db.get(Document, run.document_id) if run else None
        if run is None or doc is None:
            continue
        rows.append(
            record_usage(
                db,
                run=run,
                doc=doc,
                outcome=run.status,
                provider=run.provider,
                model=run.model,
                latency_ms=run.latency_ms or 0,
            )
        )
    return rows


def publish(row: AiUsage, reference_no: str | None, *, announce: bool) -> None:
    """After the commit: the counters, then the Telegram line when `announce` is set, the switch is on and
    the check reached a provider. A check that never did (refused, paused, unreadable file, no provider
    configured, ended by the system) gets no line, wherever it stopped. Labels come from the closed
    vocabularies; an id or a free-form string never reaches a metric."""
    doc_type = bounded_label(row.document_type, DOCUMENT_TYPE_LABELS)
    outcome = bounded_label(row.outcome, OUTCOME_LABELS)
    metrics.AI_CHECKS.labels(doc_type, outcome).inc()
    metrics.AI_TOKENS.labels(doc_type, outcome, "input").inc(row.input_tokens)
    metrics.AI_TOKENS.labels(doc_type, outcome, "output").inc(row.output_tokens)
    metrics.AI_COST.labels(doc_type, outcome).inc(float(row.cost_usd))
    if not announce or row.provider == "none":
        return
    try:
        if live().bool_value("telegram_per_check_messages"):
            notifier.notify(
                check_message(
                    document_type=doc_type,
                    outcome=outcome,
                    cost=row.cost_usd,
                    latency_ms=row.latency_ms,
                    reference_no=reference_no,
                )
            )
    except Exception:  # noqa: BLE001 - an announcement never fails a check that is already committed
        logger.exception("ai_usage_announce_failed")


def count_unrecorded(tokens: tuple[int, int]) -> None:
    """Tokens billed for a result that was dropped (the lease changed hands, the draft was deleted): no row
    holds them, so they are counted here and the ledger's undercount can be seen."""
    metrics.AI_UNRECORDED_TOKENS.labels("input").inc(tokens[0])
    metrics.AI_UNRECORDED_TOKENS.labels("output").inc(tokens[1])


def trace_ids(user_id: uuid.UUID | None, application_id: uuid.UUID) -> dict[str, str]:
    """What LangSmith may know about who and which case: keyed hashes, never an id or an email. Keyed with
    the server secret, so only this server can tell whose trace it is."""
    secret = get_settings().jwt_secret
    ids = {"application_hash": pseudonym(secret, "application", application_id)}
    if user_id is not None:
        ids["user_pseudonym"] = pseudonym(secret, "user", user_id)
    return ids


# ---------- the administrator's reads ----------


def filters_for(
    *,
    user_id: uuid.UUID | None,
    application_id: uuid.UUID | None,
    day_from: date | None,
    day_to: date | None,
    reference: str | None = None,
) -> UsageFilters:
    """Days are Singapore calendar days, both ends included (the same day as the admin overview)."""
    if day_from and day_to and day_from > day_to:
        raise BadRequest("The start day is after the end day.", details={"reason": "bad_range"})
    try:  # the first and last days the calendar has do not fit in UTC with the offset applied
        since = singapore_day_window(day_from)[0] if day_from else None
        until = singapore_day_window(day_to)[1] if day_to else None
    except (OverflowError, ValueError) as exc:
        raise BadRequest("That day is outside the supported range.", details={"reason": "bad_range"}) from exc
    return UsageFilters(
        user_id=user_id,
        application_id=application_id,
        reference=reference or None,
        since=since,
        until=until,
    )


def _row_out(r: UsageRow) -> AiUsageRowOut:
    u = r.usage
    return AiUsageRowOut(
        id=u.id,
        created_at=u.created_at,
        run_id=u.run_id,
        document_id=u.document_id,
        application_id=u.application_id,
        reference_no=r.reference_no,
        business_name=r.business_name or None,
        user_id=u.user_id,
        user_name=r.user_name,
        document_type=u.document_type,
        provider=u.provider,
        model=u.model,
        input_tokens=u.input_tokens,
        output_tokens=u.output_tokens,
        cost_usd=u.cost_usd,
        latency_ms=u.latency_ms,
        outcome=u.outcome,
    )


def _totals_out(t: UsageTotals) -> AiUsageTotalsOut:
    return AiUsageTotalsOut(
        runs=t.runs,
        input_tokens=t.input_tokens,
        output_tokens=t.output_tokens,
        cost_usd=t.cost_usd,
        avg_latency_ms=t.avg_latency_ms,
    )


class AiUsageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AiUsageRepository(db)

    def page(self, f: UsageFilters, *, limit: int = 50, before: str | None = None) -> AiUsageOut:
        limit = max(1, min(limit, MAX_LIMIT))
        cursor = decode_cursor(before) if before else None
        rows = self.repo.page(f, limit=limit + 1, before=cursor)  # one past the page: is there more?
        more = len(rows) > limit
        rows = rows[:limit]
        last = rows[-1].usage if rows else None
        return AiUsageOut(
            items=[_row_out(r) for r in rows],
            next_cursor=encode_cursor(last.created_at, last.id) if more and last is not None else None,
            totals=_totals_out(self.repo.totals(f)),
            today=self._today(),
        )

    def _today(self) -> AiUsageTodayOut:
        """The Singapore day so far, with the checks that count toward the daily cap (`ai_runs_per_day`,
        which the quota itself counts over a rolling 24 hours)."""
        start, end = singapore_day_window(today_in_singapore())
        totals = self.repo.totals(UsageFilters(since=start, until=end))
        counted = DocumentRepository(self.db).count_runs_since(start, exclude_reasons=NOT_COUNTED_REASONS)
        return AiUsageTodayOut(
            runs=counted,
            input_tokens=totals.input_tokens,
            output_tokens=totals.output_tokens,
            cost_usd=totals.cost_usd,
            daily_cap=live().int_value("ai_runs_per_day"),
        )


def csv_stream(f: UsageFilters, actor_id: uuid.UUID) -> Iterator[str]:
    """The export, one CSV line at a time, from a session of its own: the streaming response outlives the
    request's session. Every cell is formula-safe. At most `CSV_MAX_ROWS` rows: when more match, the file ends
    with a line saying it was cut and how to narrow it. Every statement is capped at `CSV_STATEMENT_TIMEOUT`.
    The export is audited (`admin.ai_usage_exported`: the filters and the row count, no names), also when the
    reader goes away halfway."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")

    def line(cells: list[str]) -> str:
        writer.writerow(cells)
        text = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
        return text

    yield line(list(CSV_COLUMNS))
    rows = 0
    cut = False
    with session_factory()() as db:
        repo = AiUsageRepository(db)
        repo.limit_statement_time(CSV_STATEMENT_TIMEOUT)
        try:
            for r in repo.stream(f, limit=CSV_MAX_ROWS + 1):
                if rows == CSV_MAX_ROWS:
                    cut = True
                    break
                rows += 1
                u = r.usage
                yield line(
                    [
                        csv_cell(c)
                        for c in (
                            u.created_at.astimezone(UTC).isoformat(),
                            r.reference_no,
                            r.business_name,
                            u.application_id,
                            u.document_id,
                            u.run_id,
                            u.user_id,
                            r.user_name,
                            u.document_type,
                            u.provider,
                            u.model,
                            u.input_tokens,
                            u.output_tokens,
                            f"{u.cost_usd:f}",
                            u.latency_ms,
                            u.outcome,
                        )
                    ]
                )
            if cut:
                yield line([CSV_CUT_NOTICE.format(rows=CSV_MAX_ROWS)])
        finally:
            AuditRepository(db).record(
                application_id=None,
                actor_id=actor_id,
                event_type="admin.ai_usage_exported",
                payload={
                    "user_id": str(f.user_id) if f.user_id else None,
                    "application_id": str(f.application_id) if f.application_id else None,
                    "reference": f.reference,
                    "since": f.since.isoformat() if f.since else None,
                    "until": f.until.isoformat() if f.until else None,
                    "rows": rows,
                    "cut": cut,
                },
            )
            db.commit()
