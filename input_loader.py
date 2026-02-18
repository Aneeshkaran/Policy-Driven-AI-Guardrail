"""
input_loader.py
Responsible for loading and validating AI-generated inputs from a JSON file.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def load_inputs(filepath: str) -> list[dict]:
    """
    Load and validate AI response inputs from a JSON file.
    Returns a list of valid input dicts.
    """
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Input file not found: {filepath}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in input file: {e}")
        return []

    if not isinstance(data, list):
        logger.error("Input file must contain a JSON array at the top level.")
        return []

    valid_inputs = []
    for i, item in enumerate(data):
        validated = _validate_input(item, index=i)
        if validated:
            valid_inputs.append(validated)

    logger.info(f"Loaded {len(valid_inputs)} valid inputs from '{filepath}'")
    return valid_inputs


def _validate_input(item: Any, index: int) -> dict | None:
    """
    Validate a single input entry.
    Returns the input dict if valid, None otherwise.
    """
    if not isinstance(item, dict):
        logger.warning(f"Input at index {index} is not a dict — skipped.")
        return None

    input_id = item.get("id")
    risk = item.get("risk")
    output = item.get("output")
    confidence = item.get("confidence")

    if not input_id or not isinstance(input_id, str):
        logger.warning(f"Input at index {index} missing or invalid 'id' — skipped.")
        return None

    if not risk or not isinstance(risk, str):
        logger.warning(f"Input '{input_id}' missing or invalid 'risk' — defaulting to 'unknown'.")
        risk = "unknown"

    if output is None or not isinstance(output, str):
        logger.warning(f"Input '{input_id}' missing or invalid 'output' — defaulting to empty string.")
        output = ""

    if confidence is None or not isinstance(confidence, (int, float)):
        logger.warning(f"Input '{input_id}' missing or invalid 'confidence' — defaulting to 0.0.")
        confidence = 0.0

    confidence = float(confidence)
    if not (0.0 <= confidence <= 1.0):
        logger.warning(f"Input '{input_id}' confidence {confidence} out of range — clamping to [0,1].")
        confidence = max(0.0, min(1.0, confidence))

    return {
        "id": input_id,
        "risk": risk.lower().strip(),
        "output": output,
        "confidence": confidence,
    }
