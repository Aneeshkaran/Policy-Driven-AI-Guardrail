"""
engine.py
Orchestrates the full guardrail pipeline:
  load policies → load inputs → match → evaluate → resolve → write output
"""

import json
import logging
from typing import Any

from policy_loader import load_policies
from input_loader import load_inputs
from matcher import find_matching_policies, evaluate_policy
from resolver import resolve_decision

logger = logging.getLogger(__name__)


def run_engine(
    policies_path: str,
    inputs_path: str,
    output_path: str,
) -> list[dict]:
    """
    Run the guardrail engine end-to-end.

    Args:
        policies_path: Path to policies.json
        inputs_path:   Path to inputs.json
        output_path:   Path to write output.json

    Returns:
        List of decision dicts (also written to output_path).
    """
    # ── 1. Load policies ────────────────────────────────────────────────────
    policy_data = load_policies(policies_path)
    policies = policy_data["policies"]
    default_action = policy_data["default_action"]

    # ── 2. Load inputs ──────────────────────────────────────────────────────
    inputs = load_inputs(inputs_path)

    if not inputs:
        logger.warning("No valid inputs to process.")
        _write_output([], output_path)
        return []

    # ── 3. Process each input ───────────────────────────────────────────────
    results: list[dict] = []

    for item in inputs:
        # Match
        matched_policies = find_matching_policies(item, policies)

        # Evaluate each matched policy
        traces = [evaluate_policy(item, p) for p in matched_policies]

        # Resolve final decision
        decision = resolve_decision(item, traces, default_action)
        results.append(decision)

        logger.info(
            f"[{item['id']}] risk={item['risk']} conf={item['confidence']} "
            f"→ decision={decision['decision']} "
            f"policies={decision['applied_policies']}"
        )

    # ── 4. Write output ─────────────────────────────────────────────────────
    _write_output(results, output_path)
    logger.info(f"Output written to '{output_path}' ({len(results)} records).")

    return results


def _write_output(results: list[dict], path: str) -> None:
    """Write decision results to a JSON file."""
    try:
        with open(path, "w") as f:
            json.dump(results, f, indent=2)
    except OSError as e:
        logger.error(f"Failed to write output file '{path}': {e}")
