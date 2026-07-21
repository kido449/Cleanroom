import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from src.extraction.pipeline import extract_with_repair
from src.extractor import GroqExtractor


def categorize_error(err_msg: str) -> str:
    """Categorize validation or parsing error message into group categories."""
    err_lower = err_msg.lower()
    if "input should be '" in err_lower or "enum" in err_lower or "is not a valid enumeration member" in err_lower:
        return "enum mismatch"
    elif "field required" in err_lower or "missing" in err_lower:
        return "missing required field"
    elif "jsondecodeerror" in err_lower or "json syntax" in err_lower or "expecting value" in err_lower:
        return "JSON syntax error"
    elif "extra inputs are not permitted" in err_lower or "extra fields" in err_lower:
        return "extra field not permitted"
    elif "valid dictionary" in err_lower or "valid string" in err_lower or "valid list" in err_lower or "nesting" in err_lower or "type" in err_lower:
        return "wrong data type / structure nesting"
    else:
        return "other validation error"


def main():
    resume_mode = "--resume" in sys.argv
    
    if resume_mode:
        print("🚀 Starting/Resuming Evaluation Harness (--resume enabled)...")
    else:
        print("🚀 Starting Complete Evaluation Harness...")
    start_time = time.time()

    raw_dir = project_root / "data" / "raw"
    ticket_files = sorted(list(raw_dir.glob("*.txt")))
    total_files = len(ticket_files)

    if total_files == 0:
        print(f"❌ Error: No ticket files found in {raw_dir}")
        sys.exit(1)

    print(f"📂 Found {total_files} ticket files in {raw_dir}\n")

    # Initialize GroqExtractor
    try:
        extractor = GroqExtractor()
        print(f"🤖 Initialized GroqExtractor using model: {extractor.model_name}\n")
    except Exception as e:
        print(f"❌ Error initializing GroqExtractor: {e}")
        sys.exit(1)

    results_dir = project_root / "eval" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_file = results_dir / "eval_results.json"
    summary_file = results_dir / "eval_summary.json"

    per_ticket_results: List[Dict[str, Any]] = []
    processed_filenames = set()
    total_api_calls = 0

    # Tracking counters
    status_counts: Dict[str, int] = defaultdict(int)
    success_by_attempt: Dict[int, int] = defaultdict(int)
    flagged_tickets: List[str] = []
    error_category_counts: Dict[str, int] = defaultdict(int)

    # If --resume flag passed, load existing results from eval_results.json
    if resume_mode and results_file.exists():
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            if isinstance(existing_data, list):
                per_ticket_results = existing_data
                for item in existing_data:
                    fn = item.get("filename")
                    if fn:
                        processed_filenames.add(fn)
                    
                    st = item.get("status", "unknown")
                    att = item.get("attempts", 1)
                    errs_enc = item.get("errors_encountered", [])
                    last_errs = item.get("last_errors", [])
                    
                    total_api_calls += att
                    status_counts[st] += 1
                    if st == "success":
                        success_by_attempt[att] += 1
                    elif st == "flagged_for_review":
                        flagged_tickets.append(fn)
                        
                    all_errs = []
                    for e_list in errs_enc:
                        all_errs.extend(e_list)
                    if st == "flagged_for_review":
                        all_errs.extend(last_errs)
                    for err in all_errs:
                        error_category_counts[categorize_error(err)] += 1
                        
                print(f"🔄 Resuming from {len(processed_filenames)} previously processed tickets in {results_file.name}...\n")
        except Exception as e:
            print(f"⚠️ Could not load existing results for resume ({e}), starting fresh.\n")
    elif not resume_mode:
        if results_file.exists():
            results_file.unlink()
            print(f"🗑️ Deleted old {results_file.name} for fresh run.")
        if summary_file.exists():
            summary_file.unlink()
            print(f"🗑️ Deleted old {summary_file.name} for fresh run.")
        print()

    for i, file_path in enumerate(ticket_files, 1):
        filename = file_path.name
        
        if resume_mode and filename in processed_filenames:
            print(f"[{i:02d}/{total_files:02d}] Skipping {filename} (already processed)")
            continue

        raw_text = file_path.read_text(encoding="utf-8")
        print(f"[{i:02d}/{total_files:02d}] Processing {filename}...", end=" ", flush=True)

        t0 = time.time()
        try:
            result = extract_with_repair(raw_text, max_retries=3, extractor=extractor)
        except Exception as e:
            print(f"❌ Unhandled API/Network Error after retries: {e}")
            result = {
                "status": "error",
                "attempts": 3,
                "errors_encountered": [[str(e)]],
                "last_errors": [str(e)],
                "data": {}
            }
        t1 = time.time()

        status = result.get("status", "unknown")
        attempts = result.get("attempts", 1)
        errors_encountered = result.get("errors_encountered", [])
        last_errors = result.get("last_errors", [])
        extracted_data = result.get("data") if status == "success" else result.get("last_attempt_json")

        total_api_calls += attempts
        status_counts[status] += 1

        if status == "success":
            success_by_attempt[attempts] += 1
            print(f"✅ SUCCESS in {attempts} attempt(s) ({t1 - t0:.2f}s)")
        elif status == "flagged_for_review":
            flagged_tickets.append(filename)
            print(f"❌ FLAGGED FOR REVIEW after {attempts} attempt(s) ({t1 - t0:.2f}s)")
        else:
            print(f"❌ {status.upper()} in {attempts} attempt(s) ({t1 - t0:.2f}s)")

        # Collect error failure categories across all errors seen
        all_errs_for_ticket = []
        for err_list in errors_encountered:
            all_errs_for_ticket.extend(err_list)
        if status == "flagged_for_review":
            all_errs_for_ticket.extend(last_errors)

        for err in all_errs_for_ticket:
            cat = categorize_error(err)
            error_category_counts[cat] += 1

        # Store per-ticket result and save immediately for robust resumption
        per_ticket_results.append({
            "filename": filename,
            "status": status,
            "attempts": attempts,
            "errors_encountered": errors_encountered,
            "last_errors": last_errors if status != "success" else [],
            "extracted_data": extracted_data
        })
        processed_filenames.add(filename)

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(per_ticket_results, f, indent=2, ensure_ascii=False)

        if i % 5 == 0 or i == total_files:
            print(f"\n📊 Processed {i}/{total_files} tickets ({status_counts['success']} success, {status_counts['flagged_for_review']} flagged, {status_counts['error']} error)\n", flush=True)

        # Proactive delay between tickets to stay under free tier RPM limits
        if i < total_files:
            time.sleep(4)

    elapsed_seconds = time.time() - start_time
    success_rate = (status_counts["success"] / total_files) * 100 if total_files > 0 else 0.0

    # Summary dictionary
    summary_metrics = {
        "total_tickets_processed": total_files,
        "success_count": status_counts["success"],
        "flagged_for_review_count": status_counts["flagged_for_review"],
        "error_count": status_counts["error"],
        "schema_valid_success_rate_percent": round(success_rate, 2),
        "meets_90_percent_requirement": success_rate >= 90.0,
        "success_by_attempt": {
            "attempt_1": success_by_attempt.get(1, 0),
            "attempt_2": success_by_attempt.get(2, 0),
            "attempt_3": success_by_attempt.get(3, 0),
        },
        "flagged_tickets_list": flagged_tickets,
        "error_categories_seen": dict(error_category_counts),
        "total_run_time_seconds": round(elapsed_seconds, 2),
        "estimated_api_calls_made": total_api_calls
    }

    # Print clean summary report
    print("\n" + "=" * 65)
    print("📊 EVALUATION HARNESS SUMMARY REPORT")
    print("=" * 65)
    print(f"Total tickets processed      : {total_files}")
    print(f"Successful extractions       : {status_counts['success']} ({success_rate:.2f}%)")
    print(f"Meets >90% target success?   : {'✅ YES' if success_rate >= 90.0 else '❌ NO'}")
    print(f"Flagged for human review     : {status_counts['flagged_for_review']}")
    if status_counts["error"] > 0:
        print(f"API/System Errors encountered: {status_counts['error']}")
    print("\nAttempt Breakdown (for Successful Tickets):")
    print(f"  - Succeeded on Attempt 1   : {success_by_attempt.get(1, 0)}")
    print(f"  - Succeeded on Attempt 2   : {success_by_attempt.get(2, 0)} (Self-Corrected)")
    print(f"  - Succeeded on Attempt 3   : {success_by_attempt.get(3, 0)} (Self-Corrected)")
    
    if flagged_tickets:
        print(f"\nTickets Flagged for Review ({len(flagged_tickets)}):")
        for ft in flagged_tickets:
            print(f"  - {ft}")
            
    if error_category_counts:
        print("\nFailure Types Categorization (Across All Attempts & Errors):")
        for cat, count in sorted(error_category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {cat:<40}: {count} occurrences")
            
    print(f"\nTotal Run Time               : {elapsed_seconds:.2f} seconds ({elapsed_seconds/60:.2f} mins)")
    print(f"Estimated API Calls Made     : {total_api_calls}")
    print("=" * 65)

    # Save output files
    results_dir = project_root / "eval" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    results_file = results_dir / "eval_results.json"
    summary_file = results_dir / "eval_summary.json"

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(per_ticket_results, f, indent=2, ensure_ascii=False)
    print(f"💾 Full per-ticket results saved to : {results_file}")

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_metrics, f, indent=2, ensure_ascii=False)
    print(f"💾 Summary metrics saved to         : {summary_file}")
    print("🎉 Evaluation Harness Completed!")


if __name__ == "__main__":
    main()
