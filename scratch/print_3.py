import json
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
results_file = project_root / "eval" / "results" / "eval_results.json"
raw_dir = project_root / "data" / "raw"

with open(results_file, "r", encoding="utf-8") as f:
    data = {d["filename"]: d for d in json.load(f)}

for fname in ["ticket_002.txt", "ticket_017.txt", "ticket_024.txt", "ticket_018.txt", "ticket_031.txt", "ticket_045.txt"]:
    print(f"============================================================")
    print(f"TICKET: {fname} (Attempts taken: {data[fname]['attempts']})")
    print(f"============================================================")
    print(f"--- ORIGINAL RAW TEXT ---")
    raw_path = raw_dir / fname
    print(raw_path.read_text(encoding="utf-8").strip())
    print(f"\n--- EXTRACTED JSON ---")
    print(json.dumps(data[fname]["extracted_data"], indent=2, ensure_ascii=False))
    if data[fname]["errors_encountered"]:
        print(f"\n--- ERRORS ENCOUNTERED & SELF-CORRECTED ---")
        print(data[fname]["errors_encountered"])
    print()
