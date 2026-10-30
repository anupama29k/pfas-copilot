# PFAS Copilot — Validation

This document describes how PFAS Copilot reaches a verdict, how that logic is tested, and what it does
not do. It is written to be shared with a customer's compliance or quality team.

Version 0.3 · rules database: 33 obligations (10 US states, EU, France, Denmark), sources compiled to
Oct 30, 2026.

## 1. Decision rules

| Situation | Verdict |
| --- | --- |
| result + U < limit | **Pass** |
| result − U ≥ limit | **Fail** |
| uncertainty band crosses the limit | **At risk** (retest or confirm with a targeted method) |
| result below LOQ, and LOQ < limit | **Pass** |
| result below LOQ, but LOQ ≥ limit | **At risk** (the method cannot show compliance) |
| supplier declares intentionally added PFAS, under an intent-based rule | **Fail** |
| intent-based ban, no declaration on file | **Declaration required** |
| intent-based ban, fluorine screen ≥ 100 ppm | **At risk** (likely intentional use) |
| required test missing | **No data** (never reported as Pass) |
| only labeling, notice or reporting duties apply | **Obligations only** |

U = the lab's stated expanded uncertainty (k = 2). If the lab states none, 20% relative is used and
shown as "20% default" in the evidence table.

**Total organic fluorine (TOF) vs total fluorine (TF).** TF ≥ TOF, because TF also counts inorganic fluorine.
- Against a TOF limit (California, Vermont): a TF pass proves a TOF pass. A TF result over the limit is only At risk.
- Against a TF limit (Washington, France, Denmark): a TOF result over the limit proves a fail. A TOF result under the limit is only At risk.

**Targeted limits** (EU PFHxA, PFOA, C9–C14 PFCAs; France single-substance limits) are compared only
against the matching analyte from targeted LC-MS/MS, and are reported in ppb.

**Superseded thresholds.** When a stricter threshold replaces an earlier one (California 100 → 50 ppm
on Jan 1, 2027), only the threshold in force on the evaluation date applies.

**Severe-wet outdoor apparel** is evaluated only against rules that cover it on that date. Several
states defer it to 2028 and require a "Made with PFAS chemicals" disclosure in the meantime.

## 2. Evidence controls

- Results read from a lab PDF are **not used** until a named reviewer confirms the value, the unit
  conversion and the material match. The reviewer's name and timestamp are stored and printed in the
  report's evidence appendix.
- Results imported from a CSV are recorded as "CSV import", with the time of import.
- Every upload, confirmation, rejection, value edit, material reassignment and declaration change is
  written to a change log, printed as Appendix C of the client report.
- Results still awaiting review at report time are excluded, and the report says so.

## 3. Automated test scenarios

Run `pytest`: 26 tests, passing on Python 3.9 and 3.12.

| # | Scenario | Expected | Test |
| --- | --- | --- | --- |
| 1 | TOF 30 ppm (U 20%) vs 50 ppm limit | Pass | `test_uncertainty_band` |
| 2 | TOF 45 ppm (U 20%) vs 50 ppm | At risk | `test_uncertainty_band` |
| 3 | TOF 70 ppm (U 20%) vs 50 ppm | Fail | `test_uncertainty_band` |
| 4 | < LOQ with LOQ 5 vs 50 ppm limit | Pass | `test_below_loq_passes_only_if_loq_below_limit` |
| 5 | < LOQ with LOQ 60 vs 50 ppm limit | At risk | same |
| 6 | California rule on Oct 30, 2026 vs Jan 1, 2027 | CA-1 (100 ppm), then CA-2 (50 ppm) | `test_california_threshold_supersedes` |
| 7 | Severe-wet jacket in California, 2026 vs 2028 | no limit, then CA-3 | `test_severe_wet_deferral_in_california` |
| 8 | TOF 48 ppm: 2026 vs 2027 in California | Pass, then At risk | `test_tof_48_passes_100_but_at_risk_at_50` |
| 9 | Supplier declares PFAS, New York ban | Fail | `test_declared_intentional_fails_ban` |
| 10 | TF 80 ppm vs California 50 ppm TOF limit | At risk, not Fail | `test_tf_fail_is_only_at_risk_against_tof_limit` |
| 11 | Market with only reporting duties | Obligations only, not Pass | `test_obligation_only_market_is_not_reported_as_pass` |
| 12 | PDF, one column per analyte (TOF in mg/kg) | value, LOQ, uncertainty and report id extracted | `test_wide_tof_report` |
| 13 | PDF, one row per analyte (µg/kg and mg/kg mixed) | units converted to ppm per row | `test_long_targeted_report_converts_ug_per_kg` |
| 14 | Confirming without a reviewer name, or without a material | rejected | `test_client_report_...`, `test_cannot_confirm_without_material` |
| 15 | Editing a lab value | verdict recalculated | `test_editing_a_value_changes_the_verdict` |
| 16 | Full flow: CSV + PDF → review → verdicts → report | expected verdicts; all report sections present | `test_full_flow_csv_then_pdf_review`, `test_client_report_...` |

## 4. Known limitations

- **Rules are compiled from secondary legal and industry sources**, not from the statutes themselves.
  Each rule has a confidence rating. Medium and Low ratings (Connecticut, Rhode Island, Vermont,
  Maine's severe-wet rule, California registration) must be checked against the statute before use.
- **The PDF parser has been tested on synthetic reports only.** Real lab formats vary, so every
  extracted value is human-reviewed by design. Scanned PDFs (no text layer) are not supported.
- **No standardized TOF method exists for textiles yet.** Results from different labs or methods may
  not be directly comparable.
- **The 100 ppm intentional-use screen** is a heuristic flag for review, not a legal threshold.
- **Cost estimates** are indicative ranges, not lab quotes.
- **Not legal advice.** Certificates of compliance are drafts for the manufacturer to review and sign.

## 5. Planned validation (before the first paid audit)

1. Re-run 3–5 real, anonymized lab reports through the parser, and compare against values typed in by hand
   (target: ≥ 95% of fields correct before review).
2. Have a second analyst independently assign verdicts for one sample brand, and reconcile any differences.
3. Check every Medium/Low-confidence rule against the statute text, and raise its rating or correct it.
4. Have counsel review the certificate wording and the report's limitations section.
