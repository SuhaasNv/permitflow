"""The site visit checklist template (US-060, FR-036): static in code and versioned like the form
schema. Seventeen items in five sections, grounded in the Singapore Food Agency's public Food Shop
pre-licensing self-checklist (https://www.sfa.gov.sg/docs/default-source/default-document-library/self-checklist_foodshop.pdf).
It is not an SFA document and the licence in this product is fictional; a configurable checklist is a
form builder by another name and stays deferred (SCOPE.md assumption 21)."""

from dataclasses import dataclass

CHECKLIST_VERSION = 1

DESCRIPTION = (
    "Seventeen items in five sections, following the Singapore Food Agency's public Food Shop "
    "pre-licensing self-checklist. This template is PermitFlow's own reading of it, not an SFA document."
)


@dataclass(frozen=True)
class ChecklistItemDef:
    key: str
    section: str
    title: str
    guidance: str
    applicable_by_default: bool = True


@dataclass(frozen=True)
class ChecklistSectionDef:
    key: str
    title: str
    items: tuple[ChecklistItemDef, ...]


def _s(
    key: str, title: str, *items: tuple[str, str, str] | tuple[str, str, str, bool]
) -> ChecklistSectionDef:
    return ChecklistSectionDef(
        key=key,
        title=title,
        items=tuple(ChecklistItemDef(i[0], key, i[1], i[2], i[3] if len(i) > 3 else True) for i in items),
    )


SECTIONS: tuple[ChecklistSectionDef, ...] = (
    _s(
        "premises",
        "Premises",
        (
            "layout_matches_plan",
            "Layout matches the submitted floor plan",
            "Kitchen area at least 10 m² excluding the servery",
        ),
        ("floor_trap_graded", "Floor trap in the food preparation area", "Kitchen floor graded to the trap"),
        ("coved_edges", "Edge between wall and floor coved", "Preparation and servery areas"),
        (
            "no_drain_hazards",
            "No manhole, inspection chamber, waste sump, grease trap or overhead waste pipe in food areas",
            "Where food is prepared, stored or served",
        ),
        (
            "walls_impervious",
            "Walls lined with impervious material to at least 1.5 m",
            "Preparation and servery areas",
        ),
    ),
    _s(
        "kitchen",
        "Kitchen",
        ("sink_provided", "At least one sink in the food preparation area", "More for a large kitchen"),
        (
            "handwash_basin",
            "Wash-hand basin with soap for workers",
            "Separate taps if a double-bowl sink is used",
        ),
        (
            "exhaust_air_cleaning",
            "Cooking fumes extracted, treated and exhausted away from neighbours",
            "Air-cleaning system fitted",
        ),
        ("make_up_air", "Sufficient make-up air; negative pressure under the hood", ""),
        ("ducting", "Air ducts non-combustible, smooth, easy to clean, with inspection openings", ""),
    ),
    _s(
        "storage",
        "Storage",
        (
            "separate_storage",
            "Separate, pest-proof storage for belongings, cleaning materials, ingredients, cutlery "
            "and packaging",
            "",
        ),
        (
            "chiller_temperature",
            "Temperature gauge on every refrigerator and chiller",
            "Chillers at or below 4 °C, freezers at or below minus 18 °C",
        ),
    ),
    _s(
        "upkeep",
        "Upkeep",
        (
            "pest_control_contract",
            "Signed pest control contract on the premises",
            "Rodents, cockroaches and flies, at least monthly",
        ),
        ("cleaning_schedule", "Detailed cleaning schedule on the premises", ""),
        ("refuse_handling", "Covered refuse bins; refuse area clean and away from food areas", ""),
    ),
    _s(
        "people",
        "People",
        (
            "food_handlers_certified",
            "Every food handler holds Food Safety Course Level 1",
            "Refresher if attained more than five years ago",
        ),
        (
            "food_hygiene_officer",
            "Food Safety Course Level 3 holder appointed",
            "Only where the kitchen exceeds 16 m² or the shop spans two or more units",
            False,
        ),
    ),
)

ITEMS: tuple[ChecklistItemDef, ...] = tuple(i for s in SECTIONS for i in s.items)
ITEM_KEYS: tuple[str, ...] = tuple(i.key for i in ITEMS)
ITEM_BY_KEY: dict[str, ChecklistItemDef] = {i.key: i for i in ITEMS}
POSITION: dict[str, int] = {k: n for n, k in enumerate(ITEM_KEYS, start=1)}
MAX_COMMENT = 2000
