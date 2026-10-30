/* PFAS Copilot UI: plain JS, hash routing (#audits, #a12-setup, #a12-lab, #a12-verdicts, ...). */
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt = x => x == null ? "" : (Math.round(x * 10000) / 10000).toString();
const today = new Date().toISOString().slice(0, 10);
const cls = v => "v-" + (v === "No rule in force" ? "Norule" : String(v).replace(/\s/g, ""));
const badge = v => `<span class="badge ${cls(v)}">${esc(v)}</span>`;
const fdate = d => new Date(d + "T00:00:00").toLocaleDateString("en-US", {month: "short", day: "numeric", year: "numeric"});
const STEPS = [["setup", "Products"], ["lab", "Lab results"], ["verdicts", "Verdicts"], ["plan", "Test plan"], ["certs", "Certificates"], ["deadlines", "Deadlines"], ["report", "Client report"]];
const store = {get(k, d = "") { try { return localStorage.getItem(k) ?? d; } catch (_) { return d; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (_) {} }};
const reviewer = () => store.get("pfasReviewer");
const S = {audit: null, evalCache: null, asOf: today, look: nextJan(), sel: null};

function nextJan() { const y = new Date().getFullYear() + 1; return `${y}-01-01`; }
function toast(t) { const el = $("#toast"); el.textContent = t; el.classList.add("show"); clearTimeout(toast.t); toast.t = setTimeout(() => el.classList.remove("show"), 2600); }

async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (r.status === 204) return null;
  const ct = r.headers.get("content-type") || "";
  const body = ct.includes("json") ? await r.json() : await r.text();
  if (!r.ok) throw new Error(body && body.detail ? (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)) : `Error ${r.status}`);
  return body;
}
const post = (p, b) => api(p, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(b || {})});
const patch = (p, b) => api(p, {method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify(b)});
const upload = (p, file) => { const f = new FormData(); f.append("file", file); return api(p, {method: "POST", body: f}); };

function route() {
  const h = (location.hash || "#audits").slice(1);
  const m = h.match(/^a(\d+)-(\w+)$/);
  return m ? {id: +m[1], view: m[2]} : {view: "audits"};
}

function renderNav(r) {
  const nav = $("#nav");
  let html = `<a href="#audits" data-v="audits" class="${r.view === "audits" ? "active" : ""}"><span class="n">≡</span>All audits</a>`;
  if (r.id) html += STEPS.map(([k, l], i) => `<a href="#a${r.id}-${k}" class="${r.view === k ? "active" : ""}"><span class="n">${i + 1}</span>${l}</a>`).join("")
    + `<div class="foot">Reviewing as: <b>${esc(reviewer() || "not set")}</b><br><a href="/api/audits/${r.id}/report.html?as_of=${S.asOf}&lookahead=${S.look}" target="_blank" rel="noopener" style="padding:0;min-height:0;color:var(--accent);display:inline">Technical report</a></div>`;
  nav.innerHTML = html;
  const pill = $("#brandpill");
  if (r.id && S.audit) { pill.hidden = false; pill.textContent = `${S.audit.brand} · ${S.audit.products.length} SKUs`; } else pill.hidden = true;
}

async function render() {
  const r = route();
  const main = $("#main");
  try {
    if (r.id && (!S.audit || S.audit.id !== r.id)) { S.audit = await api(`/api/audits/${r.id}`); S.evalCache = null; S.sel = null; }
    renderNav(r);
    main.innerHTML = await (views[r.view] || views.audits)(r);
    bind(r);
  } catch (e) {
    main.innerHTML = `<h1>Something went wrong</h1><div class="err">${esc(e.message)}</div><a class="btn ghost" href="#audits">Back to audits</a>`;
  }
}
async function reloadAudit() { S.audit = await api(`/api/audits/${S.audit.id}`); S.evalCache = null; }
async function evaluation() {
  const key = S.asOf + "|" + S.look;
  if (!S.evalCache || S.evalCache.key !== key) S.evalCache = {key, data: await api(`/api/audits/${S.audit.id}/evaluate?as_of=${S.asOf}&lookahead=${S.look}`)};
  return S.evalCache.data;
}

const views = {
  async audits() {
    const list = await api("/api/audits");
    return `<h1>Audits</h1><p class="sub">One audit per brand. Upload the brand's products, materials and lab reports, then review verdicts for every market and date.</p>
    <div class="card"><h2>New audit</h2><form id="newaudit" class="row"><label class="sr" for="brand">Brand name</label>
      <input type="text" id="brand" placeholder="Brand name" required style="min-width:260px">
      <button class="btn" type="submit">Create audit</button><button class="btn ghost" type="button" id="sample">Create sample audit</button></form></div>
    <div class="card auditlist"><h2>Your audits</h2>${list.length ? `<div class="scroll"><table><tr><th>Brand</th><th>Created</th><th>SKUs</th><th>Lab results</th><th>To review</th><th></th></tr>
      ${list.map(a => `<tr><td><a href="#a${a.id}-${a.n_products ? "verdicts" : "setup"}">${esc(a.brand)}</a></td><td>${esc(a.created_at.slice(0, 10))}</td><td>${a.n_products}</td><td>${a.n_results}</td>
      <td>${a.n_review ? badge(a.n_review + " to review") : "—"}</td><td><button class="btn small danger" data-del="${a.id}" aria-label="Delete audit ${esc(a.brand)}">Delete</button></td></tr>`).join("")}</table></div>`
      : `<p class="empty">No audits yet. Create one, or start with the sample to see how it works.</p>`}</div>`;
  },

  async setup() {
    const a = S.audit;
    const decl = m => `<label class="sr" for="d-${esc(m.material_id)}">Supplier declaration for ${esc(m.material_id)}</label><select id="d-${esc(m.material_id)}" data-decl="${esc(m.material_id)}">${["unknown", "no", "yes"].map(o => `<option ${m.declared_intentional === o ? "selected" : ""}>${o}</option>`).join("")}</select>`;
    return `<h1>Products and materials</h1><p class="sub">Upload the product list first, then the materials. Re-uploading a file replaces it. CSV or Excel (.xlsx). Templates: products <a href="/api/templates/products.xlsx">.xlsx</a> / <a href="/api/templates/products.csv">.csv</a> · materials <a href="/api/templates/materials.xlsx">.xlsx</a> / <a href="/api/templates/materials.csv">.csv</a>.</p>
    <div class="grid2">
      <div class="card"><h2>1. Product list</h2>${dropZone("products", ".csv,.xlsx", "sku, name, category, severe_wet, markets")}</div>
      <div class="card"><h2>2. Materials</h2>${dropZone("materials", ".csv,.xlsx", "material_id, sku, component, material_type, finish, supplier, declared_intentional")}</div>
    </div><div id="msg"></div>
    <div class="card"><h2>Products (${a.products.length})</h2>${a.products.length ? `<div class="scroll"><table><tr><th>SKU</th><th>Product</th><th>Category</th><th>Severe-wet</th><th>Markets</th></tr>
      ${a.products.map(p => `<tr><td>${esc(p.sku)}</td><td>${esc(p.name)}</td><td>${esc(p.category)}</td><td>${p.severe_wet ? "Yes" : "No"}</td><td>${p.markets.map(esc).join(", ")}</td></tr>`).join("")}</table></div>` : `<p class="empty">No products yet.</p>`}</div>
    <div class="card"><h2>Materials (${a.materials.length})</h2>${a.materials.length ? `<div class="scroll"><table><tr><th>ID</th><th>SKU</th><th>Component</th><th>Material</th><th>Finish</th><th>Supplier</th><th>Supplier says PFAS added?</th></tr>
      ${a.materials.map(m => `<tr><td>${esc(m.material_id)}</td><td>${esc(m.sku)}</td><td>${esc(m.component)}</td><td>${esc(m.material_type)}</td><td>${esc(m.finish || "—")}</td><td>${esc(m.supplier)}</td><td>${decl(m)}</td></tr>`).join("")}</table></div>` : `<p class="empty">No materials yet.</p>`}</div>
    ${a.materials.length ? `<a class="btn" href="#a${a.id}-lab" style="text-decoration:none;display:inline-flex;align-items:center">Next: lab results</a>` : ""}`;
  },

  async lab() {
    const a = S.audit;
    const mats = a.materials;
    const review = a.results.filter(r => r.status === "needs_review");
    const confirmed = a.results.filter(r => r.status === "confirmed");
    const matSel = r => `<label class="sr" for="m-${r.id}">Material for result ${r.id}</label><select id="m-${r.id}" data-mat="${r.id}"><option value="">Pick material…</option>${mats.map(m => `<option value="${esc(m.material_id)}" ${r.material_id === m.material_id ? "selected" : ""}>${esc(m.material_id)} · ${esc(m.component)} (${esc(m.sku)})</option>`).join("")}</select>`;
    const val = r => r.below_loq ? `<span class="mono">&lt;LOQ</span>` : `<label class="sr" for="v-${r.id}">Value for result ${r.id}</label><input class="num mono" id="v-${r.id}" type="number" step="any" min="0" value="${fmt(r.value_ppm)}" data-val="${r.id}">`;
    const docs = a.documents.map(d => { const w = JSON.parse(d.warnings || "[]"); return `<tr><td>${esc(d.filename)}</td><td>${esc(d.kind.toUpperCase())}</td><td>${esc(d.lab || "—")}</td><td class="mono">${esc(d.report_id || "—")}</td><td>${esc(d.report_date || "—")}</td><td>${d.uncertainty_rel != null ? Math.round(d.uncertainty_rel * 100) + "%" : "—"}</td><td class="reason">${w.map(esc).join("<br>") || "—"}</td></tr>`; }).join("");
    return `<h1>Lab results</h1><p class="sub">Upload lab-report PDFs or a results CSV (<a href="/api/templates/lab_results.csv">template</a>). Results read from a PDF wait here for your review: check the value, unit conversion and material match before they count in any verdict.</p>
    ${mats.length ? "" : `<div class="err">Upload products and materials first, so results can be matched to materials.</div>`}
    <div class="card"><form class="row" id="revform"><label for="rev"><b>Reviewer</b> (recorded on every confirmation)</label><input type="text" id="rev" value="${esc(reviewer())}" placeholder="Your name" style="min-width:220px"><button class="btn small ghost" type="submit">Save</button></form></div>
    <div class="grid2"><div class="card"><h2>Lab report PDF</h2>${dropZone("pdf", ".pdf", "Text-based PDFs; scanned PDFs need OCR (not yet supported)")}</div>
    <div class="card"><h2>Results CSV or Excel</h2>${dropZone("rcsv", ".csv,.xlsx", "material_id, analyte, result, unit, loq, uncertainty_pct, date…")}</div></div><div id="msg"></div>
    <div class="card"><div class="row" style="justify-content:space-between"><h2 style="margin:0">To review (${review.length})</h2>${review.length ? `<button class="btn small" id="confirmall">Confirm all matched</button>` : ""}</div>
    ${review.length ? `<div class="scroll"><table><tr><th>Sample (from report)</th><th>Analyte</th><th>Result (ppm)</th><th>Raw</th><th>LOQ (ppm)</th><th>Material</th><th>Notes</th><th></th></tr>
      ${review.map(r => `<tr class="${r.confidence < 0.8 ? "lowconf" : ""}"><td><b>${esc(r.sample_ref)}</b><div class="reason">${esc(r.description)}</div></td><td>${esc(r.analyte)}</td><td>${val(r)}</td><td class="mono">${esc(r.raw_result)}</td><td class="mono">${fmt(r.loq_ppm)}</td><td>${matSel(r)}</td><td class="reason">${esc(r.notes)}</td>
      <td><div class="row"><button class="btn small" data-confirm="${r.id}">Confirm</button><button class="btn small danger" data-reject="${r.id}">Reject</button></div></td></tr>`).join("")}</table></div>` : `<p class="empty">Nothing waiting for review.</p>`}</div>
    <div class="card"><h2>Confirmed results (${confirmed.length})</h2>${confirmed.length ? `<div class="scroll"><table><tr><th>Material</th><th>Report</th><th>Analyte</th><th>Result (ppm)</th><th>LOQ</th><th>U</th><th>Method</th><th>Confirmed by</th><th></th></tr>
      ${confirmed.map(r => `<tr><td>${esc(r.material_id)}</td><td class="mono">${esc(r.report_id)}</td><td>${esc(r.analyte)}</td><td>${val(r)}</td><td class="mono">${fmt(r.loq_ppm)}</td><td class="mono">${r.uncertainty_rel != null ? Math.round(r.uncertainty_rel * 100) + "%" : "20% default"}</td><td>${esc(r.method)}</td><td class="reason">${esc(r.confirmed_by || "—")}<br>${esc((r.confirmed_at || "").slice(0, 16))}</td><td><button class="btn small danger" data-delres="${r.id}" aria-label="Delete result ${r.id}">Delete</button></td></tr>`).join("")}</table></div>` : `<p class="empty">No confirmed results yet.</p>`}</div>
    ${a.documents.length ? `<div class="card"><h2>Uploaded documents</h2><div class="scroll"><table><tr><th>File</th><th>Type</th><th>Lab</th><th>Report</th><th>Date</th><th>U</th><th>Parser warnings</th></tr>${docs}</table></div></div>` : ""}
    ${(a.events || []).length ? `<div class="card"><h2>Activity</h2><div class="scroll"><table><tr><th>When</th><th>Who</th><th>Action</th><th>Detail</th></tr>${a.events.slice(0, 30).map(ev => `<tr><td class="mono">${esc(ev.at.slice(0, 16))}</td><td>${esc(ev.actor || "—")}</td><td>${esc(ev.action)}</td><td class="reason">${esc(ev.detail)}</td></tr>`).join("")}</table></div></div>` : ""}`;
  },

  async verdicts() {
    const e = await evaluation();
    const di = Math.min(S.dateIdx || 0, e.dates.length - 1);
    const d = e.dates[di];
    const c = d.counts;
    const kp = (k, v) => `<div class="kpi"><div class="k">${k}</div><div class="val">${v}</div></div>`;
    let drawer = "";
    if (S.sel) {
      const p = d.products.find(x => x.sku === S.sel.sku);
      if (p) {
        const vs = p.verdicts.filter(v => v.jurisdiction === S.sel.j);
        drawer = `<div class="card drawer"><h2>${esc(p.name)} in ${esc(S.sel.j)}, as of ${fdate(d.date)}: ${badge(p.by_market[S.sel.j] || "—")}</h2>
        ${vs.length ? `<div class="scroll"><table><tr><th>Material</th><th>Rule</th><th>Verdict</th><th>Why</th></tr>${vs.map(v => `<tr><td>${esc(v.component)} · ${esc(v.material_type)}</td><td><b>${esc(v.rule_id)}</b><div class="reason">${esc(v.law)}${v.confidence !== "High" ? ` · ${esc(v.confidence)} confidence` : ""}</div><div class="reason">${(v.sources || []).map(x => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title.split(":")[0])}</a>`).join(" · ")}</div></td><td>${badge(v.verdict)}</td><td class="reason">${esc(v.reason)}</td></tr>`).join("")}</table></div>`
          : `<p class="reason">No rule covers this product in this market on this date${p.severe_wet ? " (severe-wet outdoor apparel is often deferred)" : ""}.</p>`}</div>`;
      }
    }
    return `<h1>Compliance verdicts</h1><p class="sub">Every material checked against every rule in force in each market, with measurement uncertainty. Only confirmed lab results count. Click a cell to see why.</p>
    ${e.pending_review ? `<div class="warnbox">${e.pending_review} lab result(s) are waiting for review and are not counted yet. <a href="#a${S.audit.id}-lab">Review them</a>.</div>` : ""}
    ${e.warnings.length ? `<div class="warnbox">${e.warnings.map(esc).join("<br>")}</div>` : ""}
    <div class="row" style="margin-bottom:14px;justify-content:space-between">
      <div class="chips" role="group" aria-label="Evaluate as of">${e.dates.map((x, i) => `<button class="chip ${i === di ? "on" : ""}" data-di="${i}" aria-pressed="${i === di}">${i === 0 ? "As of " : "Look-ahead "}${fdate(x.date)}</button>`).join("")}</div>
      <form class="row" id="dates"><label for="asof">As of</label><input type="date" id="asof" value="${S.asOf}"><label for="look">Look-ahead</label><input type="date" id="look" value="${S.look}"><button class="btn small ghost" type="submit">Update</button></form>
    </div>
    <div class="kpis">${kp("Pass", c["Pass"] || 0)}${kp("Fail", c["Fail"] || 0)}${kp("At risk", c["At risk"] || 0)}${kp("Needs data or declaration", (c["No data"] || 0) + (c["Declaration required"] || 0))}</div>
    <div class="card"><div class="scroll"><table class="matrix"><tr><th>Product</th>${e.markets.map(m => `<th>${esc(m)}</th>`).join("")}</tr>
    ${d.products.map(p => `<tr class="${S.sel && S.sel.sku === p.sku ? "sel" : ""}"><td><b>${esc(p.sku)}</b> ${esc(p.name)}${p.severe_wet ? ' <span class="note">· severe wet</span>' : ""}</td>${e.markets.map(m => p.by_market[m] ? `<td class="cell"><button data-s="${esc(p.sku)}" data-j="${esc(m)}" aria-label="${esc(p.sku)} in ${esc(m)}: ${esc(p.by_market[m])}">${badge(p.by_market[m])}</button></td>` : `<td class="note">not sold</td>`).join("")}</tr>`).join("")}
    </table></div></div>${drawer}`;
  },

  async plan() {
    const e = await evaluation();
    const st = e.test_plan, lo = st.reduce((a, s) => a + s.cost_low, 0), hi = st.reduce((a, s) => a + s.cost_high, 0);
    const mats = Object.fromEntries(S.audit.materials.map(m => [m.material_id, m]));
    return `<h1>Test plan</h1><p class="sub">Only the tests that change a decision: fluorine screens first, targeted LC-MS/MS where a limit or market needs it, and replacement where testing can't help. Covers both evaluation dates.</p>
    <div class="kpis"><div class="kpi"><div class="k">Actions</div><div class="val">${st.length}</div></div><div class="kpi"><div class="k">Estimated lab cost</div><div class="val">$${lo.toLocaleString()}–${hi.toLocaleString()}</div></div></div>
    <div class="card">${st.length ? `<div class="scroll"><table><tr><th>Material</th><th>Risk</th><th>Action</th><th>Why</th><th>Est. cost (USD)</th></tr>
    ${st.map(s => `<tr><td>${esc(s.material_id)} · ${esc(mats[s.material_id]?.component)} (${esc(mats[s.material_id]?.sku)})</td><td><span class="badge r-${s.risk}">${s.risk}</span></td><td><b>${esc(s.test)}</b></td><td class="reason">${esc(s.why)}</td><td class="mono">${s.cost_low}–${s.cost_high}</td></tr>`).join("")}</table></div>` : `<p class="empty">No tests needed for the current data.</p>`}
    <p class="note">Indicative costs: a few hundred dollars per fluorine screen, $400–700 per targeted LC-MS/MS test.</p></div>`;
  },

  async certs() {
    const md = await api(`/api/audits/${S.audit.id}/certificates.md?as_of=${S.asOf}&lookahead=${S.look}`);
    return `<h1>Certificates</h1><p class="sub">Draft California AB 1817 certificates of compliance for SKUs that pass on ${fdate(S.asOf)}, with the evidence listed. The manufacturer reviews and signs. Have counsel review the wording before first use.</p>
    <div class="row" style="margin-bottom:12px"><button class="btn" id="copycert">Copy text</button><a class="btn ghost" style="text-decoration:none;display:inline-flex;align-items:center" href="/api/audits/${S.audit.id}/certificates.md?as_of=${S.asOf}&lookahead=${S.look}" target="_blank" rel="noopener">Open as Markdown</a></div>
    <div class="cert" style="max-width:860px"><pre class="cert-md" id="certtext">${esc(md)}</pre></div>`;
  },

  async report() {
    const a = S.audit, pb = store.get("pfasPreparedBy", reviewer());
    const url = final => `/api/audits/${a.id}/client-report.html?as_of=${S.asOf}&lookahead=${S.look}&prepared_by=${encodeURIComponent(pb)}${final ? "&final=true" : ""}`;
    const pend = a.results.filter(r => r.status === "needs_review").length;
    return `<h1>Client report</h1><p class="sub">The deliverable you hand the brand: executive summary, findings, action plan with costs, deadlines, methodology, limitations, and appendices with the lab evidence, every rule's sources, and the change log. Open it, then use <b>Save as PDF</b>.</p>
    ${pend ? `<div class="warnbox">${pend} lab result(s) are still waiting for review and will be left out. <a href="#a${a.id}-lab">Review them first</a>.</div>` : ""}
    <div class="card"><form class="row" id="pbform"><label for="pb">Prepared by</label><input type="text" id="pb" value="${esc(pb)}" placeholder="Your name, company" style="min-width:280px"><button class="btn small ghost" type="submit">Save</button></form>
    <p class="note">Evaluated as of ${fdate(S.asOf)}, look-ahead ${fdate(S.look)} (change on the Verdicts page).</p>
    <div class="row"><a class="btn" style="text-decoration:none;display:inline-flex;align-items:center" target="_blank" rel="noopener" href="${url(false)}">Open draft report</a>
    <a class="btn ghost" style="text-decoration:none;display:inline-flex;align-items:center" target="_blank" rel="noopener" href="${url(true)}">Open final report (no DRAFT mark)</a></div></div>`;
  },

  async deadlines() {
    const e = await evaluation();
    return `<h1>Deadlines in this brand's markets</h1><p class="sub">Rules from the bundled rules workbook. Medium and Low confidence rows should be checked against the statute.</p>
    <div class="card"><div class="timeline">${e.deadlines.map(r => `<div class="tl ${r.date <= S.asOf ? "past" : ""}"><div class="d">${fdate(r.date)} · ${esc(r.jurisdiction)} <span class="note">${r.date <= S.asOf ? "in force" : "upcoming"}${r.confidence !== "High" ? " · " + esc(r.confidence) + " confidence" : ""}</span></div>
    <div>${esc(r.type)}: ${esc(r.products)}${r.limit_value != null ? ` — <b>${fmt(r.limit_value)} ${esc(r.limit_unit)}</b>` : ""}</div></div>`).join("") || `<p class="empty">No deadlines for these markets.</p>`}</div></div>`;
  },
};

function dropZone(id, accept, hint) {
  return `<div class="drop" data-drop="${id}"><p style="margin:0 0 8px">Drag a file here, or</p>
  <label class="btn ghost small" style="display:inline-flex;align-items:center;cursor:pointer">Choose file<input type="file" accept="${accept}" data-file="${id}" class="sr"></label>
  <p class="note" style="margin:8px 0 0">${esc(hint)}</p></div>`;
}

async function handleFile(kind, file) {
  const id = S.audit.id, msg = $("#msg");
  const paths = {products: "products", materials: "materials", pdf: "results/pdf", rcsv: "results/csv"};
  msg.innerHTML = `<div class="ok">Uploading ${esc(file.name)}…</div>`;
  try {
    const r = await upload(`/api/audits/${id}/${paths[kind]}`, file);
    await reloadAudit();
    await render();
    const text = kind === "pdf" ? `Read ${r.rows} result(s) from ${file.name}${r.report_id ? " (report " + r.report_id + ")" : ""}. Review them below.` : `Imported ${r.imported} row(s) from ${file.name}.`;
    const warn = (r.warnings || []).map(esc).join("<br>");
    $("#msg").innerHTML = `<div class="ok">${esc(text)}</div>${warn ? `<div class="warnbox">${warn}</div>` : ""}`;
  } catch (e) { msg.innerHTML = `<div class="err">${esc(file.name)}: ${esc(e.message)}</div>`; }
}

function bind(r) {
  const main = $("#main");
  main.querySelectorAll("[data-drop]").forEach(z => {
    z.addEventListener("dragover", e => { e.preventDefault(); z.classList.add("over"); });
    z.addEventListener("dragleave", () => z.classList.remove("over"));
    z.addEventListener("drop", e => { e.preventDefault(); z.classList.remove("over"); const f = e.dataTransfer.files[0]; if (f) handleFile(z.dataset.drop, f); });
  });
  main.querySelectorAll("[data-file]").forEach(i => i.addEventListener("change", () => i.files[0] && handleFile(i.dataset.file, i.files[0])));
  const na = $("#newaudit");
  if (na) na.addEventListener("submit", async e => { e.preventDefault(); const a = await post("/api/audits", {brand: $("#brand").value}); location.hash = `a${a.id}-setup`; });
  const rf = $("#revform");
  if (rf) rf.addEventListener("submit", e => { e.preventDefault(); store.set("pfasReviewer", $("#rev").value.trim()); renderNav(route()); toast("Reviewer saved"); });
  const pf = $("#pbform");
  if (pf) pf.addEventListener("submit", e => { e.preventDefault(); store.set("pfasPreparedBy", $("#pb").value.trim()); render(); toast("Saved"); });
  const df = $("#dates");
  if (df) df.addEventListener("submit", e => { e.preventDefault(); S.asOf = $("#asof").value || today; S.look = $("#look").value || nextJan(); S.dateIdx = 0; render(); });
}

document.addEventListener("click", async e => {
  const t = e.target.closest("button"); if (!t) return;
  const id = S.audit && S.audit.id;
  try {
    if (t.id === "sample") { const a = await post("/api/audits", {brand: "Sample Outdoor Co"}); await post(`/api/audits/${a.id}/load-sample`); location.hash = `a${a.id}-verdicts`; toast("Sample audit created"); }
    else if (t.dataset.del) { if (t.dataset.armed) { await api(`/api/audits/${t.dataset.del}`, {method: "DELETE"}); render(); toast("Audit deleted"); } else { t.dataset.armed = "1"; t.textContent = "Click again to delete"; } }
    else if (t.dataset.confirm) { const sel = $(`#m-${t.dataset.confirm}`); const v = $(`#v-${t.dataset.confirm}`);
      const body = {status: "confirmed", material_id: sel.value || null, reviewer: reviewer()}; if (v) body.value_ppm = parseFloat(v.value);
      await patch(`/api/audits/${id}/results/${t.dataset.confirm}`, body); await reloadAudit(); render(); toast("Result confirmed"); }
    else if (t.dataset.reject) { await patch(`/api/audits/${id}/results/${t.dataset.reject}`, {status: "rejected", reviewer: reviewer()}); await reloadAudit(); render(); toast("Result rejected"); }
    else if (t.dataset.delres) { await api(`/api/audits/${id}/results/${t.dataset.delres}`, {method: "DELETE"}); await reloadAudit(); render(); toast("Result deleted"); }
    else if (t.id === "confirmall") { const r = await post(`/api/audits/${id}/results/confirm-all?reviewer=${encodeURIComponent(reviewer())}`); await reloadAudit(); render(); toast(`${r.confirmed} result(s) confirmed`); }
    else if (t.dataset.di) { S.dateIdx = +t.dataset.di; render(); }
    else if (t.dataset.s) { S.sel = {sku: t.dataset.s, j: t.dataset.j}; render(); }
    else if (t.id === "copycert") { try { await navigator.clipboard.writeText($("#certtext").textContent); toast("Copied"); } catch (_) { toast("Copy isn't available here"); } }
  } catch (err) { toast(err.message); }
});

document.addEventListener("change", async e => {
  const el = e.target, id = S.audit && S.audit.id;
  try {
    if (el.dataset.decl) { await patch(`/api/audits/${id}/materials/${encodeURIComponent(el.dataset.decl)}`, {declared_intentional: el.value, reviewer: reviewer()}); await reloadAudit(); toast(`${el.dataset.decl}: declaration set to ${el.value}`); }
    else if (el.dataset.val) { const row = S.audit.results.find(r => r.id === +el.dataset.val);
      if (row && row.status === "confirmed") { await patch(`/api/audits/${id}/results/${el.dataset.val}`, {value_ppm: parseFloat(el.value), reviewer: reviewer()}); await reloadAudit(); toast("Value updated; verdicts will recalculate"); } }
    else if (el.dataset.mat) { await patch(`/api/audits/${id}/results/${el.dataset.mat}`, {material_id: el.value || null, reviewer: reviewer()}); await reloadAudit(); }
  } catch (err) { toast(err.message); }
});

window.addEventListener("hashchange", render);
render();
