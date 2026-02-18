"""
matcher.py
Responsible for matching input entries against policies.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def find_matching_policies(input_item: dict, policies: list[dict]) -> list[dict]:
    """
    Return all policies whose risk type matches the input's risk type.
    Matching is case-insensitive (both are already lowercased by loaders).
    """
    input_risk = input_item.get("risk", "")
    matched = [p for p in policies if p.get("risk", "") == input_risk]
    logger.debug(f"Input '{input_item['id']}' (risk='{input_risk}'): matched {len(matched)} policies.")
    return matched


def evaluate_policy(input_item: dict, policy: dict) -> dict:
    """
    Evaluate a single policy against an input.
    Returns a trace dict describing what happened:
      - policy_id
      - confidence_required
      - confidence_given
      - threshold_met (bool)
      - candidate_actions: actions available if threshold is met
      - effective_actions: actions that actually apply (empty if threshold not met)
    """
    confidence = input_item.get("confidence", 0.0)
    min_confidence = policy.get("min_confidence", 0.0)
    threshold_met = confidence >= min_confidence
    allowed_actions = policy.get("allowed_actions", [])

    return {
        "policy_id": policy["id"],
        "confidence_required": min_confidence,
        "confidence_given": confidence,
        "threshold_met": threshold_met,
        "candidate_actions": allowed_actions,
        "effective_actions": allowed_actions if threshold_met else [],
    }
