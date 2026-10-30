"""PFAS Copilot web app: FastAPI backend + static single-page UI."""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import re
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pfas_copilot.audit import run_audit
from pfas_copilot.models import CATEGORIES, Audit, LabResult, Material, Product, to_ppm
from pfas_copilot.parsers.pdf import parse_pdf
from pfas_copilot.report import render_ca_certificates, render_report
from pfas_copilot.rules import load_rules

from . import db
from .client_report import render_client_report

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).parent / "static"
SAMPLES = ROOT / "samples"
RULES = load_rules()

app = FastAPI(title="PFAS Copilot", version="0.3.0")
db.init()


# ---------------------------------------------------------------- helpers
def _audit_or_404(con, audit_id: int) -> dict:
    a = db.rows(con, "SELECT * FROM audits WHERE id=?", audit_id)
    if not a:
        raise HTTPException(404, "Audit not found")
    return a[0]


def _csv_rows(data: bytes) -> list[dict]:
    text = data.decode("utf-8-sig")
    return [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(io.StringIO(text))]


def _require(row: dict, cols: list[str], line: int):
    missing = [c for c in cols if not row.get(c)]
    if missing:
        raise HTTPException(422, f"Row {line}: missing {', '.join(missing)}")


def _yes(v) -> bool:
    return str(v).strip().lower() in {"y", "yes", "true", "1"}


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(t) > 2}


def guess_material(con, audit_id: int, description: str, sample_ref: str) -> tuple[Optional[str], float]:
    """Best-matching material for a lab sample description (token overlap)."""
    mats = db.rows(con, """SELECT m.*, p.name AS pname FROM materials m JOIN products p
                           ON p.audit_id=m.audit_id AND p.sku=m.sku WHERE m.audit_id=?""", audit_id)
    want = _tokens(description) | _tokens(sample_ref)
    best, score = None, 0.0
    for m in mats:
        have = _tokens(" ".join([m["component"] or "", m["material_type"] or "", m["finish"] or "",
                                 m["pname"] or "", m["sku"], m["material_id"]]))
        if not have or not want:
            continue
        s = len(want & have) / len(want | have)
        if s > score:
            best, score = m["material_id"], s
    return (best, round(score, 2)) if score >= 0.15 else (None, round(score, 2))


def build_audit(con, audit_id: int) -> tuple[Audit, int]:
    a = _audit_or_404(con, audit_id)
    products = [Product(r["sku"], r["name"], r["category"], bool(r["severe_wet"]), json.loads(r["markets"]))
                for r in db.rows(con, "SELECT * FROM products WHERE audit_id=? ORDER BY sku", audit_id)]
    materials = [Material(r["material_id"], r["sku"], r["component"] or "", r["material_type"] or "",
                          r["finish"] or "", r["supplier"] or "", r["declared_intentional"] or "unknown")
                 for r in db.rows(con, "SELECT * FROM materials WHERE audit_id=? ORDER BY material_id", audit_id)]
    res = db.rows(con, "SELECT * FROM results WHERE audit_id=?", audit_id)
    results = [LabResult(r["material_id"], r["lab"] or "", r["report_id"] or "", r["method"] or "", r["analyte"],
                         r["value_ppm"], r["loq_ppm"], r["uncertainty_rel"],
                         dt.date.fromisoformat(r["result_date"]) if r["result_date"] else None, bool(r["below_loq"]))
               for r in res if r["status"] == "confirmed" and r["material_id"]]
    pending = sum(1 for r in res if r["status"] == "needs_review")
    return Audit(a["brand"], products, materials, results), pending


# ---------------------------------------------------------------- models
class AuditIn(BaseModel):
    brand: str
    notes: str = ""


class ResultPatch(BaseModel):
    material_id: Optional[str] = None
    value_ppm: Optional[float] = None
    below_loq: Optional[bool] = None
    loq_ppm: Optional[float] = None
    uncertainty_rel: Optional[float] = None
    status: Optional[str] = None
    reviewer: Optional[str] = None


class MaterialPatch(BaseModel):
    declared_intentional: str
    reviewer: Optional[str] = None


# ---------------------------------------------------------------- rules
@app.get("/api/rules")
def get_rules():
    return [dict(id=r.rule_id, jurisdiction=r.jurisdiction, law=r.law, type=r.rule_type, products=r.products,
                 limit_value=r.limit_value, limit_unit=r.limit_unit, effective=r.effective.isoformat() if r.effective else None,
                 kind=r.limit_kind, scope=sorted(r.scope), duties=r.duties, confidence=r.confidence,
                 sources=[{"title": t, "url": u} for t, u in r.sources]) for r in RULES]


@app.get("/api/markets")
def get_markets():
    return sorted({r.jurisdiction for r in RULES})


# ---------------------------------------------------------------- audits
@app.get("/api/audits")
def list_audits():
    with db.tx() as con:
        return db.rows(con, """SELECT a.*, (SELECT COUNT(*) FROM products p WHERE p.audit_id=a.id) AS n_products,
                               (SELECT COUNT(*) FROM results r WHERE r.audit_id=a.id) AS n_results,
                               (SELECT COUNT(*) FROM results r WHERE r.audit_id=a.id AND r.status='needs_review') AS n_review
                               FROM audits a ORDER BY a.id DESC""")


@app.post("/api/audits", status_code=201)
def create_audit(body: AuditIn):
    if not body.brand.strip():
        raise HTTPException(422, "Brand name is required")
    with db.tx() as con:
        cur = con.execute("INSERT INTO audits (brand, notes) VALUES (?, ?)", (body.brand.strip(), body.notes))
        return {"id": cur.lastrowid, "brand": body.brand.strip()}


@app.get("/api/audits/{audit_id}")
def get_audit(audit_id: int):
    with db.tx() as con:
        a = _audit_or_404(con, audit_id)
        a["products"] = db.rows(con, "SELECT * FROM products WHERE audit_id=? ORDER BY sku", audit_id)
        for p in a["products"]:
            p["markets"] = json.loads(p["markets"])
        a["materials"] = db.rows(con, "SELECT * FROM materials WHERE audit_id=? ORDER BY material_id", audit_id)
        a["documents"] = db.rows(con, "SELECT * FROM documents WHERE audit_id=? ORDER BY id DESC", audit_id)
        a["results"] = db.rows(con, "SELECT * FROM results WHERE audit_id=? ORDER BY status DESC, id", audit_id)
        a["events"] = db.rows(con, "SELECT * FROM events WHERE audit_id=? ORDER BY id DESC LIMIT 200", audit_id)
        return a


@app.delete("/api/audits/{audit_id}", status_code=204)
def delete_audit(audit_id: int):
    with db.tx() as con:
        _audit_or_404(con, audit_id)
        con.execute("DELETE FROM audits WHERE id=?", (audit_id,))


# ---------------------------------------------------------------- uploads
@app.post("/api/audits/{audit_id}/products")
async def upload_products(audit_id: int, file: UploadFile = File(...)):
    return import_products(audit_id, await file.read())


def import_products(audit_id: int, data: bytes):
    rows = _csv_rows(data)
    known = {r.jurisdiction for r in RULES}
    clean, warnings = [], []
    for i, r in enumerate(rows, start=2):
        _require(r, ["sku", "name", "category", "markets"], i)
        cat = r["category"].lower()
        if cat not in CATEGORIES:
            raise HTTPException(422, f"Row {i}: category must be one of {sorted(CATEGORIES)}")
        markets = [m.strip() for m in r["markets"].split(";") if m.strip()]
        warnings += [f"{r['sku']}: no rules tracked for {m!r}" for m in markets if m not in known]
        clean.append((audit_id, r["sku"], r["name"], cat, int(_yes(r.get("severe_wet", ""))), json.dumps(markets)))
    with db.tx() as con:
        _audit_or_404(con, audit_id)
        con.execute("DELETE FROM products WHERE audit_id=?", (audit_id,))
        con.executemany("INSERT INTO products VALUES (?,?,?,?,?,?)", clean)
        db.log(con, audit_id, "upload products", f"{len(clean)} SKU(s)")
    return {"imported": len(clean), "warnings": warnings}


@app.post("/api/audits/{audit_id}/materials")
async def upload_materials(audit_id: int, file: UploadFile = File(...)):
    return import_materials(audit_id, await file.read())


def import_materials(audit_id: int, data: bytes):
    rows = _csv_rows(data)
    with db.tx() as con:
        _audit_or_404(con, audit_id)
        skus = {r["sku"] for r in db.rows(con, "SELECT sku FROM products WHERE audit_id=?", audit_id)}
        clean = []
        for i, r in enumerate(rows, start=2):
            _require(r, ["material_id", "sku"], i)
            if r["sku"] not in skus:
                raise HTTPException(422, f"Row {i}: SKU {r['sku']!r} is not in the product list; upload products first")
            decl = (r.get("declared_intentional") or "unknown").lower()
            if decl not in {"yes", "no", "unknown"}:
                raise HTTPException(422, f"Row {i}: declared_intentional must be yes, no or unknown")
            clean.append((audit_id, r["material_id"], r["sku"], r.get("component", ""), r.get("material_type", ""),
                          r.get("finish", ""), r.get("supplier", ""), decl))
        con.execute("DELETE FROM materials WHERE audit_id=?", (audit_id,))
        con.executemany("INSERT INTO materials VALUES (?,?,?,?,?,?,?,?)", clean)
        db.log(con, audit_id, "upload materials", f"{len(clean)} material(s)")
    return {"imported": len(clean)}


@app.post("/api/audits/{audit_id}/results/csv")
async def upload_results_csv(audit_id: int, file: UploadFile = File(...)):
    return import_results_csv(audit_id, await file.read(), file.filename or "results.csv")


def import_results_csv(audit_id: int, data: bytes, filename: str):
    rows = _csv_rows(data)
    with db.tx() as con:
        _audit_or_404(con, audit_id)
        mats = {r["material_id"] for r in db.rows(con, "SELECT material_id FROM materials WHERE audit_id=?", audit_id)}
        cur = con.execute("INSERT INTO documents (audit_id, filename, kind) VALUES (?,?,?)",
                          (audit_id, filename, "csv"))
        doc_id, n = cur.lastrowid, 0
        for i, r in enumerate(rows, start=2):
            _require(r, ["material_id", "analyte", "result", "unit"], i)
            if r["material_id"] not in mats:
                raise HTTPException(422, f"Row {i}: unknown material {r['material_id']!r}")
            raw = r["result"].upper()
            below = raw.startswith("<") or raw in {"ND", "NOT DETECTED"}
            try:
                val = None if below else to_ppm(float(raw), r["unit"])
                loq = to_ppm(float(r["loq"]), r["unit"]) if r.get("loq") else None
            except ValueError as e:
                raise HTTPException(422, f"Row {i}: {e}")
            unc = float(r["uncertainty_pct"]) / 100 if r.get("uncertainty_pct") else None
            con.execute("""INSERT INTO results (audit_id, document_id, material_id, lab, report_id, method, analyte,
                           value_ppm, below_loq, loq_ppm, uncertainty_rel, result_date, raw_result, status, confirmed_by, confirmed_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, 'confirmed', 'CSV import', datetime('now'))""",
                        (audit_id, doc_id, r["material_id"], r.get("lab", ""), r.get("report_id", ""), r.get("method", ""),
                         r["analyte"], val, int(below), loq, unc, r.get("date") or None, r["result"]))
            n += 1
        db.log(con, audit_id, "upload results CSV", f"{filename}: {n} result(s), imported as confirmed")
    return {"imported": n, "document_id": doc_id}


@app.post("/api/audits/{audit_id}/results/pdf")
async def upload_results_pdf(audit_id: int, file: UploadFile = File(...)):
    data = await file.read()
    if not data.startswith(b"%PDF"):
        raise HTTPException(422, "That file is not a PDF")
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(data)
        tmp.flush()
        rep = parse_pdf(tmp.name)
    rep.filename = file.filename or rep.filename
    with db.tx() as con:
        _audit_or_404(con, audit_id)
        cur = con.execute("""INSERT INTO documents (audit_id, filename, kind, lab, report_id, report_date, method,
                             uncertainty_rel, layout, warnings) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                          (audit_id, rep.filename, "pdf", rep.lab, rep.report_id,
                           rep.date.isoformat() if rep.date else None, rep.method, rep.uncertainty_rel,
                           rep.layout, json.dumps(rep.warnings)))
        doc_id = cur.lastrowid
        cache: dict[str, tuple] = {}
        for r in rep.rows:
            key = r.sample_ref + "|" + r.description
            if key not in cache:
                cache[key] = guess_material(con, audit_id, r.description, r.sample_ref)
            mid, score = cache[key]
            notes = list(r.notes) + ([f"Matched to {mid} (score {score})"] if mid else ["No material match; pick one"])
            con.execute("""INSERT INTO results (audit_id, document_id, material_id, sample_ref, description, lab,
                           report_id, method, analyte, value_ppm, below_loq, loq_ppm, uncertainty_rel, result_date,
                           raw_result, confidence, notes, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'needs_review')""",
                        (audit_id, doc_id, mid, r.sample_ref, r.description, rep.lab, rep.report_id, rep.method,
                         r.analyte, r.value_ppm, int(r.below_loq), r.loq_ppm, rep.uncertainty_rel,
                         rep.date.isoformat() if rep.date else None, r.raw_result, r.confidence, "; ".join(notes)))
        db.log(con, audit_id, "upload lab PDF", f"{rep.filename}: {len(rep.rows)} result(s) read, waiting for review")
    return {"document_id": doc_id, "rows": len(rep.rows), "lab": rep.lab, "report_id": rep.report_id,
            "layout": rep.layout, "warnings": rep.warnings}


@app.patch("/api/audits/{audit_id}/results/{rid}")
def patch_result(audit_id: int, rid: int, body: ResultPatch):
    fields = body.model_dump(exclude_unset=True)
    reviewer = (fields.pop("reviewer", None) or "").strip()
    if "status" in fields and fields["status"] not in {"confirmed", "needs_review", "rejected"}:
        raise HTTPException(422, "Invalid status")
    with db.tx() as con:
        r = db.rows(con, "SELECT * FROM results WHERE id=? AND audit_id=?", rid, audit_id)
        if not r:
            raise HTTPException(404, "Result not found")
        if fields.get("status") == "confirmed" and not (fields.get("material_id") or r[0]["material_id"]):
            raise HTTPException(422, "Assign a material before confirming")
        if "material_id" in fields and fields["material_id"]:
            ok = db.rows(con, "SELECT 1 FROM materials WHERE audit_id=? AND material_id=?", audit_id, fields["material_id"])
            if not ok:
                raise HTTPException(422, "Unknown material")
        if "below_loq" in fields:
            fields["below_loq"] = int(fields["below_loq"])
        if fields.get("status") == "confirmed":
            if not reviewer:
                raise HTTPException(422, "Enter your name as reviewer before confirming results")
            fields["confirmed_by"] = reviewer
            fields["confirmed_at"] = dt.datetime.now().isoformat(timespec="seconds")
        old = r[0]
        if fields:
            sets = ", ".join(f"{k}=?" for k in fields)
            con.execute(f"UPDATE results SET {sets} WHERE id=?", (*fields.values(), rid))
            label = f"result #{rid} ({old['analyte']}, {old['material_id'] or old['sample_ref']})"
            if "value_ppm" in fields and fields["value_ppm"] != old["value_ppm"]:
                db.log(con, audit_id, "edit value", f"{label}: {old['value_ppm']} -> {fields['value_ppm']} ppm", reviewer)
            if "material_id" in fields and fields["material_id"] != old["material_id"]:
                db.log(con, audit_id, "assign material", f"{label}: -> {fields['material_id']}", reviewer)
            if "status" in fields and fields["status"] != old["status"]:
                db.log(con, audit_id, fields["status"], label, reviewer)
        return db.rows(con, "SELECT * FROM results WHERE id=?", rid)[0]


@app.post("/api/audits/{audit_id}/results/confirm-all")
def confirm_all(audit_id: int, document_id: Optional[int] = None, reviewer: str = ""):
    if not reviewer.strip():
        raise HTTPException(422, "Enter your name as reviewer before confirming results")
    with db.tx() as con:
        _audit_or_404(con, audit_id)
        now = dt.datetime.now().isoformat(timespec="seconds")
        q = ("UPDATE results SET status='confirmed', confirmed_by=?, confirmed_at=? "
             "WHERE audit_id=? AND status='needs_review' AND material_id IS NOT NULL")
        args = [reviewer.strip(), now, audit_id]
        if document_id:
            q += " AND document_id=?"
            args.append(document_id)
        n = con.execute(q, args).rowcount
        db.log(con, audit_id, "confirm all", f"{n} result(s)", reviewer.strip())
    return {"confirmed": n}


@app.delete("/api/audits/{audit_id}/results/{rid}", status_code=204)
def delete_result(audit_id: int, rid: int):
    with db.tx() as con:
        con.execute("DELETE FROM results WHERE id=? AND audit_id=?", (rid, audit_id))


@app.patch("/api/audits/{audit_id}/materials/{material_id}")
def patch_material(audit_id: int, material_id: str, body: MaterialPatch):
    if body.declared_intentional not in {"yes", "no", "unknown"}:
        raise HTTPException(422, "declared_intentional must be yes, no or unknown")
    with db.tx() as con:
        n = con.execute("UPDATE materials SET declared_intentional=? WHERE audit_id=? AND material_id=?",
                        (body.declared_intentional, audit_id, material_id)).rowcount
        if not n:
            raise HTTPException(404, "Material not found")
        db.log(con, audit_id, "supplier declaration", f"{material_id}: {body.declared_intentional}", body.reviewer or "")
    return {"ok": True}


@app.post("/api/audits/{audit_id}/load-sample")
def load_sample(audit_id: int):
    """Fill an audit with the bundled sample brand (for demos)."""
    with db.tx() as con:
        _audit_or_404(con, audit_id)
        for t in ("results", "documents", "materials", "products"):
            con.execute(f"DELETE FROM {t} WHERE audit_id=?", (audit_id,))
    import_products(audit_id, (SAMPLES / "products.csv").read_bytes())
    import_materials(audit_id, (SAMPLES / "materials.csv").read_bytes())
    import_results_csv(audit_id, (SAMPLES / "lab_results.csv").read_bytes(), "lab_results.csv")
    return {"ok": True}


# ---------------------------------------------------------------- evaluation
def _evaluate(audit_id: int, as_of: Optional[str], lookahead: Optional[str]):
    d0 = dt.date.fromisoformat(as_of) if as_of else dt.date.today()
    d1 = dt.date.fromisoformat(lookahead) if lookahead else None
    with db.tx() as con:
        audit, pending = build_audit(con, audit_id)
    if not audit.products:
        raise HTTPException(409, "Upload a product list first")
    return run_audit(audit, RULES, d0, d1), pending


@app.get("/api/audits/{audit_id}/evaluate")
def evaluate(audit_id: int, as_of: Optional[str] = None, lookahead: Optional[str] = None):
    res, pending = _evaluate(audit_id, as_of, lookahead)
    rules = {r.rule_id: r for r in RULES}
    mats = {m.material_id: m for m in res.audit.materials}
    markets = sorted({m for p in res.audit.products for m in p.markets})
    out = {"markets": markets, "pending_review": pending, "warnings": res.warnings, "dates": []}
    for d in res.dates:
        counts: dict[str, int] = {}
        prods = []
        for pr in res.results[d]:
            for v in pr.by_market.values():
                counts[v] = counts.get(v, 0) + 1
            prods.append({
                "sku": pr.product.sku, "name": pr.product.name, "severe_wet": pr.product.severe_wet,
                "by_market": pr.by_market,
                "verdicts": [{"material_id": v.material_id, "component": mats[v.material_id].component,
                              "material_type": mats[v.material_id].material_type, "rule_id": v.rule_id,
                              "jurisdiction": v.jurisdiction, "verdict": v.verdict, "reason": v.reason,
                              "law": rules[v.rule_id].law, "confidence": rules[v.rule_id].confidence,
                              "sources": [{"title": t, "url": u} for t, u in rules[v.rule_id].sources]}
                             for v in pr.verdicts]})
        out["dates"].append({"date": d.isoformat(), "counts": counts, "products": prods})
    out["test_plan"] = [s.__dict__ for s in res.test_plan]
    out["risk"] = res.risk
    out["deadlines"] = [{"date": r.effective.isoformat(), "rule_id": r.rule_id, "jurisdiction": r.jurisdiction,
                         "type": r.rule_type, "products": r.products, "limit_value": r.limit_value,
                         "limit_unit": r.limit_unit, "confidence": r.confidence,
                         "sources": [{"title": t, "url": u} for t, u in r.sources]}
                        for r in sorted((r for r in RULES if r.effective and r.jurisdiction in markets
                                         and r.effective >= res.dates[0] - dt.timedelta(days=730)),
                                        key=lambda r: r.effective)]
    return out


@app.get("/api/audits/{audit_id}/report.html", response_class=HTMLResponse)
def report(audit_id: int, as_of: Optional[str] = None, lookahead: Optional[str] = None):
    res, _ = _evaluate(audit_id, as_of, lookahead)
    return render_report(res)


@app.get("/api/audits/{audit_id}/client-report.html", response_class=HTMLResponse)
def client_report(audit_id: int, as_of: Optional[str] = None, lookahead: Optional[str] = None,
                  prepared_by: str = "", final: bool = False):
    res, _ = _evaluate(audit_id, as_of, lookahead)
    with db.tx() as con:
        docs = db.rows(con, "SELECT * FROM documents WHERE audit_id=? ORDER BY id", audit_id)
        results = db.rows(con, "SELECT * FROM results WHERE audit_id=? ORDER BY material_id, analyte", audit_id)
        events = db.rows(con, "SELECT * FROM events WHERE audit_id=? ORDER BY id", audit_id)
    return render_client_report(res, docs, results, events, prepared_by=prepared_by, final=final)


@app.get("/api/audits/{audit_id}/certificates.md", response_class=PlainTextResponse)
def certificates(audit_id: int, as_of: Optional[str] = None, lookahead: Optional[str] = None, signatory: str = "[Name, title]"):
    res, _ = _evaluate(audit_id, as_of, lookahead)
    return render_ca_certificates(res, signatory)


# ---------------------------------------------------------------- templates + UI
@app.get("/api/templates/{name}")
def template(name: str):
    files = {"products.csv": "products.csv", "materials.csv": "materials.csv", "lab_results.csv": "lab_results.csv"}
    if name not in files:
        raise HTTPException(404)
    return FileResponse(SAMPLES / files[name], media_type="text/csv", filename=name)


@app.get("/healthz")
def healthz():
    return {"ok": True, "rules": len(RULES)}


app.mount("/", StaticFiles(directory=STATIC, html=True), name="ui")
