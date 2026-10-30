"""Core data objects and CSV loaders."""
from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

CATEGORIES = {"apparel", "accessories", "footwear", "home_textiles"}


def _yes(v: str) -> bool:
    return str(v).strip().lower() in {"y", "yes", "true", "1"}


@dataclass
class Product:
    sku: str
    name: str
    category: str
    severe_wet: bool
    markets: list[str]


@dataclass
class Material:
    material_id: str
    sku: str
    component: str
    material_type: str
    finish: str
    supplier: str
    declared_intentional: str = "unknown"  # yes / no / unknown (supplier declaration)


@dataclass
class LabResult:
    material_id: str
    lab: str
    report_id: str
    method: str
    analyte: str  # TOF, TF, or a specific PFAS such as PFHxA
    value: float | None  # in ppm (mg/kg); None when below LOQ
    loq: float | None
    uncertainty_rel: float | None  # expanded uncertainty as a fraction, e.g. 0.2
    date: dt.date | None
    below_loq: bool = False


@dataclass
class Audit:
    brand: str
    products: list[Product]
    materials: list[Material]
    results: list[LabResult] = field(default_factory=list)

    def materials_for(self, sku: str) -> list[Material]:
        return [m for m in self.materials if m.sku == sku]

    def results_for(self, material_id: str) -> list[LabResult]:
        return [r for r in self.results if r.material_id == material_id]


def _rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def load_products(path: str | Path) -> list[Product]:
    out = []
    for r in _rows(path):
        cat = r["category"].lower()
        if cat not in CATEGORIES:
            raise ValueError(f"{r['sku']}: unknown category {cat!r}; use one of {sorted(CATEGORIES)}")
        out.append(Product(r["sku"], r["name"], cat, _yes(r.get("severe_wet", "")),
                           [m.strip() for m in r["markets"].split(";") if m.strip()]))
    return out


def load_materials(path: str | Path) -> list[Material]:
    return [
        Material(r["material_id"], r["sku"], r["component"], r["material_type"], r.get("finish", ""),
                 r.get("supplier", ""), (r.get("declared_intentional") or "unknown").lower())
        for r in _rows(path)
    ]


def to_ppm(value: float, unit: str) -> float:
    u = unit.lower().replace(" ", "")
    if u in {"ppm", "mg/kg", "mgf/kg", "µg/g", "ug/g"}:
        return value
    if u in {"ppb", "µg/kg", "ug/kg", "ng/g"}:
        return value / 1000.0
    raise ValueError(f"Unknown unit {unit!r}")


def load_results(path: str | Path) -> list[LabResult]:
    """CSV columns: material_id, lab, report_id, method, analyte, result, unit, loq, uncertainty_pct, date.

    `result` may be a number or '<LOQ' / 'ND'.
    """
    out = []
    for r in _rows(path):
        unit = r["unit"]
        raw = r["result"].upper()
        below = raw.startswith("<") or raw in {"ND", "NOT DETECTED"}
        value = None if below else to_ppm(float(raw), unit)
        loq = to_ppm(float(r["loq"]), unit) if r.get("loq") else None
        unc = float(r["uncertainty_pct"]) / 100 if r.get("uncertainty_pct") else None
        date = dt.date.fromisoformat(r["date"]) if r.get("date") else None
        out.append(LabResult(r["material_id"], r.get("lab", ""), r.get("report_id", ""), r.get("method", ""),
                             r["analyte"].strip(), value, loq, unc, date, below))
    return out
