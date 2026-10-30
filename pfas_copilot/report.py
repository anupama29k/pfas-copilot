"""HTML audit report and California certificate-of-compliance drafts."""
from __future__ import annotations

import datetime as dt
import html

from .audit import AuditResult
from .check import FAIL, PASS

COLORS = {"Pass": "#e5f4e4", "Fail": "#fbebeb", "At risk": "#f9ece7", "Declaration required": "#f9eeda",
          "No data": "#f0efec", "No rule in force": "#ffffff", "Obligations only": "#e7f1fb"}

CSS = """body{font-family:Arial,sans-serif;margin:32px;color:#222;max-width:1100px}
h1{margin-bottom:4px}table{border-collapse:collapse;margin:12px 0 24px;width:100%}
th,td{border:1px solid #ddd;padding:6px 8px;font-size:13px;text-align:left;vertical-align:top}
th{background:#1f3a5f;color:#fff}.note{color:#666;font-size:12px}.warn{background:#fff7e0;padding:8px 12px;border-left:4px solid #e0a800}"""


def e(x) -> str:
    return html.escape(str(x))


def render_report(res: AuditResult) -> str:
    a = res.audit
    markets = sorted({m for p in a.products for m in p.markets})
    parts = [f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>PFAS audit: {e(a.brand)}</title>"
             f"<style>{CSS}</style></head><body>",
             f"<h1>PFAS compliance audit: {e(a.brand)}</h1>",
             f"<p class='note'>Generated {dt.date.today().isoformat()} · {len(a.products)} SKUs · "
             f"{len(a.materials)} materials · {len(a.results)} lab results. Draft for expert review; not legal advice.</p>"]
    if res.warnings:
        parts.append("<div class='warn'><b>Warnings</b><ul>" + "".join(f"<li>{e(w)}</li>" for w in res.warnings) + "</ul></div>")

    for d in res.dates:
        parts.append(f"<h2>Verdicts as of {d.isoformat()}</h2><table><tr><th>SKU</th><th>Product</th>"
                     + "".join(f"<th>{e(m)}</th>" for m in markets) + "</tr>")
        for pr in res.results[d]:
            cells = []
            for m in markets:
                val = pr.by_market.get(m, "—")
                cells.append(f"<td style='background:{COLORS.get(val, '#fff')}'>{e(val)}</td>")
            parts.append(f"<tr><td>{e(pr.product.sku)}</td><td>{e(pr.product.name)}"
                         f"{' (severe wet)' if pr.product.severe_wet else ''}</td>{''.join(cells)}</tr>")
        parts.append("</table>")

    parts.append("<h2>Findings by material</h2><table><tr><th>Date</th><th>Material</th><th>Rule</th>"
                 "<th>Verdict</th><th>Reason</th></tr>")
    mats = {m.material_id: m for m in a.materials}
    for d in res.dates:
        for pr in res.results[d]:
            for v in pr.verdicts:
                if v.verdict in (PASS, "Obligation"):
                    continue
                m = mats[v.material_id]
                parts.append(f"<tr><td>{d}</td><td>{e(m.material_id)} · {e(m.component)} ({e(m.material_type)})</td>"
                             f"<td>{e(v.rule_id)}</td><td style='background:{COLORS.get(v.verdict, '#fff')}'>"
                             f"{e(v.verdict)}</td><td>{e(v.reason)}</td></tr>")
    parts.append("</table>")

    oblig = sorted({(v.rule_id, v.reason) for rows in res.results.values() for pr in rows
                    for v in pr.verdicts if v.verdict == "Obligation"})
    if oblig:
        parts.append("<h2>Other obligations (labels, notices, reporting)</h2><ul>"
                     + "".join(f"<li><b>{e(r)}</b>: {e(t)}</li>" for r, t in oblig) + "</ul>")

    lo = sum(s.cost_low for s in res.test_plan)
    hi = sum(s.cost_high for s in res.test_plan)
    parts.append(f"<h2>Test plan ({len(res.test_plan)} tests, est. ${lo:,}–${hi:,})</h2><table><tr><th>Material</th>"
                 "<th>Risk</th><th>Test</th><th>Why</th><th>Est. cost (USD)</th></tr>")
    for s in res.test_plan:
        parts.append(f"<tr><td>{e(s.material_id)}</td><td>{e(s.risk)}</td><td>{e(s.test)}</td><td>{e(s.why)}</td>"
                     f"<td>{s.cost_low}–{s.cost_high}</td></tr>")
    parts.append("</table>")

    upcoming = sorted((r for r in res.rules if r.effective and r.effective > res.dates[0]
                       and r.jurisdiction in markets), key=lambda r: r.effective)
    parts.append("<h2>Upcoming deadlines in your markets</h2><table><tr><th>Date</th><th>Rule</th>"
                 "<th>What changes</th><th>Confidence</th></tr>")
    for r in upcoming:
        limit = f" — {r.limit_value:g} {r.limit_unit}" if r.limit_value is not None else ""
        parts.append(f"<tr><td>{r.effective}</td><td>{e(r.rule_id)} {e(r.jurisdiction)}</td>"
                     f"<td>{e(r.rule_type)}: {e(r.products)}{e(limit)}</td><td>{e(r.confidence)}</td></tr>")
    parts.append("</table></body></html>")
    return "\n".join(parts)


def render_ca_certificates(res: AuditResult, signatory: str = "[Name, title]") -> str:
    """Draft California certificates (AB 1817) for SKUs that pass every CA rule on the first date."""
    d = res.dates[0]
    mats = {m.material_id: m for m in res.audit.materials}
    lines = ["# Draft certificates of compliance — California AB 1817", "",
             f"Brand: {res.audit.brand}  ", f"Evaluated as of: {d.isoformat()}", "",
             "> DRAFT for the manufacturer's review. The manufacturer issues and signs the certificate; "
             "have counsel review the wording before use.", ""]
    skipped = []
    for pr in res.results[d]:
        if "California" not in pr.product.markets:
            continue
        verdict = pr.by_market.get("California")
        ca = [v for v in pr.verdicts if v.jurisdiction == "California" and v.verdict != "Obligation"]
        if verdict != PASS:
            why = ("no CA limit in force on this date; severe-wet apparel needs the 'Made with PFAS chemicals' "
                   "disclosure until 2028" if verdict == "No rule in force" and pr.product.severe_wet else verdict)
            skipped.append(f"{pr.product.sku} ({why})")
            continue
        later = [res.results[d2] for d2 in res.dates[1:]]
        warn = [f"{d2.isoformat()}: {p2.by_market.get('California')}" for d2, rows in zip(res.dates[1:], later)
                for p2 in rows if p2.product.sku == pr.product.sku and p2.by_market.get("California") != PASS]
        lines += [f"## {pr.product.sku} — {pr.product.name}", "",
                  "The manufacturer certifies that this textile article does not contain regulated PFAS as defined "
                  "by California Health and Safety Code (AB 1817): no intentionally added PFAS, and total organic "
                  "fluorine below the threshold in effect on the date above.", "", "Evidence:"]
        for v in ca:
            m = mats[v.material_id]
            lines.append(f"- {m.component} ({m.material_type}, supplier {m.supplier or 'n/a'}): {v.reason} [{v.rule_id}]")
        if warn:
            lines += ["", f"**Warning:** this SKU does not pass on a later date ({'; '.join(warn)}). "
                      "Retest or reformulate before the threshold changes."]
        lines += ["", f"Signed: {signatory}    Date: ________", ""]
    if skipped:
        lines += ["## Not certified", "", *[f"- {s}" for s in skipped]]
    return "\n".join(lines)
