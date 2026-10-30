# PFAS Copilot

PFAS compliance for apparel brands. Upload a brand's products, materials and lab reports; get
verdicts for every product in every market (US states, EU, France, Denmark) on any date, a test
plan with costs, and draft California AB 1817 certificates of compliance.

> Draft verdicts for expert review. Not legal advice. Rules marked Medium/Low confidence in the
> rules workbook must be checked against the statute before customer use.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate   # Python 3.9+
pip install -r requirements-dev.txt
uvicorn app.main:app --reload        # open http://127.0.0.1:8000
```

Click **Create sample audit** to see a full example, or create an audit and upload your own files.

Docker:

```bash
docker build -t pfas-copilot .
docker run -p 8000:8000 -v pfas-data:/data pfas-copilot
```

Tests: `pytest` (engine, PDF parser, API).

## How it works

1. **Products and materials** (CSV upload). Templates at `/api/templates/products.csv` and `materials.csv`.
   Each material carries the supplier's declaration on intentionally added PFAS (yes / no / unknown).
2. **Lab results**: a results CSV, or lab-report **PDFs**. The PDF parser (`pfas_copilot/parsers/pdf.py`)
   reads the report number, date, method and measurement uncertainty, finds result tables in either
   layout (one row per analyte, or one column per analyte), converts units to ppm, and matches each
   sample to a material by its description. PDF results stay in **To review** until a person confirms
   them; only confirmed results count.
3. **Verdicts** (`pfas_copilot/check.py`): Pass if result + U < limit, Fail if result − U ≥ limit,
   otherwise At risk. U is the lab's expanded uncertainty, or 20% by default. Bans without a number rely
   on supplier declarations, with a fluorine screen ≥ 100 ppm flagged as likely intentional use.
   TOF vs total fluorine and ppb targeted limits are handled separately. Evaluated on an as-of date and a look-ahead date.
4. **Outputs**: test plan with cost estimates, HTML report (`/api/audits/{id}/report.html`), certificate
   drafts (`/api/audits/{id}/certificates.md`), deadline timeline.

## Layout

```
app/                 FastAPI app (main.py), SQLite storage (db.py), UI (static/)
pfas_copilot/        engine: rules, models, check, risk, audit, report, CLI
pfas_copilot/parsers PDF lab-report parser
pfas_copilot/data    rules.xlsx — the rules workbook (33 obligations)
samples/             sample brand CSVs and synthetic lab PDFs (fictional labs)
scripts/             build_rules_workbook.py, make_sample_pdfs.py
tests/               engine, parser and API tests
```

Updating rules: edit `scripts/build_rules_workbook.py` (or the workbook directly, keeping the
`Scope codes` and `Limit kind` columns) and replace `pfas_copilot/data/rules.xlsx`.

## Not built yet

- OCR for scanned PDFs; parser profiles tuned on real reports from the first customers' labs
- User accounts, multi-tenant hosting, PDF export of reports
- Certificate wording reviewed by counsel
- Statute check of Low/Medium-confidence rules (CT, RI, ME severe-wet, VT)
