"""Extract PFAS results from lab-report PDFs.

Strategy (lab-agnostic):
1. Pull report-level metadata from the text with regexes: lab name, report id, date,
   method, expanded uncertainty.
2. Find result tables and map their columns by header keywords. Two layouts are handled:
   - long:  one row per sample x analyte (columns: sample, analyte, result, unit, LOQ/RL)
   - wide:  one row per sample, one column per analyte ("TOF (mg/kg)", "PFHxA µg/kg")
3. Normalize analyte names and units (everything to ppm = mg/kg).

Every parsed row is returned with `confidence` and is meant to be reviewed by a person
before it counts in an audit.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

ANALYTES = [
    (r"total\s+organic\s+fluorine|\btof\b", "TOF"),
    (r"total\s+fluorine|\btf\b", "TF"),
    (r"extractable\s+organic\s+fluorine|\beof\b", "EOF"),
    (r"\bpfhxa\b|perfluorohexanoic", "PFHxA"),
    (r"\bpfoa\b|perfluorooctanoic", "PFOA"),
    (r"\bpfos\b|perfluorooctane\s*sulfon", "PFOS"),
    (r"\bpfna\b", "PFNA"),
    (r"\bpfda\b", "PFDA"),
    (r"\bpfbs\b", "PFBS"),
    (r"6:2\s*ftoh", "6:2 FTOH"),
    (r"8:2\s*ftoh", "8:2 FTOH"),
]
UNIT_RE = re.compile(r"(mg\s*/\s*kg|µg\s*/\s*kg|ug\s*/\s*kg|ng\s*/\s*g|ppm|ppb|mg\s*f\s*/\s*kg)", re.I)
TO_PPM = {"mg/kg": 1.0, "ppm": 1.0, "mgf/kg": 1.0, "µg/kg": 1e-3, "ug/kg": 1e-3, "ng/g": 1e-3, "ppb": 1e-3}


@dataclass
class ParsedRow:
    sample_ref: str
    description: str
    analyte: str
    value_ppm: float | None
    below_loq: bool
    loq_ppm: float | None
    unit_raw: str
    raw_result: str
    confidence: float = 0.9
    notes: list[str] = field(default_factory=list)


@dataclass
class ParsedReport:
    filename: str
    lab: str = ""
    report_id: str = ""
    date: dt.date | None = None
    method: str = ""
    uncertainty_rel: float | None = None
    layout: str = ""
    rows: list[ParsedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def norm_analyte(text: str) -> str | None:
    t = text.lower()
    for pat, name in ANALYTES:
        if re.search(pat, t):
            return name
    return None


def norm_unit(text: str) -> str | None:
    m = UNIT_RE.search(text or "")
    if not m:
        return None
    u = re.sub(r"\s+", "", m.group(1).lower()).replace("µ", "µ")
    return {"mgf/kg": "mgf/kg"}.get(u, u)


def parse_number(s: str):
    """Return (value, below_loq). '<5', '< LOQ', 'ND', 'n.d.' count as below LOQ."""
    t = (s or "").strip()
    if not t:
        return None, False
    if re.match(r"^(<|nd\b|n\.d\.|not\s+detected|bdl|<\s*loq|<\s*rl)", t, re.I):
        return None, True
    m = re.search(r"-?\d+(?:[.,]\d+)?", t)
    if not m:
        return None, False
    return float(m.group(0).replace(",", ".")), False


def _meta(text: str, rep: ParsedReport):
    first = [l.strip() for l in text.splitlines() if l.strip()]
    if first:
        rep.lab = re.sub(r"\s{2,}.*", "", first[0])[:80]
    m = re.search(r"(?:test\s+)?report\s*(?:no\.?|number|#|id)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{2,})", text, re.I)
    if m:
        rep.report_id = m.group(1)
    m = re.search(r"(?:issued|report\s+date|date\s+of\s+issue|date)\s*[:]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})", text, re.I)
    if m:
        d = m.group(1)
        try:
            rep.date = dt.date.fromisoformat(d) if "-" in d else dt.datetime.strptime(d, "%m/%d/%Y").date()
        except ValueError:
            rep.warnings.append(f"Could not read date {d!r}")
    m = re.search(r"method\s*[:]?\s*([^\n]{4,120})", text, re.I)
    if m:
        rep.method = m.group(1).strip().rstrip(".")
    m = re.search(r"(?:expanded\s+)?(?:measurement\s+)?uncertainty[^\n%]{0,40}?(\d{1,2}(?:\.\d)?)\s*%", text, re.I)
    if m:
        rep.uncertainty_rel = float(m.group(1)) / 100


def _find_col(header, *keys):
    for i, h in enumerate(header):
        hl = (h or "").lower()
        if any(k in hl for k in keys):
            return i
    return None


def _parse_table(table, rep: ParsedReport) -> list[ParsedRow]:
    rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in table if r and any(r)]
    if len(rows) < 2:
        return []
    header = rows[0]
    c_sample = _find_col(header, "sample", "lab id", "specimen")
    c_desc = _find_col(header, "description", "material", "article")
    c_analyte = _find_col(header, "analyte", "parameter", "compound", "substance", "test item")
    c_result = _find_col(header, "result", "value", "conc")
    c_unit = _find_col(header, "unit")
    c_loq = _find_col(header, "loq", "rl", "reporting limit", "detection limit", "lod", "mdl")
    out = []
    if c_analyte is not None and c_result is not None:  # long layout
        rep.layout = rep.layout or "long"
        for r in rows[1:]:
            an = norm_analyte(r[c_analyte])
            if not an:
                continue
            unit = norm_unit(r[c_unit]) if c_unit is not None else norm_unit(header[c_result])
            if not unit:
                unit = norm_unit(" ".join(header)) or "mg/kg"
            out.append(_row(r, c_sample, c_desc, an, r[c_result], r[c_loq] if c_loq is not None else "", unit))
        return out
    # wide layout: analyte names live in the headers
    analyte_cols = [(i, norm_analyte(h)) for i, h in enumerate(header) if norm_analyte(h) and i != c_loq]
    if analyte_cols and (c_sample is not None or c_desc is not None):
        rep.layout = rep.layout or "wide"
        for r in rows[1:]:
            for i, an in analyte_cols:
                unit = norm_unit(header[i]) or norm_unit(" ".join(header)) or "mg/kg"
                out.append(_row(r, c_sample, c_desc, an, r[i], r[c_loq] if c_loq is not None else "", unit))
    return out


def _row(r, c_sample, c_desc, analyte, raw, raw_loq, unit) -> ParsedRow:
    factor = TO_PPM.get(unit, 1.0)
    val, below = parse_number(raw)
    loq, _ = parse_number(raw_loq)
    if below and loq is None:
        loq, _ = parse_number(raw.lstrip("<").strip())  # "<5" carries the LOQ
    notes, conf = [], 0.95
    if unit not in TO_PPM:
        notes.append(f"Unknown unit {unit!r}, assumed ppm")
        conf = 0.6
    if val is None and not below:
        notes.append(f"Could not read result {raw!r}")
        conf = 0.3
    return ParsedRow(
        sample_ref=r[c_sample] if c_sample is not None else "",
        description=r[c_desc] if c_desc is not None else "",
        analyte=analyte,
        value_ppm=val * factor if val is not None else None,
        below_loq=below,
        loq_ppm=loq * factor if loq is not None else None,
        unit_raw=unit,
        raw_result=raw,
        confidence=conf,
        notes=notes,
    )


def parse_pdf(path: str | Path) -> ParsedReport:
    path = Path(path)
    rep = ParsedReport(filename=path.name)
    with pdfplumber.open(path) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        _meta(text, rep)
        for page in pdf.pages:
            for table in page.extract_tables():
                rep.rows.extend(_parse_table(table, rep))
    if not text.strip():
        rep.warnings.append("No text layer found: this looks like a scanned PDF (OCR not supported yet)")
    elif not rep.rows:
        rep.warnings.append("No result table recognized; enter results manually or add a parser profile")
    if rep.uncertainty_rel is None and rep.rows:
        rep.warnings.append("No measurement uncertainty stated; the 20% default will be used")
    return rep
