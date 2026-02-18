"""
test_guardrail.py
Unit tests for the Policy-Driven AI Guardrail Engine.

Run with:  python -m pytest test_guardrail.py -v
"""

import unittest
import sys
import os

# Ensure engine modules are importable
sys.path.insert(0, os.path.dirname(__file__))

from policy_loader import load_policies, _validate_policy
from input_loader import load_inputs, _validate_input
from matcher import find_matching_policies, evaluate_policy
from resolver import resolve_decision, _most_restrictive


# ────────────────────────────────────────────────────────────────
# policy_loader tests
# ────────────────────────────────────────────────────────────────

class TestValidatePolicy(unittest.TestCase):
    def test_valid_policy(self):
        p = {"id": "P1", "risk": "medical", "allowed_actions": ["escalate"], "min_confidence": 0.9}
        result = _validate_policy(p, 0)
        assert result is not None
        assert result["id"] == "P1"
        assert result["risk"] == "medical"
        assert result["min_confidence"] == 0.9

    def test_missing_id(self):
        p = {"risk": "medical", "allowed_actions": ["escalate"], "min_confidence": 0.9}
        assert _validate_policy(p, 0) is None

    def test_missing_risk(self):
        p = {"id": "P1", "allowed_actions": ["escalate"], "min_confidence": 0.9}
        assert _validate_policy(p, 0) is None

    def test_empty_allowed_actions(self):
        p = {"id": "P1", "risk": "medical", "allowed_actions": [], "min_confidence": 0.9}
        assert _validate_policy(p, 0) is None

    def test_invalid_actions_filtered(self):
        p = {"id": "P1", "risk": "medical", "allowed_actions": ["escalate", "INVALID", "fly"], "min_confidence": 0.9}
        result = _validate_policy(p, 0)
        assert result is not None
        assert result["allowed_actions"] == ["escalate"]

    def test_all_invalid_actions_skips_policy(self):
        p = {"id": "P1", "risk": "medical", "allowed_actions": ["fly", "teleport"], "min_confidence": 0.9}
        assert _validate_policy(p, 0) is None

    def test_missing_confidence_defaults_to_zero(self):
        p = {"id": "P1", "risk": "medical", "allowed_actions": ["block"]}
        result = _validate_policy(p, 0)
        assert result is not None
        assert result["min_confidence"] == 0.0

    def test_confidence_clamped(self):
        p = {"id": "P1", "risk": "medical", "allowed_actions": ["block"], "min_confidence": 1.5}
        result = _validate_policy(p, 0)
        assert result["min_confidence"] == 1.0

    def test_risk_normalized_to_lowercase(self):
        p = {"id": "P1", "risk": "MEDICAL", "allowed_actions": ["block"], "min_confidence": 0.5}
        result = _validate_policy(p, 0)
        assert result["risk"] == "medical"

    def test_not_a_dict(self):
        assert _validate_policy("not_a_dict", 0) is None


# ────────────────────────────────────────────────────────────────
# input_loader tests
# ────────────────────────────────────────────────────────────────

class TestValidateInput(unittest.TestCase):
    def test_valid_input(self):
        item = {"id": "R1", "risk": "medical", "output": "Take medicine", "confidence": 0.95}
        result = _validate_input(item, 0)
        assert result is not None
        assert result["id"] == "R1"
        assert result["confidence"] == 0.95

    def test_missing_id(self):
        item = {"risk": "medical", "output": "Take medicine", "confidence": 0.95}
        assert _validate_input(item, 0) is None

    def test_missing_risk_defaults_to_unknown(self):
        item = {"id": "R1", "output": "Take medicine", "confidence": 0.95}
        result = _validate_input(item, 0)
        assert result["risk"] == "unknown"

    def test_missing_confidence_defaults_to_zero(self):
        item = {"id": "R1", "risk": "medical", "output": "Take medicine"}
        result = _validate_input(item, 0)
        assert result["confidence"] == 0.0

    def test_confidence_clamped_high(self):
        item = {"id": "R1", "risk": "medical", "output": "x", "confidence": 2.5}
        result = _validate_input(item, 0)
        assert result["confidence"] == 1.0

    def test_confidence_clamped_low(self):
        item = {"id": "R1", "risk": "medical", "output": "x", "confidence": -0.5}
        result = _validate_input(item, 0)
        assert result["confidence"] == 0.0

    def test_risk_normalized(self):
        item = {"id": "R1", "risk": "FINANCIAL", "output": "x", "confidence": 0.9}
        result = _validate_input(item, 0)
        assert result["risk"] == "financial"


# ────────────────────────────────────────────────────────────────
# matcher tests
# ────────────────────────────────────────────────────────────────

class TestMatcher(unittest.TestCase):
    def _make_policy(self, pid, risk, actions, min_conf):
        return {"id": pid, "risk": risk, "allowed_actions": actions, "min_confidence": min_conf}

    def _make_input(self, iid, risk, confidence):
        return {"id": iid, "risk": risk, "output": "some text", "confidence": confidence}

    def test_exact_risk_match(self):
        policies = [
            self._make_policy("P1", "medical", ["escalate"], 0.9),
            self._make_policy("P2", "financial", ["allow"], 0.7),
        ]
        item = self._make_input("R1", "medical", 0.95)
        matched = find_matching_policies(item, policies)
        assert len(matched) == 1
        assert matched[0]["id"] == "P1"

    def test_no_match_returns_empty(self):
        policies = [self._make_policy("P1", "medical", ["escalate"], 0.9)]
        item = self._make_input("R1", "unknown", 0.99)
        assert find_matching_policies(item, policies) == []

    def test_multiple_policies_same_risk(self):
        policies = [
            self._make_policy("P1", "medical", ["escalate"], 0.95),
            self._make_policy("P2", "medical", ["block"], 0.0),
        ]
        item = self._make_input("R1", "medical", 0.96)
        matched = find_matching_policies(item, policies)
        assert len(matched) == 2

    def test_evaluate_policy_threshold_met(self):
        policy = self._make_policy("P1", "medical", ["escalate"], 0.9)
        item = self._make_input("R1", "medical", 0.95)
        trace = evaluate_policy(item, policy)
        assert trace["threshold_met"] is True
        assert trace["effective_actions"] == ["escalate"]

    def test_evaluate_policy_threshold_not_met(self):
        policy = self._make_policy("P1", "medical", ["escalate"], 0.9)
        item = self._make_input("R1", "medical", 0.85)
        trace = evaluate_policy(item, policy)
        assert trace["threshold_met"] is False
        assert trace["effective_actions"] == []

    def test_evaluate_policy_exact_threshold(self):
        # Exactly at threshold should pass
        policy = self._make_policy("P1", "medical", ["escalate"], 0.9)
        item = self._make_input("R1", "medical", 0.9)
        trace = evaluate_policy(item, policy)
        assert trace["threshold_met"] is True


# ────────────────────────────────────────────────────────────────
# resolver tests
# ────────────────────────────────────────────────────────────────

class TestResolver(unittest.TestCase):
    def _make_input(self, iid="R1", risk="medical", confidence=0.95):
        return {"id": iid, "risk": risk, "output": "Some AI output", "confidence": confidence}

    def _make_trace(self, pid, threshold_met, effective_actions, candidate_actions=None, conf_required=0.9, conf_given=0.95):
        return {
            "policy_id": pid,
            "confidence_required": conf_required,
            "confidence_given": conf_given,
            "threshold_met": threshold_met,
            "candidate_actions": candidate_actions or effective_actions,
            "effective_actions": effective_actions,
        }

    def test_most_restrictive_block_wins(self):
        assert _most_restrictive(["allow", "sanitize", "escalate", "block"]) == "block"

    def test_most_restrictive_escalate_over_allow(self):
        assert _most_restrictive(["allow", "escalate"]) == "escalate"

    def test_most_restrictive_single(self):
        assert _most_restrictive(["sanitize"]) == "sanitize"

    def test_no_policies_uses_default(self):
        item = self._make_input()
        decision = resolve_decision(item, [], "block")
        assert decision["decision"] == "block"
        assert decision["applied_policies"] == []

    def test_threshold_not_met_uses_default(self):
        item = self._make_input()
        traces = [self._make_trace("P1", False, [], conf_required=0.99, conf_given=0.80)]
        decision = resolve_decision(item, traces, "block")
        assert decision["decision"] == "block"
        assert decision["applied_policies"] == []

    def test_single_policy_allow(self):
        item = self._make_input(risk="general", confidence=0.8)
        traces = [self._make_trace("P1", True, ["allow"], conf_required=0.7, conf_given=0.8)]
        decision = resolve_decision(item, traces, "block")
        assert decision["decision"] == "allow"
        assert decision["final_output"] == "Some AI output"

    def test_single_policy_escalate(self):
        item = self._make_input()
        traces = [self._make_trace("P1", True, ["escalate"])]
        decision = resolve_decision(item, traces, "block")
        assert decision["decision"] == "escalate"

    def test_single_policy_sanitize(self):
        item = self._make_input()
        traces = [self._make_trace("P1", True, ["sanitize"])]
        decision = resolve_decision(item, traces, "block")
        assert decision["decision"] == "sanitize"
        assert "cannot be shown" in decision["final_output"]

    def test_single_policy_block(self):
        item = self._make_input()
        traces = [self._make_trace("P1", True, ["block"])]
        decision = resolve_decision(item, traces, "allow")
        assert decision["decision"] == "block"

    def test_multi_policy_most_restrictive(self):
        """block should win over escalate"""
        item = self._make_input()
        traces = [
            self._make_trace("P1", True, ["escalate"]),
            self._make_trace("P2", True, ["block"], conf_required=0.0),
        ]
        decision = resolve_decision(item, traces, "allow")
        assert decision["decision"] == "block"
        assert "P1" in decision["applied_policies"]
        assert "P2" in decision["applied_policies"]

    def test_one_policy_passes_one_fails(self):
        """Only the passing policy's action is used"""
        item = self._make_input(confidence=0.85)
        traces = [
            self._make_trace("P1", False, [], candidate_actions=["escalate"], conf_required=0.95, conf_given=0.85),
            self._make_trace("P2", True, ["sanitize"], conf_required=0.0, conf_given=0.85),
        ]
        decision = resolve_decision(item, traces, "block")
        assert decision["decision"] == "sanitize"
        assert "P2" in decision["applied_policies"]
        assert "P1" not in decision["applied_policies"]

    def test_decision_is_deterministic(self):
        """Same input always produces same output"""
        item = self._make_input()
        traces = [
            self._make_trace("P1", True, ["escalate"]),
            self._make_trace("P2", True, ["block"]),
        ]
        d1 = resolve_decision(item, traces, "allow")
        d2 = resolve_decision(item, traces, "allow")
        assert d1["decision"] == d2["decision"]

    def test_reason_is_present(self):
        item = self._make_input()
        traces = [self._make_trace("P1", True, ["block"])]
        decision = resolve_decision(item, traces, "allow")
        assert decision["reason"] != ""

    def test_rule_trace_included(self):
        item = self._make_input()
        traces = [self._make_trace("P1", True, ["block"])]
        decision = resolve_decision(item, traces, "allow")
        assert len(decision["rule_trace"]) == 1
        assert decision["rule_trace"][0]["policy_id"] == "P1"


# ────────────────────────────────────────────────────────────────
# Integration test using actual data files
# ────────────────────────────────────────────────────────────────

class TestIntegration(unittest.TestCase):
    def test_full_pipeline(self):
        import json, tempfile, pathlib
        from engine import run_engine
        tmp_path = pathlib.Path(tempfile.mkdtemp())

        policies = {
            "policies": [
                {"id": "MED_STRICT", "risk": "medical", "allowed_actions": ["escalate"], "min_confidence": 0.95},
                {"id": "MED_BLOCK", "risk": "medical", "allowed_actions": ["block"], "min_confidence": 0.0},
                {"id": "GEN_ALLOW", "risk": "general", "allowed_actions": ["allow"], "min_confidence": 0.7},
                {"id": "GEN_SANITIZE", "risk": "general", "allowed_actions": ["sanitize"], "min_confidence": 0.0},
            ],
            "default_action": "block"
        }
        inputs = [
            {"id": "T1", "risk": "medical", "output": "Take this pill", "confidence": 0.96},
            {"id": "T2", "risk": "medical", "output": "Increase dose", "confidence": 0.80},
            {"id": "T3", "risk": "general", "output": "Reset password", "confidence": 0.85},
            {"id": "T4", "risk": "general", "output": "Try again", "confidence": 0.50},
            {"id": "T5", "risk": "unknown", "output": "??", "confidence": 0.99},
        ]

        p_file = tmp_path / "policies.json"
        i_file = tmp_path / "inputs.json"
        o_file = tmp_path / "output.json"
        p_file.write_text(json.dumps(policies))
        i_file.write_text(json.dumps(inputs))

        results = run_engine(str(p_file), str(i_file), str(o_file))
        results_by_id = {r["id"]: r for r in results}

        # T1: medical, 0.96 — MED_STRICT (escalate) AND MED_BLOCK (block) both pass → block wins
        assert results_by_id["T1"]["decision"] == "block"

        # T2: medical, 0.80 — MED_STRICT fails (0.80 < 0.95), MED_BLOCK passes (block) → block
        assert results_by_id["T2"]["decision"] == "block"

        # T3: general, 0.85 — GEN_ALLOW passes (allow) AND GEN_SANITIZE passes (sanitize) → sanitize wins
        assert results_by_id["T3"]["decision"] == "sanitize"

        # T4: general, 0.50 — GEN_ALLOW fails (0.50 < 0.7), GEN_SANITIZE passes → sanitize
        assert results_by_id["T4"]["decision"] == "sanitize"

        # T5: unknown risk — no policies match → default block
        assert results_by_id["T5"]["decision"] == "block"

        # Output file should exist and be valid JSON
        assert o_file.exists()
        with open(o_file) as f:
            written = json.load(f)
        assert len(written) == 5
