"""
policy_loader.py
Responsible for loading and validating policies from a JSON file.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"allow", "sanitize", "escalate", "block"}


def load_policies(filepath: str) -> dict[str, Any]:
    """
    Load and validate policies from a JSON file.
    Returns a dict with:
      - 'policies': list of valid policy dicts
      - 'default_action': fallback action string
    """
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Policy file not found: {filepath}")
        return {"policies": [], "default_action": "block"}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in policy file: {e}")
        return {"policies": [], "default_action": "block"}

    raw_policies = data.get("policies", [])
    default_action = data.get("default_action", "block")

    # Validate default action
    if default_action not in VALID_ACTIONS:
        logger.warning(f"Invalid default_action '{default_action}', falling back to 'block'")
        default_action = "block"

    valid_policies = []
    for i, policy in enumerate(raw_policies):
        validated = _validate_policy(policy, index=i)
        if validated:
            valid_policies.append(validated)

    logger.info(f"Loaded {len(valid_policies)} valid policies. Default action: '{default_action}'")
    return {"policies": valid_policies, "default_action": default_action}


def _validate_policy(policy: Any, index: int) -> dict | None:
    """
    Validate a single policy entry.
    Returns the policy dict if valid, None otherwise.
    """
    if not isinstance(policy, dict):
        logger.warning(f"Policy at index {index} is not a dict — skipped.")
        return None

    policy_id = policy.get("id")
    risk = policy.get("risk")
    allowed_actions = policy.get("allowed_actions")
    min_confidence = policy.get("min_confidence")

    if not policy_id or not isinstance(policy_id, str):
        logger.warning(f"Policy at index {index} missing or invalid 'id' — skipped.")
        return None

    if not risk or not isinstance(risk, str):
        logger.warning(f"Policy '{policy_id}' missing or invalid 'risk' — skipped.")
        return None

    if not isinstance(allowed_actions, list) or len(allowed_actions) == 0:
        logger.warning(f"Policy '{policy_id}' missing or empty 'allowed_actions' — skipped.")
        return None

    # Filter out any invalid action names
    clean_actions = [a for a in allowed_actions if isinstance(a, str) and a in VALID_ACTIONS]
    if not clean_actions:
        logger.warning(f"Policy '{policy_id}' has no valid actions after filtering — skipped.")
        return None

    if min_confidence is None or not isinstance(min_confidence, (int, float)):
        logger.warning(f"Policy '{policy_id}' missing or invalid 'min_confidence' — defaulting to 0.0.")
        min_confidence = 0.0

    min_confidence = float(min_confidence)
    if not (0.0 <= min_confidence <= 1.0):
        logger.warning(f"Policy '{policy_id}' confidence {min_confidence} out of range — clamping to [0,1].")
        min_confidence = max(0.0, min(1.0, min_confidence))

    return {
        "id": policy_id,
        "risk": risk.lower().strip(),
        "allowed_actions": clean_actions,
        "min_confidence": min_confidence,
    }
