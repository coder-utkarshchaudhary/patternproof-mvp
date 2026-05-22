"""Dark pattern taxonomy for Pattern Proof.

Grounds detection in the India CCPA 2023 *Guidelines for Prevention and
Regulation of Dark Patterns* (13 specified patterns) for DPDP-compliance
certification, mapped onto the broader Mathur et al. categories.

- ``DPCategory`` — high-level Mathur category (used for grouping/scoring).
- ``DPType``     — granular detection type (YOLO classes + semantic types).
- ``CCPAPattern``— the 13 officially named patterns (the certification axis).
- ``TYPE_TO_CCPA`` maps each granular type to its CCPA pattern.

Stored as plain text in Postgres (validated here) so the taxonomy can grow
without enum migrations.
"""

from enum import Enum

class AuditStatus(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    CRAWLING = "crawling"
    ANALYZING = "analyzing"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DPCategory(str, Enum):
    SNEAKING = "sneaking"
    URGENCY = "urgency"
    MISDIRECTION = "misdirection"
    SOCIAL_PROOF = "social_proof"
    SCARCITY = "scarcity"
    OBSTRUCTION = "obstruction"
    FORCED_ACTION = "forced_action"


class CCPAPattern(str, Enum):
    """The 13 dark patterns named in the CCPA 2023 guidelines."""

    FALSE_URGENCY = "false_urgency"
    BASKET_SNEAKING = "basket_sneaking"
    CONFIRM_SHAMING = "confirm_shaming"
    FORCED_ACTION = "forced_action"
    SUBSCRIPTION_TRAP = "subscription_trap"
    INTERFACE_INTERFERENCE = "interface_interference"
    BAIT_AND_SWITCH = "bait_and_switch"
    DRIP_PRICING = "drip_pricing"
    DISGUISED_ADVERTISEMENT = "disguised_advertisement"
    NAGGING = "nagging"
    TRICK_QUESTION = "trick_question"
    SAAS_BILLING = "saas_billing"
    ROGUE_MALWARE = "rogue_malware"


class DPType(str, Enum):
    """Granular detection types produced by the visual + semantic detectors."""

    # Urgency / scarcity
    COUNTDOWN_TIMER = "countdown_timer"
    LIMITED_TIME_MESSAGE = "limited_time_message"
    LOW_STOCK_MESSAGE = "low_stock_message"
    HIGH_DEMAND_MESSAGE = "high_demand_message"
    # Sneaking / pricing
    HIDDEN_COSTS = "hidden_costs"
    DRIP_PRICING = "drip_pricing"
    BASKET_SNEAKING = "basket_sneaking"
    HIDDEN_SUBSCRIPTION = "hidden_subscription"
    BAIT_AND_SWITCH = "bait_and_switch"
    # Misdirection / interface
    CONFIRMSHAMING = "confirmshaming"
    VISUAL_INTERFERENCE = "visual_interference"
    TRICK_QUESTION = "trick_question"
    DISGUISED_AD = "disguised_ad"
    NAGGING = "nagging"
    # Forced action
    PRESELECTION = "preselection"
    FORCED_ENROLLMENT = "forced_enrollment"
    # Social proof
    FAKE_ACTIVITY = "fake_activity"
    FAKE_TESTIMONIAL = "fake_testimonial"
    # Obstruction
    HARD_TO_CANCEL = "hard_to_cancel"


# Granular type → high-level Mathur category
TYPE_TO_CATEGORY: dict[DPType, DPCategory] = {
    DPType.COUNTDOWN_TIMER: DPCategory.URGENCY,
    DPType.LIMITED_TIME_MESSAGE: DPCategory.URGENCY,
    DPType.LOW_STOCK_MESSAGE: DPCategory.SCARCITY,
    DPType.HIGH_DEMAND_MESSAGE: DPCategory.SCARCITY,
    DPType.HIDDEN_COSTS: DPCategory.SNEAKING,
    DPType.DRIP_PRICING: DPCategory.SNEAKING,
    DPType.BASKET_SNEAKING: DPCategory.SNEAKING,
    DPType.HIDDEN_SUBSCRIPTION: DPCategory.SNEAKING,
    DPType.BAIT_AND_SWITCH: DPCategory.SNEAKING,
    DPType.CONFIRMSHAMING: DPCategory.MISDIRECTION,
    DPType.VISUAL_INTERFERENCE: DPCategory.MISDIRECTION,
    DPType.TRICK_QUESTION: DPCategory.MISDIRECTION,
    DPType.DISGUISED_AD: DPCategory.MISDIRECTION,
    DPType.NAGGING: DPCategory.MISDIRECTION,
    DPType.PRESELECTION: DPCategory.FORCED_ACTION,
    DPType.FORCED_ENROLLMENT: DPCategory.FORCED_ACTION,
    DPType.FAKE_ACTIVITY: DPCategory.SOCIAL_PROOF,
    DPType.FAKE_TESTIMONIAL: DPCategory.SOCIAL_PROOF,
    DPType.HARD_TO_CANCEL: DPCategory.OBSTRUCTION,
}

# Granular type → CCPA 2023 named pattern (the certification axis)
TYPE_TO_CCPA: dict[DPType, CCPAPattern] = {
    DPType.COUNTDOWN_TIMER: CCPAPattern.FALSE_URGENCY,
    DPType.LIMITED_TIME_MESSAGE: CCPAPattern.FALSE_URGENCY,
    DPType.LOW_STOCK_MESSAGE: CCPAPattern.FALSE_URGENCY,
    DPType.HIGH_DEMAND_MESSAGE: CCPAPattern.FALSE_URGENCY,
    DPType.HIDDEN_COSTS: CCPAPattern.DRIP_PRICING,
    DPType.DRIP_PRICING: CCPAPattern.DRIP_PRICING,
    DPType.BASKET_SNEAKING: CCPAPattern.BASKET_SNEAKING,
    DPType.HIDDEN_SUBSCRIPTION: CCPAPattern.SUBSCRIPTION_TRAP,
    DPType.BAIT_AND_SWITCH: CCPAPattern.BAIT_AND_SWITCH,
    DPType.CONFIRMSHAMING: CCPAPattern.CONFIRM_SHAMING,
    DPType.VISUAL_INTERFERENCE: CCPAPattern.INTERFACE_INTERFERENCE,
    DPType.TRICK_QUESTION: CCPAPattern.TRICK_QUESTION,
    DPType.DISGUISED_AD: CCPAPattern.DISGUISED_ADVERTISEMENT,
    DPType.NAGGING: CCPAPattern.NAGGING,
    DPType.PRESELECTION: CCPAPattern.FORCED_ACTION,
    DPType.FORCED_ENROLLMENT: CCPAPattern.FORCED_ACTION,
    DPType.FAKE_ACTIVITY: CCPAPattern.FALSE_URGENCY,
    DPType.FAKE_TESTIMONIAL: CCPAPattern.DISGUISED_ADVERTISEMENT,
    DPType.HARD_TO_CANCEL: CCPAPattern.SUBSCRIPTION_TRAP,
}


def category_for(dp_type: str) -> str:
    """Best-effort map a granular type string to a Mathur category string."""
    try:
        return TYPE_TO_CATEGORY[DPType(dp_type)].value
    except (ValueError, KeyError):
        return DPCategory.MISDIRECTION.value


def ccpa_for(dp_type: str) -> str | None:
    """Map a granular type string to its CCPA pattern string, if known."""
    try:
        return TYPE_TO_CCPA[DPType(dp_type)].value
    except (ValueError, KeyError):
        return None
