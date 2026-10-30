"""Material risk scoring and test planning."""
from __future__ import annotations

from dataclasses import dataclass

from .models import LabResult, Material

HIGH_TERMS = ("dwr", "durable water repellent", "water repellent", "water-repellent", "stain", "soil release",
              "oil repellent", "ptfe", "eptfe", "gore", "fluoro", "c6", "c8", "teflon", "laminate", "membrane")
MEDIUM_TERMS = ("polyester", "nylon", "polyamide", "coated", "coating", "pu", "tpu", "softshell", "nonwoven",
                "unknown", "performance")

EU_LIKE = {"EU", "France", "Denmark"}

COST_SCREEN = (200, 400)  # USD, TOF or TF screen ("a few hundred dollars")
COST_TARGETED = (400, 700)  # USD, targeted LC-MS/MS


@dataclass
class TestStep:
    material_id: str
    risk: str
    test: str
    why: str
    cost_low: int
    cost_high: int


def risk_level(m: Material) -> str:
    text = f"{m.material_type} {m.finish} {m.component}".lower()
    if m.declared_intentional == "yes" or any(t in text for t in HIGH_TERMS):
        return "High"
    if any(t in text for t in MEDIUM_TERMS):
        return "Medium"
    return "Low"


def plan_tests(m: Material, results: list[LabResult], markets: list[str], verdicts=()) -> list[TestStep]:
    risk = risk_level(m)
    have = {r.analyte.upper() for r in results}
    steps: list[TestStep] = []
    if m.declared_intentional == "yes":
        return [TestStep(m.material_id, risk, "Replace with a PFAS-free material, then TOF screen",
                         "Supplier declares intentionally added PFAS; testing cannot make it compliant", *COST_SCREEN)]
    if any(v.verdict == "Fail" for v in verdicts):
        return [TestStep(m.material_id, risk, "Switch to a PFAS-free finish, then re-screen (TOF/TF)",
                         "Measured fluorine exceeds a limit", *COST_SCREEN)]
    if risk == "Low" and not any(v.verdict == "At risk" for v in verdicts):
        return steps
    needs_tf = any(mk in {"Washington", "France", "Denmark"} for mk in markets)
    if "TOF" not in have and "TF" not in have:
        test = "Total fluorine (EN ISO 20999) + TOF" if needs_tf else "TOF screen"
        steps.append(TestStep(m.material_id, risk, test, f"{risk}-risk material with no fluorine screen",
                              *COST_SCREEN))
    elif needs_tf and "TF" not in have:
        steps.append(TestStep(m.material_id, risk, "Total fluorine (EN ISO 20999)",
                              "Washington/France/Denmark limits are on total fluorine", *COST_SCREEN))
    if any(mk in EU_LIKE for mk in markets) and not ({"PFHXA", "PFOA"} <= have):
        steps.append(TestStep(m.material_id, risk, "Targeted PFAS, EN 17681-1 (PFHxA, PFOA, C9-C14 PFCAs)",
                              "EU/France targeted limits in ppb", *COST_TARGETED))
    if any(v.verdict == "At risk" for v in verdicts) and not any("Targeted" in s.test for s in steps):
        steps.append(TestStep(m.material_id, risk, "Retest or confirm with targeted LC-MS/MS",
                              "Result within uncertainty of a limit", *COST_TARGETED))
    return steps
