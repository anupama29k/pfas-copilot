import os
import tempfile
from pathlib import Path

os.environ["PFAS_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
c = TestClient(app)


def new_audit(brand="Test Co"):
    return c.post("/api/audits", json={"brand": brand}).json()["id"]


def test_health_and_rules():
    assert c.get("/healthz").json()["rules"] >= 30
    assert any(r["id"] == "CA-2" for r in c.get("/api/rules").json())


def test_full_flow_csv_then_pdf_review():
    i = new_audit()
    up = lambda path, name: c.post(f"/api/audits/{i}/{path}", files={"file": (name, (ROOT / "samples" / name).read_bytes())})
    assert up("products", "products.csv").json()["imported"] == 4
    assert up("materials", "materials.csv").json()["imported"] == 6
    assert up("results/csv", "lab_results.csv").json()["imported"] == 6

    pdf = (ROOT / "samples" / "pdfs" / "laby_LY-2026-0457_targeted.pdf").read_bytes()
    r = c.post(f"/api/audits/{i}/results/pdf", files={"file": ("laby.pdf", pdf, "application/pdf")}).json()
    assert r["rows"] == 5
    pending = [x for x in c.get(f"/api/audits/{i}").json()["results"] if x["status"] == "needs_review"]
    assert {x["material_id"] for x in pending} == {"M1", "M5"}  # matched by description

    e = c.get(f"/api/audits/{i}/evaluate", params={"as_of": "2026-10-30", "lookahead": "2027-01-01"}).json()
    assert e["pending_review"] == 5
    assert c.post(f"/api/audits/{i}/results/confirm-all").json()["confirmed"] == 5

    e = c.get(f"/api/audits/{i}/evaluate", params={"as_of": "2026-10-30", "lookahead": "2027-01-01"}).json()
    now, jan = ({p["sku"]: p["by_market"] for p in d["products"]} for d in e["dates"])
    assert now["SH-200"]["California"] == "Pass" and jan["SH-200"]["California"] == "At risk"
    assert now["KT-300"]["California"] == "Fail"
    assert c.get(f"/api/audits/{i}/report.html").status_code == 200
    assert "SH-200" in c.get(f"/api/audits/{i}/certificates.md", params={"as_of": "2026-10-30"}).text


def test_editing_a_value_changes_the_verdict():
    i = new_audit()
    c.post(f"/api/audits/{i}/load-sample")
    res = c.get(f"/api/audits/{i}").json()["results"]
    m3 = next(r for r in res if r["material_id"] == "M3")
    c.patch(f"/api/audits/{i}/results/{m3['id']}", json={"value_ppm": 30})
    e = c.get(f"/api/audits/{i}/evaluate", params={"as_of": "2027-01-01"}).json()
    sh = next(p for p in e["dates"][0]["products"] if p["sku"] == "SH-200")
    assert sh["by_market"]["California"] == "Pass"


def test_validation_errors():
    i = new_audit()
    bad = "sku,name,category,severe_wet,markets\nX,Thing,hats,no,California\n"
    r = c.post(f"/api/audits/{i}/products", files={"file": ("p.csv", bad)})
    assert r.status_code == 422 and "category" in r.json()["detail"]
    r = c.post(f"/api/audits/{i}/results/pdf", files={"file": ("x.pdf", b"not a pdf")})
    assert r.status_code == 422
    assert c.get(f"/api/audits/{i}/evaluate").status_code == 409
    assert c.get("/api/audits/99999").status_code == 404


def test_cannot_confirm_without_material():
    i = new_audit()
    c.post(f"/api/audits/{i}/load-sample")
    pdf = (ROOT / "samples" / "pdfs" / "labx_R-002_tof.pdf").read_bytes()
    c.post(f"/api/audits/{i}/results/pdf", files={"file": ("labx.pdf", pdf, "application/pdf")})
    row = next(x for x in c.get(f"/api/audits/{i}").json()["results"] if x["status"] == "needs_review")
    c.patch(f"/api/audits/{i}/results/{row['id']}", json={"material_id": None})
    r = c.patch(f"/api/audits/{i}/results/{row['id']}", json={"status": "confirmed"})
    assert r.status_code == 422
