"""
main.py
CLI entry point for the Policy-Driven AI Guardrail Engine.

Usage:
    python main.py
    python main.py --policies policies.json --inputs inputs.json --output output.json
    python main.py --policies policies.json --inputs inputs.json --output output.json --verbose
"""

import argparse
import logging
import sys

from engine import run_engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Policy-Driven AI Guardrail Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --policies custom_policies.json --inputs custom_inputs.json
  python main.py --verbose
        """,
    )
    parser.add_argument(
        "--policies",
        default="policies.json",
        help="Path to policies JSON file (default: policies.json)",
    )
    parser.add_argument(
        "--inputs",
        default="inputs.json",
        help="Path to inputs JSON file (default: inputs.json)",
    )
    parser.add_argument(
        "--output",
        default="output.json",
        help="Path to write output JSON file (default: output.json)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    return parser.parse_args()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger("main")
    logger.info("=" * 60)
    logger.info("Policy-Driven AI Guardrail Engine")
    logger.info("=" * 60)
    logger.info(f"Policies : {args.policies}")
    logger.info(f"Inputs   : {args.inputs}")
    logger.info(f"Output   : {args.output}")
    logger.info("=" * 60)

    results = run_engine(
        policies_path=args.policies,
        inputs_path=args.inputs,
        output_path=args.output,
    )

    # Print summary table to stdout
    print("\n── Guardrail Summary ──────────────────────────────────────────")
    print(f"{'ID':<6} {'RISK':<12} {'CONF':>6}  {'DECISION':<10} {'POLICIES'}")
    print("─" * 65)
    for r in results:
        # We need original risk/confidence — re-derive from reason or just show what we have
        policies_str = ", ".join(r["applied_policies"]) if r["applied_policies"] else "(default)"
        print(f"{r['id']:<6} {'':12} {'':>6}  {r['decision']:<10} {policies_str}")
    print("─" * 65)
    print(f"Total processed: {len(results)} inputs")
    print(f"Output written to: {args.output}\n")


if __name__ == "__main__":
    main()
