import datetime as dt
from pathlib import Path

import pytest

from pfas_copilot.audit import run_audit
from pfas_copilot.check import AT_RISK, FAIL, PASS, compare, check
from pfas_copilot.models import Audit, LabResult, Material, load_materials, load_products, load_results
from pfas_copilot.rules import applicable, load_rules, DEFAULT_RULES

ROOT = Path(__file__).resolve().parents[1]
RULES = load_rules(DEFAULT_RULES)


def res(value, unc=0.2, analyte="TOF", below=False, loq=5.0):
    return LabResult("M", "lab", "r", "m", analyte, value, loq, unc, dt.date(2026, 9, 1), below)


def mat(declared="no"):
    return Material("M", "S", "shell", "polyester", "DWR", "Mill", declared)


def rule(rid):
    return next(r for r in RULES if r.rule_id == rid)


def test_rules_load():
    assert len(RULES) >= 30
    assert rule("CA-2").limit_ppm == 50
    assert rule("EU-1").limit_ppm == pytest.approx(0.025)
    assert rule("EU-1").target_analyte == "PFHxA"


@pytest.mark.parametrize("value,expected", [(30, PASS), (45, AT_RISK), (70, FAIL)])
def test_uncertainty_band(value, expected):
    assert compare(res(value), 50)[0] == expected


def test_below_loq_passes_only_if_loq_below_limit():
    assert compare(res(None, below=True, loq=5), 50)[0] == PASS
    assert compare(res(None, below=True, loq=60), 50)[0] == AT_RISK


def test_california_threshold_supersedes():
    before = applicable(RULES, "California", "apparel", False, dt.date(2026, 10, 30))
    after = applicable(RULES, "California", "apparel", False, dt.date(2027, 1, 1))
    assert [r.rule_id for r in before if r.is_limit] == ["CA-1"]
    assert [r.rule_id for r in after if r.is_limit] == ["CA-2"]


def test_severe_wet_deferral_in_california():
    rules = applicable(RULES, "California", "apparel", True, dt.date(2026, 10, 30))
    assert not [r for r in rules if r.is_limit]
    rules = applicable(RULES, "California", "apparel", True, dt.date(2028, 1, 1))
    assert [r.rule_id for r in rules if r.is_limit] == ["CA-3"]


def test_tof_48_passes_100_but_at_risk_at_50():
    m, r = mat(), [res(48)]
    assert check(m, rule("CA-1"), r).verdict == PASS
    assert check(m, rule("CA-2"), r).verdict == AT_RISK


def test_declared_intentional_fails_ban():
    assert check(mat("yes"), rule("NY-1"), []).verdict == FAIL


def test_tf_fail_is_only_at_risk_against_tof_limit():
    assert check(mat(), rule("CA-2"), [res(80, analyte="TF")]).verdict == AT_RISK


def test_sample_audit_end_to_end(tmp_path):
    s = ROOT / "samples"
    audit = Audit("Sample Outdoor Co", load_products(s / "products.csv"), load_materials(s / "materials.csv"),
                  load_results(s / "lab_results.csv"))
    out = run_audit(audit, RULES, dt.date(2026, 10, 30), dt.date(2027, 1, 1))
    now = {p.product.sku: p.by_market for p in out.results[dt.date(2026, 10, 30)]}
    jan = {p.product.sku: p.by_market for p in out.results[dt.date(2027, 1, 1)]}
    assert now["SH-200"]["California"] == PASS       # TOF 48 vs 100 ppm
    assert jan["SH-200"]["California"] == AT_RISK    # TOF 48 vs 50 ppm
    assert now["KT-300"]["California"] == FAIL       # TOF 140 ppm
    assert now["RJ-100"]["New York"] in ("No rule in force",)  # severe-wet exempt until 2028
    assert now["TB-400"]["California"] == PASS
    assert out.test_plan


def test_obligation_only_market_is_not_reported_as_pass():
    s = ROOT / "samples"
    audit = Audit("S", load_products(s / "products.csv"), load_materials(s / "materials.csv"),
                  load_results(s / "lab_results.csv"))
    out = run_audit(audit, RULES, dt.date(2026, 10, 30))
    rj = next(p for p in out.results[dt.date(2026, 10, 30)] if p.product.sku == "RJ-100")
    assert rj.by_market["Washington"] == "Obligations only"
    steps = {s.material_id: s.test for s in out.test_plan}
    assert steps["M2"].startswith("Replace")   # declared PFAS: don't test, replace
    assert steps["M5"].startswith("Switch")    # measured fail: reformulate
