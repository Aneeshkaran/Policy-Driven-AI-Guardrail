"""
resolver.py
Responsible for resolving the final action from multiple policy evaluations.

Restriction order (most → least restrictive):
    block > escalate > sanitize > allow
"""

import logging

logger = logging.getLogger(__name__)

# Lower index = more restrictive
ACTION_PRIORITY: dict[str, int] = {
    "block": 0,
    "escalate": 1,
    "sanitize": 2,
    "allow": 3,
}

SAFE_FALLBACK_OUTPUT = (
    "This response cannot be shown. Please consult a qualified professional."
)

FINAL_OUTPUT_MAP = {
    "allow": None,          # use original output
    "sanitize": SAFE_FALLBACK_OUTPUT,
    "escalate": "Sent for human review.",
    "block": "[Output suppressed by guardrail policy.]",
}


def resolve_decision(
    input_item: dict,
    policy_traces: list[dict],
    default_action: str,
) -> dict:
    """
    Given all policy evaluation traces for one input, determine the single
    most restrictive final action and return a full decision record.

    Args:
        input_item:     The validated input dict.
        policy_traces:  List of trace dicts from matcher.evaluate_policy().
        default_action: Fallback action if no effective actions found.

    Returns:
        A decision dict ready for output.json.
    """
    applied_policy_ids = []
    candidate_actions: list[str] = []

    for trace in policy_traces:
        effective = trace.get("effective_actions", [])
        if effective:
            applied_policy_ids.append(trace["policy_id"])
            candidate_actions.extend(effective)

    # Build reason parts for transparency
    reason_parts = []

    if not policy_traces:
        # No policies matched this risk type at all
        final_action = default_action
        reason_parts.append(
            f"No policies found for risk type '{input_item['risk']}'; "
            f"default action '{default_action}' applied."
        )
    elif not candidate_actions:
        # Policies matched but none had their confidence threshold met
        final_action = default_action
        failed_summaries = [
            f"{t['policy_id']} requires confidence >= {t['confidence_required']} "
            f"(got {t['confidence_given']})"
            for t in policy_traces
        ]
        reason_parts.append(
            f"All matching policies failed confidence threshold: "
            + "; ".join(failed_summaries)
            + f". Default action '{default_action}' applied."
        )
    else:
        # Pick the most restrictive action across all effective actions
        final_action = _most_restrictive(candidate_actions)

        # Describe which policies contributed
        for trace in policy_traces:
            if trace["policy_id"] in applied_policy_ids:
                status = (
                    f"confidence {trace['confidence_given']} >= {trace['confidence_required']} ✓"
                )
                reason_parts.append(
                    f"Policy {trace['policy_id']}: {status}, "
                    f"actions={trace['effective_actions']}"
                )

        # Explain why other actions were overridden if multiple policies clashed
        unique_actions = set(candidate_actions)
        if len(unique_actions) > 1:
            reason_parts.append(
                f"Multiple actions found {sorted(unique_actions)}; "
                f"most restrictive '{final_action}' selected."
            )

    # Build the final output text
    final_output = _build_final_output(input_item["output"], final_action)

    return {
        "id": input_item["id"],
        "decision": final_action,
        "applied_policies": applied_policy_ids,
        "rule_trace": _build_rule_trace(policy_traces),
        "final_output": final_output,
        "reason": " | ".join(reason_parts),
    }


def _most_restrictive(actions: list[str]) -> str:
    """Return the most restrictive action from a list."""
    return min(actions, key=lambda a: ACTION_PRIORITY.get(a, 99))


def _build_final_output(original: str, action: str) -> str:
    """Map action to the appropriate output string."""
    mapped = FINAL_OUTPUT_MAP.get(action)
    if mapped is None:
        # action == "allow": show original
        return original
    return mapped


def _build_rule_trace(policy_traces: list[dict]) -> list[dict]:
    """
    Build an audit-friendly rule trace showing pass/fail for every matched policy.
    """
    trace_output = []
    for t in policy_traces:
        trace_output.append({
            "policy_id": t["policy_id"],
            "confidence_required": t["confidence_required"],
            "confidence_given": t["confidence_given"],
            "threshold_met": t["threshold_met"],
            "candidate_actions": t["candidate_actions"],
            "effective_actions": t["effective_actions"],
        })
    return trace_output
