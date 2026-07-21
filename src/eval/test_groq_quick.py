"""Quick smoke test: process ticket_001.txt and ticket_002.txt through GroqExtractor pipeline."""
import os
import sys
import json
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from src.extractor import GroqExtractor
from src.extraction.pipeline import extract_with_repair

raw_dir = project_root / "data" / "raw"
test_tickets = ["ticket_001.txt", "ticket_002.txt"]

extractor = GroqExtractor()
print(f"✅ GroqExtractor initialized: model={extractor.model_name}\n")

for ticket_name in test_tickets:
    ticket_path = raw_dir / ticket_name
    if not ticket_path.exists():
        print(f"❌ {ticket_name} not found!")
        continue

    raw_text = ticket_path.read_text(encoding="utf-8")
    print(f"{'='*60}")
    print(f"📄 {ticket_name}")
    print(f"{'='*60}")
    print(f"Raw text ({len(raw_text)} chars): {raw_text[:200]}...")
    print()

    try:
        result = extract_with_repair(raw_text, max_retries=3, extractor=extractor)
    except Exception as e:
        print(f"❌ Exception: {e}")
        continue

    status = result.get("status")
    attempts = result.get("attempts")
    data = result.get("data") if status == "success" else result.get("last_attempt_json")

    print(f"Status: {status}")
    print(f"Attempts: {attempts}")
    if result.get("errors_encountered"):
        print(f"Errors encountered: {result['errors_encountered']}")
    print(f"\n📋 Extracted JSON:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print()
