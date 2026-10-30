"""Load PFAS rules from the rules-engine spreadsheet and select the ones that apply."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook

OBLIGATION_KINDS = {"obligation", "tbd"}
DEFAULT_RULES = Path(__file__).parent / "data" / "rules.xlsx"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    jurisdiction: str
    law: str
    rule_type: str
    products: str
    notes: str
    limit_basis: str
    limit_value: float | None
    limit_unit: str
    test_basis: str
    effective: dt.date | None
    severe_wet: str
    duties: str
    confidence: str
    scope: frozenset[str] = field(default_factory=frozenset)
    limit_kind: str = "tbd"
    sources: tuple = ()  # ((title, url), ...)

    @property
    def limit_ppm(self) -> float | None:
        """Limit converted to ppm (mg/kg)."""
        if self.limit_value is None:
            return None
        unit = self.limit_unit.lower()
        if "ppb" in unit:
            return self.limit_value / 1000.0
        return float(self.limit_value)  # ppm, mg/kg, mg F/kg

    @property
    def target_analyte(self) -> str | None:
        if self.limit_kind.startswith("targeted:"):
            return self.limit_kind.split(":", 1)[1].strip()
        return None

    @property
    def is_limit(self) -> bool:
        return self.limit_kind not in OBLIGATION_KINDS

    def in_force(self, as_of: dt.date) -> bool:
        return self.effective is not None and self.effective <= as_of

    def applies_to(self, category: str, severe_wet: bool) -> bool:
        if "all" in self.scope:
            return True
        if severe_wet:
            return "severe_wet" in self.scope
        return category in self.scope


def _to_date(v) -> dt.date | None:
    if v is None or v == "":
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v)[:10])


def load_rules(path: str | Path = DEFAULT_RULES) -> list[Rule]:
    wb = load_workbook(path, data_only=True, read_only=True)
    src = {}
    if "Sources" in wb.sheetnames:
        it = wb["Sources"].iter_rows(values_only=True)
        next(it, None)
        for row in it:
            if row and row[0]:
                src[str(row[0]).strip()] = (str(row[2]) if len(row) > 2 and row[2] else str(row[1]), str(row[1]))
    ws = wb["Rules"]
    rows = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h else "" for h in next(rows)]
    idx = {h: i for i, h in enumerate(header)}

    def g(row, name, default=""):
        v = row[idx[name]] if name in idx else None
        return default if v is None else v

    rules = []
    for row in rows:
        if not row or not g(row, "Rule ID"):
            continue
        value = g(row, "Limit value", None)
        rules.append(
            Rule(
                rule_id=str(g(row, "Rule ID")),
                jurisdiction=str(g(row, "Jurisdiction")),
                law=str(g(row, "Law / citation")),
                rule_type=str(g(row, "Rule type")),
                products=str(g(row, "Products covered")),
                notes=str(g(row, "Exclusions / notes")),
                limit_basis=str(g(row, "Limit basis")),
                limit_value=float(value) if value not in (None, "") else None,
                limit_unit=str(g(row, "Limit unit")),
                test_basis=str(g(row, "Test basis")),
                effective=_to_date(g(row, "Effective date", None)),
                severe_wet=str(g(row, "Severe-wet outdoor apparel")),
                duties=str(g(row, "Duties (certificate / label / report)")),
                confidence=str(g(row, "Confidence")),
                scope=frozenset(s.strip() for s in str(g(row, "Scope codes")).split(",") if s.strip()),
                limit_kind=str(g(row, "Limit kind", "tbd")).strip() or "tbd",
                sources=tuple(src[k.strip()] for k in str(g(row, "Sources")).split(";") if k.strip() in src),
            )
        )
    return rules


def applicable(rules, jurisdiction: str, category: str, severe_wet: bool, as_of: dt.date):
    """Rules for one jurisdiction that are in force on `as_of` and cover the product.

    When several in-force limit rules of the same kind apply (e.g. CA 100 ppm then 50 ppm),
    only the most recent one is kept, since it supersedes the earlier threshold.
    """
    hits = [
        r for r in rules
        if r.jurisdiction == jurisdiction and r.in_force(as_of) and r.applies_to(category, severe_wet)
    ]
    latest: dict[tuple, Rule] = {}
    others = []
    for r in hits:
        if r.is_limit:
            key = (r.limit_kind,)
            if key not in latest or r.effective > latest[key].effective:
                latest[key] = r
        else:
            others.append(r)
    return sorted(latest.values(), key=lambda r: r.rule_id) + sorted(others, key=lambda r: r.rule_id)
