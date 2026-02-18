# Policy-Driven AI Guardrail Engine

A deterministic guardrail layer that evaluates AI-generated outputs against configurable policy rules before they reach end users. No hardcoded logic — all behaviour is driven by `policies.json`.

---

## Architecture

```
inputs.json ──┐
              ├──► policy_loader.py ──► matcher.py ──► resolver.py ──► output.json
policies.json─┘         ↑                                   ↑
                    Loads & validates                  Picks most
                    all policies                       restrictive action
```

**Module responsibilities:**

| File | Responsibility |
|---|---|
| `policy_loader.py` | Load, validate, and normalise `policies.json` |
| `input_loader.py` | Load, validate, and normalise `inputs.json` |
| `matcher.py` | Match inputs to policies; evaluate confidence thresholds |
| `resolver.py` | Resolve the most restrictive action; build decision record |
| `engine.py` | Orchestrate the full pipeline |
| `main.py` | CLI entry point with `--policies`, `--inputs`, `--output` flags |
| `test_guardrail.py` | 38 unit + integration tests |

---

## How to Run

**Requirements:** Python 3.10+ (no third-party dependencies)

```bash
# Default — uses policies.json, inputs.json, writes output.json
python main.py

# Custom file paths
python main.py --policies policies.json --inputs inputs.json --output output.json

# Verbose/debug logging
python main.py --verbose

# Run tests
python -m unittest test_guardrail -v
```

---

## Policy Configuration (`policies.json`)

```json
{
  "policies": [
    {
      "id": "MED_STRICT",
      "risk": "medical",
      "allowed_actions": ["escalate"],
      "min_confidence": 0.95
    }
  ],
  "default_action": "block"
}
```

| Field | Description |
|---|---|
| `id` | Unique policy identifier |
| `risk` | Risk category to match against (case-insensitive) |
| `allowed_actions` | One or more of: `allow`, `sanitize`, `escalate`, `block` |
| `min_confidence` | Minimum AI confidence score (0.0–1.0) required to apply this policy |
| `default_action` | Action to use when no policies match or no thresholds are met |

---

## Action Hierarchy (Most → Least Restrictive)

```
block  >  escalate  >  sanitize  >  allow
```

When multiple policies match the same input, the **most restrictive** action always wins.

| Action | Effect |
|---|---|
| `allow` | Show original AI output to user |
| `sanitize` | Replace output with a generic safe message |
| `escalate` | Flag for human review |
| `block` | Suppress output entirely |

---

## Decision Logic

For each input:

1. Find all policies whose `risk` matches the input's `risk`
2. For each matched policy, check if `confidence >= min_confidence`
3. Collect all `allowed_actions` from policies that passed the threshold
4. Select the most restrictive action from those candidates
5. If no policy matched, or none passed the threshold → apply `default_action`

---

## Output Format (`output.json`)

```json
[
  {
    "id": "R1",
    "decision": "block",
    "applied_policies": ["MED_STRICT", "MED_BLOCK"],
    "rule_trace": [
      {
        "policy_id": "MED_STRICT",
        "confidence_required": 0.95,
        "confidence_given": 0.96,
        "threshold_met": true,
        "candidate_actions": ["escalate"],
        "effective_actions": ["escalate"]
      },
      {
        "policy_id": "MED_BLOCK",
        "confidence_required": 0.0,
        "confidence_given": 0.96,
        "threshold_met": true,
        "candidate_actions": ["block"],
        "effective_actions": ["block"]
      }
    ],
    "final_output": "[Output suppressed by guardrail policy.]",
    "reason": "Policy MED_STRICT: confidence 0.96 >= 0.95 ✓, actions=['escalate'] | Policy MED_BLOCK: confidence 0.96 >= 0.0 ✓, actions=['block'] | Multiple actions found ['block', 'escalate']; most restrictive 'block' selected."
  }
]
```

---

## Assumptions

1. **Confidence comparison is inclusive** — a confidence of exactly `min_confidence` passes (i.e., `>=` not `>`).
2. **Risk matching is case-insensitive** — `"MEDICAL"` and `"medical"` are treated identically.
3. **Unknown risk types** always fall through to `default_action` since no policies will match.
4. **Malformed policies** are skipped with a warning rather than crashing the engine.
5. **Malformed inputs** are skipped with a warning rather than crashing the engine.
6. **Multiple policies of the same risk** are all evaluated and the most restrictive outcome wins — there is no "first match wins" short-circuit.

---

## Tradeoffs

| Decision | Tradeoff |
|---|---|
| **Most restrictive multi-policy resolution** | Maximises safety but may over-block legitimate content where a lenient policy was intended to override a strict one. An explicit priority ordering system could give more control. |
| **Default action = block** | Safe by default — unknown risks are suppressed. This means new risk categories in inputs will be silently blocked until a policy is added. |
| **Sanitize replaces whole output** | Prevents partial leakage of unsafe content but loses potentially useful parts of the AI's response. |
| **No external dependencies** | Maximises portability and reproducibility. A schema validation library (e.g., `pydantic`) would improve validation ergonomics at the cost of a dependency. |
| **Policy loading fails gracefully** | The engine continues with zero policies (all inputs default-blocked) rather than hard-crashing on a bad config file. |
# Policy-Driven-AI-Guardrail
