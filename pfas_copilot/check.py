"""Compliance check: one material against one rule, with measurement uncertainty."""
from __future__ import annotations

from dataclasses import dataclass

from .models import LabResult, Material
from .rules import Rule

DEFAULT_UNCERTAINTY = 0.20  # 20% relative expanded uncertainty when the lab gives none
INTENT_SCREEN_PPM = 100.0  # fluorine screen above this suggests intentional use (heuristic)

PASS, FAIL, AT_RISK, DECL, NO_DATA, OBLIG = (
    "Pass", "Fail", "At risk", "Declaration required", "No data", "Obligation")
SEVERITY = {FAIL: 5, AT_RISK: 4, DECL: 3, NO_DATA: 2, PASS: 1, OBLIG: 0}


@dataclass
class Verdict:
    material_id: str
    rule_id: str
    jurisdiction: str
    verdict: str
    reason: str


def _q(x_ppm: float, ppb: bool) -> str:
    return f"{x_ppm * 1000:.3g} ppb" if ppb else f"{x_ppm:.3g} ppm"


def compare(result: LabResult, limit_ppm: float, default_unc: float = DEFAULT_UNCERTAINTY):
    """Return (verdict, reason) for one numeric result against a limit in ppm.

    Limits below 1 ppm (targeted PFAS) are reported in ppb for readability.
    """
    ppb = limit_ppm < 1
    if result.below_loq:
        loq = f" (LOQ {_q(result.loq, ppb)})" if result.loq is not None else ""
        if result.loq is not None and result.loq >= limit_ppm:
            return AT_RISK, f"{result.analyte} below LOQ{loq}, but LOQ is not below the {_q(limit_ppm, ppb)} limit"
        return PASS, f"{result.analyte} below LOQ{loq}"
    u_rel = result.uncertainty_rel if result.uncertainty_rel is not None else default_unc
    u = result.value * u_rel
    lo, hi = result.value - u, result.value + u
    band = f"{result.analyte} {_q(result.value, ppb)} ± {_q(u, ppb)} vs limit {_q(limit_ppm, ppb)}"
    if hi < limit_ppm:
        return PASS, band
    if lo >= limit_ppm:
        return FAIL, band
    return AT_RISK, band + " (uncertainty band crosses the limit; retest or use a targeted method)"


def _latest(results: list[LabResult], analyte: str) -> LabResult | None:
    hits = [r for r in results if r.analyte.upper() == analyte.upper()]
    hits.sort(key=lambda r: (r.date is not None, r.date))
    return hits[-1] if hits else None


def check(material: Material, rule: Rule, results: list[LabResult]) -> Verdict:
    def v(verdict, reason):
        return Verdict(material.material_id, rule.rule_id, rule.jurisdiction, verdict, reason)

    kind = rule.limit_kind
    if kind == "obligation":
        return v(OBLIG, f"{rule.rule_type}: {rule.duties or rule.products}")
    if kind == "tbd":
        return v(NO_DATA, "Limit not yet set by regulator")

    declared = material.declared_intentional
    tof, tf = _latest(results, "TOF"), _latest(results, "TF")

    if kind in {"ban_intent", "intent_or_tof", "intent_or_total_f"} and declared == "yes":
        return v(FAIL, "Supplier declares intentionally added PFAS")

    if kind == "ban_intent":
        screen = tof or tf
        if screen and not screen.below_loq and screen.value >= INTENT_SCREEN_PPM:
            return v(AT_RISK, f"{screen.analyte} {screen.value:g} ppm suggests intentional use despite declaration '{declared}'")
        if declared == "no":
            return v(PASS, "Supplier declares no intentionally added PFAS" + (f"; {screen.analyte} screen consistent" if screen else ""))
        return v(DECL, "Ban on intentionally added PFAS: get a supplier declaration")

    limit = rule.limit_ppm
    if kind == "intent_or_tof":
        if tof:
            return v(*compare(tof, limit))
        if tf:  # TF >= TOF, so a TF pass also proves a TOF pass
            verdict, reason = compare(tf, limit)
            if verdict == FAIL:
                return v(AT_RISK, reason + " (total F includes inorganic F; run TOF)")
            return v(verdict, reason + " (TF used as upper bound for TOF)")
        return v(NO_DATA, f"Needs TOF screen against {limit:g} ppm")

    if kind in {"intent_or_total_f", "total_f"}:
        if tf:
            return v(*compare(tf, limit))
        if tof:
            verdict, reason = compare(tof, limit)
            if verdict == FAIL:
                return v(FAIL, reason + " (TOF already exceeds a total-fluorine limit)")
            return v(AT_RISK, reason + " (TOF is a lower bound; run total fluorine)")
        return v(NO_DATA, f"Needs total fluorine test against {limit:g} ppm")

    analyte = rule.target_analyte
    if analyte:
        res = _latest(results, analyte)
        if res:
            return v(*compare(res, limit))
        return v(NO_DATA, f"Needs targeted LC-MS/MS for {analyte} (limit {limit*1000:g} ppb)")

    return v(NO_DATA, f"Unhandled limit kind {kind!r}")


def worst(verdicts: list[Verdict]) -> str:
    graded = [x.verdict for x in verdicts if x.verdict != OBLIG]
    if graded:
        return max(graded, key=SEVERITY.get)
    return "Obligations only" if verdicts else PASS
