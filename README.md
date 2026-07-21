# structured-extract

A Python document extraction pipeline for processing noisy input samples (contracts, support tickets) into validated structured schemas.

## Project Structure

```
structured-extract/
├── data/
│   ├── raw/          # Noisy input samples (contracts/tickets)
│   └── schema/       # Pydantic models for domain schema definitions
├── src/
│   ├── extraction/   # Extraction logic
│   ├── validation/   # Validation logic using Pydantic
│   └── eval/         # Evaluation scripts
├── eval/
│   └── results/      # Evaluation metrics and outputs
├── report/           # Reports and documentation
├── requirements.txt
└── README.md
```

## Setup & Running Tests

1. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run tests:
   ```bash
   pytest
   ```
