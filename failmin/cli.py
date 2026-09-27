from __future__ import annotations

import argparse
import sys

from .adapters.generic import load_trace, save_trace
from .api import minimize
from .core.models import RunResult, Trace
from .core.predicates import ExceptionPredicate, OutputContainsPredicate
from .demo import run_demo
from .reports import write_html_report, write_json_report


def _print_result(result) -> None:
    before = len(result.original.events)
    after = len(result.minimal.events)
    print("Original trace")
    print(f"Events        {before}")
    print(f"Failure rate  {result.original_failure_rate:.1%}")
    print("\nMinimal failure")
    print(f"Events        {after}")
    print(f"Reduction     {result.reduction:.1%}")
    print(f"Strategy      {result.strategy}")
    print(f"Evaluations   {result.tests_run}")
    print(f"Replay calls  {result.replay_calls}")
    print(f"Cache hits    {result.cache_hits}")
    print("\nCritical elements:")
    for event in result.minimal.events:
        print(f"- {event.id} ({event.type})")
    print("\nFailure still reproduced ✓")


def _snapshot_replay(trace: Trace) -> RunResult:
    """Offline replay for captured traces using the last recorded output/error.

    This is intentionally deterministic and network-free. Real agent execution is
    supplied through the Python API (or future framework adapters).
    """
    exception = None
    output = None
    for event in trace.events:
        if event.type in {"exception", "error"}:
            exception = str(event.output or event.input)
        if event.type in {"model_output", "assistant_message", "tool_result"}:
            output = event.output
    return RunResult(output=output, exception=exception)


def _add_reproduction_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runs", type=int, default=1, help="replays per candidate (default: 1)")
    parser.add_argument(
        "--threshold",
        type=float,
        default=1.0,
        help="required failure ratio in (0,1] (default: 1.0)",
    )
    parser.add_argument(
        "--strategy",
        choices=("delta", "hierarchical"),
        default="delta",
        help="reduction strategy (default: delta)",
    )
    parser.add_argument(
        "--group-key",
        default="group",
        help="metadata key used by hierarchical strategy (default: group)",
    )
    parser.add_argument("--no-cache", action="store_true", help="disable replay-decision cache")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="failmin", description="Minimize AI/Agent failure traces")
    sub = parser.add_subparsers(dest="command", required=True)

    demo_parser = sub.add_parser("demo", help="run the built-in zero-config demo")
    _add_reproduction_args(demo_parser)

    p = sub.add_parser("minimize", help="minimize a Generic JSON trace")
    p.add_argument("trace")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--output-contains")
    group.add_argument("--exception-contains")
    p.add_argument("--out", default="minimal-trace.json")
    p.add_argument("--report-json", help="write a machine-readable JSON report")
    p.add_argument("--report-html", help="write a self-contained HTML report")
    _add_reproduction_args(p)

    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            result = run_demo(
                runs=args.runs,
                threshold=args.threshold,
                cache=not args.no_cache,
                strategy=args.strategy,
                group_metadata_key=args.group_key,
            )
            _print_result(result)
            return 0

        trace = load_trace(args.trace)
        predicate = (
            OutputContainsPredicate(args.output_contains)
            if args.output_contains is not None
            else ExceptionPredicate(args.exception_contains)
        )
        result = minimize(
            trace,
            _snapshot_replay,
            predicate,
            runs=args.runs,
            threshold=args.threshold,
            cache=not args.no_cache,
            strategy=args.strategy,
            group_metadata_key=args.group_key,
        )
        save_trace(result.minimal, args.out)
        if args.report_json:
            write_json_report(result, args.report_json)
        if args.report_html:
            write_html_report(result, args.report_html)

        _print_result(result)
        print(f"\nSaved trace: {args.out}")
        if args.report_json:
            print(f"Saved JSON report: {args.report_json}")
        if args.report_html:
            print(f"Saved HTML report: {args.report_html}")
        return 0
    except Exception as exc:
        print(f"failmin: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
