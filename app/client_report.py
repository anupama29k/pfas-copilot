"""Client-ready audit report: the deliverable of a paid PFAS audit.

Structure: cover, executive summary, findings, verdict matrices, action plan, deadlines,
methodology, limitations, and appendices (lab evidence, rules applied with sources, change log).
Printable to PDF from the browser (print styles included).
"""
from __future__ import annotations

import datetime as dt
import html

from pfas_copilot.audit import AuditResult
from pfas_copilot.check import DEFAULT_UNCERTAINTY, INTENT_SCREEN_PPM

OK_STATES = {"Pass", "Obligations only", "No rule in force"}
COLORS = {"Pass": "#e3f3e6", "Fail": "#fbe5e3", "At risk": "#fdf0dc", "Declaration required": "#efeafc",
          "No data": "#eef0f2", "Obligations only": "#e4eefb", "No rule in force": "#ffffff"}
SEV = {"Fail": 5, "At risk": 4, "Declaration required": 3, "No data": 2}


def e(x) -> str:
    return html.escape("" if x is None else str(x))


def fdate(d) -> str:
    if isinstance(d, str):
        d = dt.date.fromisoformat(d[:10])
    return d.strftime("%b %-d, %Y")


CSS = """
@page{size:letter;margin:18mm 16mm}
body{font-family:"IBM Plex Sans",Arial,sans-serif;color:#16202b;margin:0;font-size:12.5px;line-height:1.5}
.page{max-width:900px;margin:0 auto;padding:36px 40px}
h1{font-size:30px;margin:0 0 6px}h2{font-size:19px;margin:34px 0 10px;padding-bottom:6px;border-bottom:2px solid #16324f}
h3{font-size:14px;margin:18px 0 6px}
.cover{border-bottom:4px solid #0b6e75;padding-bottom:22px;margin-bottom:10px}
.meta{color:#5b6673}.meta b{color:#16202b}
.draft{display:inline-block;border:2px solid #b45309;color:#b45309;font-weight:700;padding:2px 10px;border-radius:6px;font-size:11px;letter-spacing:.6px}
table{border-collapse:collapse;width:100%;margin:8px 0 14px;page-break-inside:auto}
tr{page-break-inside:avoid}
th,td{border:1px solid #dfe3e8;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#16324f;color:#fff;font-weight:600;font-size:11.5px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0}
.kpi{border:1px solid #dfe3e8;border-radius:10px;padding:10px 12px}.kpi .k{font-size:11px;color:#5b6673;text-transform:uppercase}.kpi .v{font-size:24px;font-weight:700}
.callout{background:#f3f8f8;border-left:4px solid #0b6e75;padding:10px 14px;margin:10px 0}
.warn{background:#fdf0dc;border-left:4px solid #b45309;padding:10px 14px;margin:10px 0}
.small{font-size:11px;color:#5b6673}
a{color:#0b6e75}
.printbar{position:sticky;top:0;background:#16324f;color:#fff;padding:10px 16px;display:flex;gap:12px;align-items:center;justify-content:space-between}
.printbar button{font:inherit;font-weight:600;background:#fff;color:#16324f;border:0;border-radius:6px;padding:8px 14px;cursor:pointer}
.pb{page-break-before:always}
@media print{.printbar{display:none}.page{padding:0;max-width:none}h2{page-break-after:avoid}}
"""


def render_client_report(res: AuditResult, documents: list[dict], results: list[dict], events: list[dict],
                         prepared_by: str = "", final: bool = False) -> str:
    a = res.audit
    d0 = res.dates[0]
    d1 = res.dates[1] if len(res.dates) > 1 else None
    rules = {r.rule_id: r for r in res.rules}
    mats = {m.material_id: m for m in a.materials}
    markets = sorted({m for p in a.products for m in p.markets})
    now_rows, later_rows = res.results[d0], res.results.get(d1, [])

    def clear(pr):
        return all(v in OK_STATES for v in pr.by_market.values())

    n = len(a.products)
    clear_now = sum(clear(p) for p in now_rows)
    clear_later = sum(clear(p) for p in later_rows) if d1 else None
    counts = {}
    for pr in now_rows:
        for v in pr.by_market.values():
            counts[v] = counts.get(v, 0) + 1

    # findings: every non-OK product x market, worst first, with the reasons behind it
    findings = []
    for date, rows in ((d0, now_rows), (d1, later_rows)):
        for pr in rows:
            for mk, v in pr.by_market.items():
                if v in OK_STATES:
                    continue
                if date == d1 and any(f[1] == pr.product.sku and f[2] == mk and f[3] == v for f in findings):
                    continue  # unchanged from as-of date
                why = [x for x in pr.verdicts if x.jurisdiction == mk and x.verdict == v]
                findings.append((date, pr.product.sku, mk, v, pr.product.name, why))
    findings.sort(key=lambda f: (f[0], -SEV.get(f[3], 0), f[1]))

    upcoming = sorted((r for r in res.rules if r.effective and r.effective > d0 and r.jurisdiction in markets),
                      key=lambda r: r.effective)
    nxt = upcoming[0] if upcoming else None
    pending = sum(1 for r in results if r["status"] == "needs_review")
    used_rules = sorted({v.rule_id for rows in res.results.values() for pr in rows for v in pr.verdicts})
    lo = sum(s.cost_low for s in res.test_plan)
    hi = sum(s.cost_high for s in res.test_plan)

    P = [f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>PFAS audit — {e(a.brand)}</title>"
         "<link href='https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&display=swap' rel='stylesheet'>"
         f"<style>{CSS}</style></head><body>",
         "<div class='printbar'><span>Client report preview</span><button onclick='window.print()'>Save as PDF / Print</button></div>",
         "<div class='page'>"]

    # cover
    P.append(f"""<div class='cover'>{'' if final else "<span class='draft'>DRAFT — FOR REVIEW</span>"}
    <h1>PFAS Compliance Audit</h1><div style='font-size:20px;font-weight:600'>{e(a.brand)}</div>
    <p class='meta'><b>Evaluated as of:</b> {fdate(d0)}{f" &nbsp;·&nbsp; <b>Look-ahead:</b> {fdate(d1)}" if d1 else ""}<br>
    <b>Scope:</b> {n} SKUs, {len(a.materials)} materials, {len([r for r in results if r['status'] == 'confirmed'])} confirmed lab results, markets: {e(', '.join(markets))}<br>
    <b>Prepared by:</b> {e(prepared_by or '[Your name], PFAS Copilot')} &nbsp;·&nbsp; <b>Issued:</b> {fdate(dt.date.today())}</p></div>""")

    # executive summary
    P.append("<h2>1. Executive summary</h2>")
    lines = [f"<b>{clear_now} of {n}</b> SKUs can be sold in all their markets as of {fdate(d0)} with no open compliance issue."]
    if d1:
        lines.append(f"On {fdate(d1)}, <b>{clear_later} of {n}</b> will be, once upcoming rule changes take effect.")
    if nxt:
        lim = f" ({nxt.limit_value:g} {e(nxt.limit_unit)})" if nxt.limit_value is not None else ""
        lines.append(f"Next deadline in your markets: <b>{fdate(nxt.effective)}</b>, {e(nxt.jurisdiction)} — {e(nxt.rule_type.lower())}{lim}.")
    if res.test_plan:
        lines.append(f"Recommended actions: <b>{len(res.test_plan)}</b>, with estimated lab cost <b>${lo:,}–${hi:,}</b>.")
    P.append("<div class='callout'>" + "<br>".join(lines) + "</div>")
    P.append("<div class='kpis'>" + "".join(
        f"<div class='kpi'><div class='k'>{k}</div><div class='v'>{counts.get(k, 0) if k != 'Needs data' else counts.get('No data', 0) + counts.get('Declaration required', 0)}</div></div>"
        for k in ("Pass", "Fail", "At risk", "Needs data")) + "</div><p class='small'>Counts are SKU × market combinations as of the evaluation date.</p>")
    if pending:
        P.append(f"<div class='warn'>{pending} lab result(s) were still awaiting review when this report was generated and are <b>not</b> included.</div>")
    if res.warnings:
        P.append("<div class='warn'>" + "<br>".join(e(w) for w in res.warnings) + "</div>")

    # findings
    P.append("<h2>2. Findings that need action</h2>")
    if findings:
        P.append("<table><tr><th>When</th><th>SKU</th><th>Market</th><th>Verdict</th><th>Why</th></tr>")
        for date, sku, mk, v, name, why in findings:
            reasons = "<br>".join(f"{e(mats[x.material_id].component)} ({e(mats[x.material_id].material_type)}): {e(x.reason)} <span class='small'>[{e(x.rule_id)}]</span>" for x in why[:4])
            P.append(f"<tr><td>{'Now' if date == d0 else fdate(date)}</td><td><b>{e(sku)}</b><br><span class='small'>{e(name)}</span></td><td>{e(mk)}</td>"
                     f"<td style='background:{COLORS.get(v, '#fff')}'><b>{e(v)}</b></td><td>{reasons}</td></tr>")
        P.append("</table>")
    else:
        P.append("<p>No open findings for the products and markets in scope.</p>")

    # matrices
    P.append("<h2>3. Verdicts by product and market</h2>")
    for date, rows in ((d0, now_rows), (d1, later_rows)):
        if date is None:
            continue
        P.append(f"<h3>As of {fdate(date)}</h3><table><tr><th>SKU</th>" + "".join(f"<th>{e(m)}</th>" for m in markets) + "</tr>")
        for pr in rows:
            P.append(f"<tr><td><b>{e(pr.product.sku)}</b> {e(pr.product.name)}{' <span class=small>(severe wet)</span>' if pr.product.severe_wet else ''}</td>"
                     + "".join(f"<td style='background:{COLORS.get(pr.by_market.get(m), '#fff')}'>{e(pr.by_market.get(m, '—'))}</td>" for m in markets) + "</tr>")
        P.append("</table>")
    P.append("<p class='small'>Pass: all applicable limits met with measurement uncertainty. Fail: exceeds a limit even after uncertainty. "
             "At risk: the uncertainty band crosses a limit, or a screen suggests intentional use. Declaration required: the rule bans intentionally "
             "added PFAS and no supplier declaration is on file. No data: a required test is missing. Obligations only: labeling, notice or reporting duties apply but no limit.</p>")

    # action plan
    P.append("<h2>4. Action plan</h2>")
    if res.test_plan:
        P.append("<table><tr><th>#</th><th>Material</th><th>Action</th><th>Why</th><th>Est. cost (USD)</th></tr>")
        for i, s in enumerate(res.test_plan, 1):
            m = mats[s.material_id]
            P.append(f"<tr><td>{i}</td><td>{e(s.material_id)} · {e(m.component)} ({e(m.sku)})<br><span class='small'>{e(m.material_type)}, supplier {e(m.supplier or 'n/a')}</span></td>"
                     f"<td><b>{e(s.test)}</b></td><td>{e(s.why)}</td><td>{s.cost_low:,}–{s.cost_high:,}</td></tr>")
        P.append(f"<tr><td colspan='4' style='text-align:right'><b>Total estimated lab cost</b></td><td><b>${lo:,}–${hi:,}</b></td></tr></table>")
        P.append("<p class='small'>Cost ranges are indicative (a few hundred dollars per fluorine screen; $400–700 per targeted LC-MS/MS test) and vary by lab and turnaround.</p>")
    else:
        P.append("<p>No testing or replacement actions are needed for the current data.</p>")
    decl = [m for m in a.materials if m.declared_intentional == "unknown"]
    if decl:
        P.append("<h3>Supplier declarations to collect</h3><p>" + ", ".join(f"{e(m.material_id)} ({e(m.component)}, {e(m.supplier or 'supplier n/a')})" for m in decl) + "</p>")

    # deadlines
    P.append("<h2>5. Upcoming deadlines in your markets</h2><table><tr><th>Date</th><th>Market</th><th>What changes</th><th>Confidence</th></tr>")
    for r in upcoming:
        lim = f" — {r.limit_value:g} {e(r.limit_unit)}" if r.limit_value is not None else ""
        P.append(f"<tr><td>{fdate(r.effective)}</td><td>{e(r.jurisdiction)}</td><td>{e(r.rule_type)}: {e(r.products)}{lim}</td><td>{e(r.confidence)}</td></tr>")
    P.append("</table>")

    # methodology + limitations
    P.append(f"""<h2 class='pb'>6. Methodology</h2>
    <ol>
    <li><b>Scope.</b> Each SKU was broken into its materials (shell, membrane, lining, trims). Each material was checked against every PFAS rule in force in each market where the SKU is sold, on each evaluation date.</li>
    <li><b>Rules.</b> {len(res.rules)} obligations across US states, the EU, France and Denmark, compiled from the legal and industry sources listed in Appendix B. Each rule carries a confidence rating; Medium and Low ratings mean sources disagree or are thin, and those rules should be confirmed against the statute.</li>
    <li><b>Numeric limits.</b> A result passes only if result + U is below the limit, and fails if result − U is at or above it; otherwise it is At risk. U is the lab's stated expanded uncertainty, or {DEFAULT_UNCERTAINTY:.0%} relative when the lab gives none. A result below the limit of quantification (LOQ) passes only if the LOQ itself is below the limit.</li>
    <li><b>Total organic fluorine vs total fluorine.</b> For TOF limits (e.g., California, Vermont), a total-fluorine result can demonstrate a pass, since TF is at least TOF, but a TF result over the limit is only At risk because inorganic fluorine may contribute. For total-fluorine limits (e.g., Washington, France, Denmark), a TOF result can demonstrate a fail but not a pass.</li>
    <li><b>Bans without a numeric limit.</b> Rules banning intentionally added PFAS rely on supplier declarations. A fluorine screen at or above {INTENT_SCREEN_PPM:g} ppm is flagged as likely intentional use regardless of the declaration.</li>
    <li><b>Targeted limits.</b> EU and French limits on specific substances (e.g., PFHxA, PFOA) are compared against targeted LC-MS/MS results for the same analyte, in ppb.</li>
    <li><b>Evidence.</b> Only lab results confirmed by a named reviewer are used (Appendix A). Results extracted from lab PDFs are checked by a person for value, unit conversion and material match before confirmation.</li>
    </ol>
    <h2>7. Limitations</h2>
    <ul>
    <li>This report is a technical compliance assessment, not legal advice. Certificates of compliance remain the manufacturer's own statement and should be reviewed by counsel.</li>
    <li>Verdicts are only as complete as the product, material, declaration and lab data provided. Untested materials are reported as No data, not as Pass.</li>
    <li>Regulations change. Rules reflect sources dated up to the report's issue date; later amendments are not included.</li>
    <li>No standardized TOF method for textiles exists yet; results from different labs and methods may not be directly comparable.</li>
    </ul>""")

    # appendix A evidence
    conf = [r for r in results if r["status"] == "confirmed"]
    P.append("<h2 class='pb'>Appendix A. Lab evidence</h2>")
    if documents:
        P.append("<h3>Documents</h3><table><tr><th>File</th><th>Lab</th><th>Report</th><th>Date</th><th>Method</th><th>Uncertainty</th></tr>")
        for d in documents:
            P.append(f"<tr><td>{e(d['filename'])}</td><td>{e(d.get('lab') or '—')}</td><td>{e(d.get('report_id') or '—')}</td><td>{e(d.get('report_date') or '—')}</td>"
                     f"<td>{e(d.get('method') or '—')}</td><td>{(str(round(d['uncertainty_rel'] * 100)) + '%') if d.get('uncertainty_rel') is not None else '—'}</td></tr>")
        P.append("</table>")
    P.append("<h3>Results used</h3><table><tr><th>Material</th><th>Analyte</th><th>Result (ppm)</th><th>LOQ (ppm)</th><th>U</th><th>Lab / report</th><th>Confirmed by</th></tr>")
    for r in conf:
        val = "&lt;LOQ" if r["below_loq"] else ("%.4g" % r["value_ppm"] if r["value_ppm"] is not None else "—")
        loq = "" if r["loq_ppm"] is None else "%.4g" % r["loq_ppm"]
        P.append(f"<tr><td>{e(r['material_id'])}</td><td>{e(r['analyte'])}</td><td>{val}</td><td>{loq}</td>"
                 f"<td>{(str(round(r['uncertainty_rel'] * 100)) + '%') if r['uncertainty_rel'] is not None else '20% default'}</td>"
                 f"<td>{e(r['lab'])} {e(r['report_id'])}</td><td>{e(r.get('confirmed_by') or '—')}<br><span class='small'>{e((r.get('confirmed_at') or '')[:16])}</span></td></tr>")
    P.append("</table>")

    # appendix B rules
    P.append("<h2>Appendix B. Rules applied and sources</h2><table><tr><th>Rule</th><th>Law</th><th>Requirement</th><th>Effective</th><th>Confidence</th><th>Sources</th></tr>")
    for rid in used_rules:
        r = rules[rid]
        lim = f"{r.limit_value:g} {e(r.limit_unit)}" if r.limit_value is not None else e(r.limit_basis)
        src = "<br>".join(f"<a href='{e(u)}'>{e(t)}</a>" for t, u in r.sources)
        P.append(f"<tr><td><b>{e(rid)}</b><br>{e(r.jurisdiction)}</td><td>{e(r.law)}</td><td>{e(r.rule_type)}: {e(r.products)} — {lim}</td>"
                 f"<td>{fdate(r.effective) if r.effective else '—'}</td><td>{e(r.confidence)}</td><td class='small'>{src}</td></tr>")
    P.append("</table>")

    # appendix C change log
    if events:
        P.append("<h2>Appendix C. Change log</h2><table><tr><th>When</th><th>Who</th><th>Action</th><th>Detail</th></tr>")
        for ev in events:
            P.append(f"<tr><td>{e(ev['at'][:16])}</td><td>{e(ev.get('actor') or '—')}</td><td>{e(ev['action'])}</td><td>{e(ev.get('detail'))}</td></tr>")
        P.append("</table>")
    P.append("<p class='small' style='margin-top:30px'>Generated by PFAS Copilot. Technical assessment for expert review; not legal advice.</p></div></body></html>")
    return "\n".join(P)
