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

### Put it online (private, password-protected)

1. Create a free account at [render.com](https://render.com) and connect your GitHub.
2. New → **Blueprint** → choose `pfas-copilot`. Render reads `render.yaml`.
3. In the service's **Environment** tab, set `PFAS_PASSWORD` to a strong password.
4. Open the URL Render gives you; log in with user `pfas` and that password.

The database lives on a 1 GB persistent disk (Starter plan). Any host that runs Docker works too:
set `PFAS_PASSWORD` and mount a volume at `/data`.

Tests: `pytest` (engine, PDF parser, API), on Python 3.9 and later.

## How it works

1. **Products and materials** (CSV or Excel upload). Templates at `/api/templates/products.xlsx` and `materials.xlsx` (or `.csv`).
   Each material carries the supplier's declaration on intentionally added PFAS (yes / no / unknown).
2. **Lab results**: a results CSV or Excel file, or lab-report **PDFs**. The PDF parser (`pfas_copilot/parsers/pdf.py`)
   reads the report number, date, method and measurement uncertainty, finds result tables in either
   layout (one row per analyte, or one column per analyte), converts units to ppm, and matches each
   sample to a material by its description. PDF results stay in **To review** until a person confirms
   them; only confirmed results count.
3. **Verdicts** (`pfas_copilot/check.py`): Pass if result + U < limit, Fail if result − U ≥ limit,
   otherwise At risk. U is the lab's expanded uncertainty, or 20% by default. Bans without a number rely
   on supplier declarations, with a fluorine screen ≥ 100 ppm flagged as likely intentional use.
   TOF vs total fluorine and ppb targeted limits are handled separately. Evaluated on an as-of date and a look-ahead date.
4. **Outputs**: test plan with cost estimates, the **client report** (Client report page → Save as PDF),
   a technical report, certificate drafts and a deadline timeline.
5. **Trust**: every rule links to its sources; every confirmation records the reviewer and time; all
   changes are logged. See [VALIDATION.md](VALIDATION.md) for the decision rules, test scenarios and limitations.

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
