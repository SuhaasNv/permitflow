"""AI usage and cost rules (US-100). Pure Python: money arithmetic, the closed label vocabularies for the
Prometheus labels, the pseudonyms sent to LangSmith, the Telegram line and the formula-safe CSV cell."""

import hashlib
import hmac
import uuid
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import DocumentType, VerificationStatus

MILLION = Decimal(1_000_000)
COST_PLACES = Decimal("0.00000001")  # the column holds eight decimals

# The only values a Prometheus label may take (never a user, an application or a free-form string). Anything
# else is counted as "other", so a new enum member or a bad caller cannot grow the series without bound.
DOCUMENT_TYPE_LABELS = frozenset(t.value for t in DocumentType)
OUTCOME_LABELS = frozenset(s.value for s in VerificationStatus)
OTHER = "other"


def bounded_label(value: str, allowed: Iterable[str]) -> str:
    return value if value in allowed else OTHER


def cost_usd(
    input_tokens: int, output_tokens: int, input_per_million: Decimal, output_per_million: Decimal
) -> Decimal:
    """What a run cost at a price (USD per million tokens), to eight decimals."""
    raw = (input_tokens * input_per_million + output_tokens * output_per_million) / MILLION
    return raw.quantize(COST_PLACES, rounding=ROUND_HALF_UP)


def pseudonym(secret: str, label: str, value: uuid.UUID | str) -> str:
    """A stable, non-reversible stand-in for an id: the first 16 hex characters of an HMAC-SHA256 keyed
    with a server secret. The same id always gives the same stand-in, so one person's traces group
    together in LangSmith, but neither the id nor the email can be recovered from it."""
    digest = hmac.new(secret.encode(), f"{label}:{value}".encode(), hashlib.sha256)
    return digest.hexdigest()[:16]


def check_message(
    *, document_type: str, outcome: str, cost: Decimal, latency_ms: int, reference_no: str | None
) -> str:
    """The Telegram line for one check. No name, email, filename or document content: the document type,
    the outcome, the cost, the time and the case reference (a number, not a person)."""
    kind = document_type.replace("_", " ")
    case = f" · case {reference_no}" if reference_no else ""
    result = outcome.replace("_", " ")
    return f"Document check: {kind} · {result} · USD {cost:.4f} · {latency_ms / 1000:.1f} s{case}"


# ---------- CSV ----------

CSV_COLUMNS = (
    "created_at",
    "reference_no",
    "application_id",
    "document_id",
    "run_id",
    "user_id",
    "user_name",
    "document_type",
    "provider",
    "model",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "latency_ms",
    "outcome",
)
_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def csv_cell(value: object) -> str:
    """A spreadsheet reads a cell that starts with = + - @ tab or CR as a formula. Such a text gets a
    single quote in front, which the spreadsheet hides and does not evaluate. Applied to every cell: a
    number we produced never starts with one of these, a person's name might."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_STARTS) else text
