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
    assert c.post(f"/api/audits/{i}/results/confirm-all").status_code == 422  # reviewer required
    assert c.post(f"/api/audits/{i}/results/confirm-all", params={"reviewer": "Anu"}).json()["confirmed"] == 5

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


def test_client_report_has_evidence_sources_and_audit_trail():
    i = new_audit("Report Co")
    c.post(f"/api/audits/{i}/load-sample")
    pdf = (ROOT / "samples" / "pdfs" / "labx_R-002_tof.pdf").read_bytes()
    c.post(f"/api/audits/{i}/results/pdf", files={"file": ("labx.pdf", pdf, "application/pdf")})
    row = next(x for x in c.get(f"/api/audits/{i}").json()["results"] if x["status"] == "needs_review")
    assert c.patch(f"/api/audits/{i}/results/{row['id']}", json={"status": "confirmed"}).status_code == 422
    ok = c.patch(f"/api/audits/{i}/results/{row['id']}", json={"status": "confirmed", "reviewer": "Anu"}).json()
    assert ok["confirmed_by"] == "Anu" and ok["confirmed_at"]
    html = c.get(f"/api/audits/{i}/client-report.html",
                 params={"as_of": "2026-10-30", "lookahead": "2027-01-01", "prepared_by": "Anu, PFAS Copilot"}).text
    for section in ("Executive summary", "Findings that need action", "Action plan", "Methodology",
                    "Limitations", "Appendix A. Lab evidence", "Appendix B. Rules applied and sources", "Appendix C. Change log"):
        assert section in html
    assert "DRAFT" in html and "morganlewis.com" in html and "Anu, PFAS Copilot" in html
    assert "awaiting review" in html  # the other PDF row is still pending
    final = c.get(f"/api/audits/{i}/client-report.html", params={"final": "true"}).text
    assert "DRAFT — FOR REVIEW" not in final
    actions = [e["action"] for e in c.get(f"/api/audits/{i}").json()["events"]]
    assert "upload lab PDF" in actions and "confirmed" in actions


def test_rules_carry_sources():
    rules = c.get("/api/rules").json()
    assert all(r["sources"] for r in rules)


def test_excel_uploads_and_templates():
    import io
    from openpyxl import load_workbook
    i = new_audit("Excel Co")
    for name in ("products", "materials", "lab_results"):
        r = c.get(f"/api/templates/{name}.xlsx")
        assert r.status_code == 200 and r.content[:2] == b"PK"
        assert load_workbook(io.BytesIO(r.content)).active.max_row > 1
    xp = c.get("/api/templates/products.xlsx").content
    xm = c.get("/api/templates/materials.xlsx").content
    xr = c.get("/api/templates/lab_results.xlsx").content
    assert c.post(f"/api/audits/{i}/products", files={"file": ("p.xlsx", xp)}).json()["imported"] == 4
    assert c.post(f"/api/audits/{i}/materials", files={"file": ("m.xlsx", xm)}).json()["imported"] == 6
    assert c.post(f"/api/audits/{i}/results/csv", files={"file": ("r.xlsx", xr)}).json()["imported"] == 6
    e = c.get(f"/api/audits/{i}/evaluate", params={"as_of": "2026-10-30"}).json()
    kt = next(p for p in e["dates"][0]["products"] if p["sku"] == "KT-300")
    assert kt["by_market"]["California"] == "Fail"


def test_headers_are_normalized():
    i = new_audit("Header Co")
    csv_text = "SKU,Name,Category,Severe Wet,Markets\nA1,Jacket,apparel,yes,California\n"
    assert c.post(f"/api/audits/{i}/products", files={"file": ("p.csv", csv_text)}).json()["imported"] == 1


def test_password_protection(monkeypatch):
    import base64
    import app.main as m
    monkeypatch.setattr(m, "_PW", "s3cret")
    assert c.get("/api/audits").status_code == 401
    assert c.get("/healthz").status_code == 200
    good = base64.b64encode(b"pfas:s3cret").decode()
    assert c.get("/api/audits", headers={"Authorization": f"Basic {good}"}).status_code == 200
    bad = base64.b64encode(b"pfas:nope").decode()
    assert c.get("/api/audits", headers={"Authorization": f"Basic {bad}"}).status_code == 401
