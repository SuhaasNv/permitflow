#!/usr/bin/env python3
"""Release guard: a release tag must be its last release candidate with the label removed.

Usage: python3 scripts/release_guard.py <tag>      (from a checkout with full history and tags)

  vX.Y.Z-rc.N  passes when the five version files at that tag carry X.Y.Z-rc.N.
  vX.Y.Z       passes when the five version files carry X.Y.Z, a tag vX.Y.Z-rc.N exists, and between the
               highest such candidate and the release nothing shipped changed except the version lines.

The rules are written down in docs/09-operations/RELEASING.md. Standard library only. The pure parts
(tag parsing, version extraction, the shipped-path filter, the version-line diff check) take text and
return values, so scripts/test_release_guard.py tests them without git.
"""

from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass

VERSION_FILES = (
    "frontend/package.json",
    "frontend/package-lock.json",
    "backend/pyproject.toml",
    "backend/uv.lock",
    "backend/app/core/version.py",
)
SHIPPED_PREFIXES = ("backend/", "frontend/", "docker/")
SHIPPED_FILES = ("docker-compose.yml",)
BACKEND_PACKAGE = "permitflow-backend"

MAX_LISTED_PATHS = 25  # a long drift list is cut after this many; the count is still printed

# How many lines carry the version in each file (package-lock.json names it twice).
VERSION_LINES_PER_FILE = {"frontend/package-lock.json": 2}

TAG_RE = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-rc\.([1-9]\d*))?$")
APP_VERSION_RE = re.compile(r'^APP_VERSION\s*=\s*"([^"]+)"\s*$', re.MULTILINE)
VERSION_LINE_RE = re.compile(r'^\s*(?:"version"\s*:|version\s*=|APP_VERSION\s*=)')


@dataclass(frozen=True)
class Tag:
    major: int
    minor: int
    patch: int
    rc: int | None  # None for a release

    @property
    def base(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @property
    def semver(self) -> str:
        return self.base if self.rc is None else f"{self.base}-rc.{self.rc}"

    @property
    def name(self) -> str:
        return f"v{self.semver}"


def parse_tag(tag: str) -> Tag | None:
    """Parse vX.Y.Z or vX.Y.Z-rc.N; None for any other shape."""
    m = TAG_RE.match(tag)
    if not m:
        return None
    rc = int(m.group(4)) if m.group(4) else None
    return Tag(int(m.group(1)), int(m.group(2)), int(m.group(3)), rc)


def pep440(semver: str) -> str:
    """X.Y.Z-rc.N becomes X.Y.ZrcN (pyproject.toml and uv.lock); a release is unchanged."""
    return re.sub(r"-rc\.(\d+)$", r"rc\1", semver)


def expected_version(path: str, semver: str) -> str:
    return pep440(semver) if path in ("backend/pyproject.toml", "backend/uv.lock") else semver


def extract_versions(path: str, text: str) -> list[str]:
    """Every version the file declares for the application itself (two for package-lock.json)."""
    if path == "frontend/package.json":
        return [str(json.loads(text)["version"])]
    if path == "frontend/package-lock.json":
        data = json.loads(text)
        return [str(data["version"]), str(data["packages"][""]["version"])]
    if path == "backend/pyproject.toml":
        return [str(tomllib.loads(text)["project"]["version"])]
    if path == "backend/uv.lock":
        packages = tomllib.loads(text).get("package", [])
        return [str(p["version"]) for p in packages if p.get("name") == BACKEND_PACKAGE]
    if path == "backend/app/core/version.py":
        return APP_VERSION_RE.findall(text)
    raise ValueError(f"not a version file: {path}")


def is_shipped(path: str) -> bool:
    return path.startswith(SHIPPED_PREFIXES) or path in SHIPPED_FILES


def shipped_changes(changed_paths: list[str]) -> list[str]:
    """Shipped paths in a diff that are not one of the five version files."""
    return [p for p in changed_paths if is_shipped(p) and p not in VERSION_FILES]


def version_line_diff_problems(path: str, old_text: str, new_text: str, old: str, new: str) -> list[str]:
    """Empty when the only changed lines are the version lines going from `old` to `new`."""
    removed: list[str] = []
    added: list[str] = []
    for line in difflib.unified_diff(old_text.splitlines(), new_text.splitlines(), n=0, lineterm=""):
        if line.startswith(("---", "+++", "@@")):
            continue
        (removed if line[0] == "-" else added).append(line[1:])
    expected = VERSION_LINES_PER_FILE.get(path, 1)
    problems: list[str] = []
    if len(removed) != expected or len(added) != expected:
        problems.append(
            f"{path}: expected {expected} changed version line(s), found {len(removed)} removed and {len(added)} added"
        )
    for before, after in zip(removed, added, strict=False):
        if not (VERSION_LINE_RE.match(before) and VERSION_LINE_RE.match(after)):
            problems.append(f"{path}: changed line is not a version line: -{before.strip()} / +{after.strip()}")
        elif old not in before or before.replace(old, new) != after:
            problems.append(f"{path}: changed line is not {old} -> {new}: -{before.strip()} / +{after.strip()}")
    return problems


def version_problems(texts: dict[str, str | None], semver: str, label: str) -> list[str]:
    """Check the five files (path -> text, None when missing) all carry `semver`."""
    problems: list[str] = []
    for path in VERSION_FILES:
        text = texts.get(path)
        want = expected_version(path, semver)
        if text is None:
            problems.append(f"{label}: {path} is missing")
            continue
        try:
            found = extract_versions(path, text)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
            problems.append(f"{label}: cannot read the version in {path} ({exc!r})")
            continue
        if not found or any(v != want for v in found):
            problems.append(f"{label}: {path} carries {found or 'no version'}, expected {want}")
    return problems


def highest_candidate(tags: list[str], base: str) -> Tag | None:
    """The vX.Y.Z-rc.N tag with the highest N (numeric) among `tags` for the base version."""
    best: Tag | None = None
    for name in tags:
        t = parse_tag(name)
        if t is None or t.rc is None or t.base != base:
            continue
        if best is None or t.rc > (best.rc or 0):
            best = t
    return best


# --- git (not unit tested) ---------------------------------------------------------------------------


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def tag_exists(tag: str) -> bool:
    return git("rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}").returncode == 0


def file_at(tag: str, path: str) -> str | None:
    result = git("show", f"refs/tags/{tag}^{{commit}}:{path}")
    return result.stdout if result.returncode == 0 else None


def files_at(tag: str) -> dict[str, str | None]:
    return {p: file_at(tag, p) for p in VERSION_FILES}


def changed_paths(a: str, b: str) -> list[str]:
    result = git("diff", "--no-renames", "--name-only", f"refs/tags/{a}^{{commit}}", f"refs/tags/{b}^{{commit}}")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    return [line for line in result.stdout.splitlines() if line]


def check(tag_name: str) -> tuple[list[str], str]:
    """Return (problems, pass message)."""
    tag = parse_tag(tag_name)
    if tag is None:
        return [f"{tag_name}: tags are vX.Y.Z or vX.Y.Z-rc.N"], ""
    if not tag_exists(tag.name):
        return [f"{tag.name}: no such tag in this checkout (fetch with full history and tags)"], ""

    problems = version_problems(files_at(tag.name), tag.semver, tag.name)
    if tag.rc is not None:
        return problems, f"PASS {tag.name}: the five version files carry {tag.semver}"

    all_tags = git("tag", "--list", f"v{tag.base}-rc.*").stdout.split()
    candidate = highest_candidate(all_tags, tag.base)
    if candidate is None:
        problems.append(f"{tag.name}: no release candidate tag v{tag.base}-rc.N exists; cut one and test it first")
        return problems, ""

    rc_texts = files_at(candidate.name)
    problems += version_problems(rc_texts, candidate.semver, candidate.name)
    try:
        paths = changed_paths(candidate.name, tag.name)
    except RuntimeError as exc:
        return [*problems, f"git diff {candidate.name}..{tag.name} failed: {exc}"], ""
    drift = shipped_changes(paths)
    for path in drift[:MAX_LISTED_PATHS]:
        problems.append(f"{path}: shipped file differs between {candidate.name} and {tag.name}")
    if len(drift) > MAX_LISTED_PATHS:
        problems.append(
            f"and {len(drift) - MAX_LISTED_PATHS} more shipped files differ ({len(drift)} in all) "
            f"between {candidate.name} and {tag.name}"
        )
    release_texts = files_at(tag.name)
    for path in VERSION_FILES:
        old_text, new_text = rc_texts.get(path), release_texts.get(path)
        if old_text is None or new_text is None:
            continue  # already reported as missing
        problems += version_line_diff_problems(
            path, old_text, new_text, expected_version(path, candidate.semver), expected_version(path, tag.semver)
        )
    return problems, f"PASS {tag.name} is {candidate.name} with the label removed (compared against {candidate.name})"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 scripts/release_guard.py <tag>", file=sys.stderr)
        return 2
    problems, message = check(argv[1])
    if problems:
        for p in problems:
            print(f"FAIL {p}")
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
