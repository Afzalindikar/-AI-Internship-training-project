"""
main.py
-------
CLI entry point for the Multi-Source Data Extraction Engine.

Usage:
    python main.py --sources "data/input/sample.csv"
    python main.py --sources "https://example.com" --llm-format text
    python main.py --batch data/input/batch.json --output-format csv --verbose
"""
import sys
# Force UTF-8 output on Windows to avoid UnicodeEncodeError with special chars
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
import os
import sys
from pathlib import Path

# ── Config loading ────────────────────────────────────────────────────────────

def load_config(config_path: str = "config.json") -> dict:
    """Load config from JSON, then apply .env overrides."""
    config = {}
    if Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    # Apply .env overrides
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    env_map = {
        "ENABLE_OCR": ("enable_ocr", lambda v: v.lower() == "true"),
        "MAX_RETRIES": ("max_retries", int),
        "LOG_LEVEL": ("logging_level", str),
        "OUTPUT_FORMAT": ("output_format", str),
        "PARALLEL": ("parallel", lambda v: v.lower() == "true"),
        "BATCH_SIZE": ("batch_size", int),
        "LLM_FORMAT": ("llm_format", str),
    }
    for env_key, (cfg_key, cast) in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            try:
                config[cfg_key] = cast(val)
            except ValueError:
                pass

    return config


# ── Argument parsing ──────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="extraction-engine",
        description=(
            "Multi-Source Data Extraction Engine\n"
            "Supports: URLs, PDFs, CSV/Excel files, SQL Databases"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --sources "data/input/sample.csv"
  python main.py --sources "https://example.com" --llm-format text
  python main.py --batch data/input/batch.json --output-format csv --verbose
        """,
    )

    # Mutually exclusive input group
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--sources",
        nargs="+",
        metavar="SOURCE",
        help="One or more file paths, URLs, or DB URIs to process.",
    )
    source_group.add_argument(
        "--batch",
        metavar="BATCH_FILE",
        help="Path to a JSON file containing a list of sources to process.",
    )

    parser.add_argument(
        "--output-format",
        choices=["json", "csv"],
        default=None,
        metavar="FORMAT",
        help="Output format: json (default) or csv.",
    )
    parser.add_argument(
        "--llm-format",
        choices=["instruction", "text"],
        default=None,
        metavar="FORMAT",
        help="LLM dataset format: instruction (default) or text.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        metavar="CONFIG_FILE",
        help="Path to config.json (default: config.json).",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Process batch sources in parallel (ThreadPoolExecutor).",
    )


    return parser


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args = parser.parse_args()



    # ── Validate inputs ───────────────────────────────────────────────────────
    if not args.sources and not args.batch:
        parser.print_help()
        print("\n[ERROR] Provide --sources or --batch.")
        sys.exit(1)

    # ── Load config ───────────────────────────────────────────────────────────
    config = load_config(args.config)

    if args.verbose:
        config["logging_level"] = "DEBUG"
    if args.output_format:
        config["output_format"] = args.output_format
    if args.llm_format:
        config["llm_format"] = args.llm_format
    if args.parallel:
        config["parallel"] = True

    # ── Collect sources ───────────────────────────────────────────────────────
    sources: list[str] = []

    if args.sources:
        sources = args.sources
    elif args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            print(f"[ERROR] Batch file not found: {args.batch}")
            sys.exit(1)
        with open(batch_path, "r", encoding="utf-8") as f:
            batch_data = json.load(f)
        if isinstance(batch_data, list):
            sources = batch_data
        elif isinstance(batch_data, dict) and "sources" in batch_data:
            sources = batch_data["sources"]
        else:
            print("[ERROR] Batch file must be a JSON list or {'sources': [...]}.")
            sys.exit(1)

    if not sources:
        print("[ERROR] No sources found to process.")
        sys.exit(1)

    # ── Run pipeline ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  Multi-Source Data Extraction Engine")
    print(f"{'=' * 60}")
    print(f"  Sources  : {len(sources)}")
    print(f"  Format   : {config.get('output_format', 'json').upper()}")
    print(f"  LLM fmt  : {config.get('llm_format', 'instruction')}")
    print(f"  Parallel : {config.get('parallel', False)}")
    print(f"  Output   : {config.get('output_dir', 'output')}/")
    print(f"{'=' * 60}")
    print()

    from pipeline.orchestrator import DataPipeline
    pipeline = DataPipeline(config)

    if len(sources) == 1:
        result = pipeline.run(sources[0])
        results = [result]
    else:
        results = pipeline.run_batch(sources)

    # ── Print summary ─────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  PIPELINE RESULTS")
    print(f"{'=' * 60}")

    success = [r for r in results if r.get("status") == "SUCCESS"]
    failed  = [r for r in results if r.get("status") == "FAILED"]

    for r in results:
        status_icon = "[OK]" if r["status"] == "SUCCESS" else "[FAIL]"
        timing = f" ({r.get('total_time_seconds', 0):.2f}s)" if r.get("total_time_seconds") else ""
        print(
            f"  {status_icon:6}  [{r['status']:7}]  "
            f"{r.get('record_count', 0):4} records{timing}  |  {r['source']}"
        )
        if r.get("error"):
            print(f"           Error: {r['error']}")
        if r.get("output_paths"):
            for fmt, path in r["output_paths"].items():
                print(f"           [{fmt.upper():7}] {path}")

    # ── Aggregate summary ─────────────────────────────────────────────────────
    total_records = sum(r.get("record_count", 0) for r in results)
    total_time    = sum(r.get("total_time_seconds", 0) for r in results)

    print(f"\n{'─' * 60}")
    print(f"  SUMMARY REPORT")
    print(f"{'─' * 60}")
    print(f"  Total sources    : {len(results)}")
    print(f"  Successful       : {len(success)}")
    print(f"  Failed           : {len(failed)}")
    print(f"  Total records    : {total_records}")
    print(f"  Execution time   : {total_time:.2f}s")

    # Print per-step timings from last successful result
    last_ok = next((r for r in reversed(results) if r.get("step_timings")), None)
    if last_ok and last_ok.get("step_timings"):
        print(f"  Step timings (last job):")
        for step, dur in last_ok["step_timings"].items():
            print(f"    [{step.upper():9}] {dur:.3f}s")

    if failed:
        print(f"\n  Failed jobs -> {config.get('output_dir', 'output')}/failed_jobs.json")

    print(f"{'=' * 60}\n")

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
