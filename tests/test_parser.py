from pathlib import Path

import pytest

from pfas_copilot.parsers.pdf import norm_analyte, parse_number, parse_pdf

PDFS = Path(__file__).resolve().parents[1] / "samples" / "pdfs"


def test_wide_tof_report():
    r = parse_pdf(PDFS / "labx_R-002_tof.pdf")
    assert r.report_id == "R-002" and r.layout == "wide" and r.uncertainty_rel == pytest.approx(0.20)
    s1 = next(x for x in r.rows if x.sample_ref == "S-1")
    assert s1.analyte == "TOF" and s1.value_ppm == 48 and s1.loq_ppm == 5
    s2 = next(x for x in r.rows if x.sample_ref == "S-2")
    assert s2.below_loq and s2.loq_ppm == 5


def test_long_targeted_report_converts_ug_per_kg():
    r = parse_pdf(PDFS / "laby_LY-2026-0457_targeted.pdf")
    assert r.report_id == "LY-2026-0457" and r.layout == "long" and str(r.date) == "2026-09-20"
    pfhxa = [x for x in r.rows if x.analyte == "PFHxA"]
    assert pfhxa[0].value_ppm == pytest.approx(0.0032)  # 3.2 ug/kg
    tf = next(x for x in r.rows if x.analyte == "TF")
    assert tf.value_ppm == 30  # stated in mg/kg on its own row


@pytest.mark.parametrize("s,expected", [("48", (48.0, False)), ("< 5", (None, True)), ("ND", (None, True)), ("3,2", (3.2, False))])
def test_parse_number(s, expected):
    assert parse_number(s) == expected


def test_norm_analyte():
    assert norm_analyte("Total organic fluorine (TOF)") == "TOF"
    assert norm_analyte("Total fluorine") == "TF"
    assert norm_analyte("Perfluorohexanoic acid") == "PFHxA"
