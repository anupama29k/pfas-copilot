"""Run a full audit: every product x market x date."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .check import Verdict, check, worst
from .models import Audit, Product
from .risk import TestStep, plan_tests, risk_level
from .rules import Rule, applicable


@dataclass
class ProductResult:
    product: Product
    as_of: dt.date
    by_market: dict[str, str] = field(default_factory=dict)  # market -> worst verdict
    verdicts: list[Verdict] = field(default_factory=list)


@dataclass
class AuditResult:
    audit: Audit
    dates: list[dt.date]
    results: dict[dt.date, list[ProductResult]]
    test_plan: list[TestStep]
    risk: dict[str, str]
    rules: list[Rule]
    warnings: list[str]


def run_audit(audit: Audit, rules: list[Rule], as_of: dt.date, lookahead: dt.date | None = None) -> AuditResult:
    dates = [as_of] + ([lookahead] if lookahead and lookahead > as_of else [])
    known = {r.jurisdiction for r in rules}
    warnings = []
    out: dict[dt.date, list[ProductResult]] = {}
    for d in dates:
        rows = []
        for p in audit.products:
            pr = ProductResult(p, d)
            for market in p.markets:
                if market not in known:
                    warnings.append(f"{p.sku}: no rules tracked for market {market!r}")
                    continue
                mv = []
                for rule in applicable(rules, market, p.category, p.severe_wet, d):
                    for m in audit.materials_for(p.sku):
                        mv.append(check(m, rule, audit.results_for(m.material_id)))
                pr.by_market[market] = worst(mv) if mv else "No rule in force"
                pr.verdicts.extend(mv)
            rows.append(pr)
        out[d] = rows

    used = {v.rule_id for rows in out.values() for pr in rows for v in pr.verdicts}
    for r in rules:
        if r.rule_id in used and r.confidence.lower() == "low":
            warnings.append(f"{r.rule_id} ({r.jurisdiction}) is Low confidence: verify against the statute")

    plan, risk = [], {}
    by_sku = {p.sku: p for p in audit.products}
    for m in audit.materials:
        risk[m.material_id] = risk_level(m)
        mv = [v for rows in out.values() for pr in rows for v in pr.verdicts if v.material_id == m.material_id]
        plan += plan_tests(m, audit.results_for(m.material_id), by_sku[m.sku].markets, mv)
    return AuditResult(audit, dates, out, plan, risk, rules, sorted(set(warnings)))
