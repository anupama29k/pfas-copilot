"""Command line: python -m pfas_copilot audit --rules R.xlsx --products p.csv --materials m.csv --results r.csv"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from .audit import run_audit
from .models import Audit, load_materials, load_products, load_results
from .report import render_ca_certificates, render_report
from .rules import load_rules


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pfas_copilot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="Run a PFAS compliance audit")
    a.add_argument("--rules", default=None, help="Rules workbook (default: bundled)")
    a.add_argument("--products", required=True)
    a.add_argument("--materials", required=True)
    a.add_argument("--results", help="Lab results CSV (optional)")
    a.add_argument("--brand", default="Brand")
    a.add_argument("--as-of", default=dt.date.today().isoformat())
    a.add_argument("--lookahead", help="Second evaluation date, e.g. 2027-01-01 (default: as-of + 1 year)")
    a.add_argument("--out", default="out")
    args = ap.parse_args(argv)

    as_of = dt.date.fromisoformat(args.as_of)
    look = dt.date.fromisoformat(args.lookahead) if args.lookahead else as_of.replace(year=as_of.year + 1)
    audit = Audit(args.brand, load_products(args.products), load_materials(args.materials),
                  load_results(args.results) if args.results else [])
    res = run_audit(audit, load_rules(args.rules) if args.rules else load_rules(), as_of, look)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.html").write_text(render_report(res), encoding="utf-8")
    (out / "ca_certificates.md").write_text(render_ca_certificates(res), encoding="utf-8")
    for d in res.dates:
        counts: dict[str, int] = {}
        for pr in res.results[d]:
            for v in pr.by_market.values():
                counts[v] = counts.get(v, 0) + 1
        print(f"{d}: " + ", ".join(f"{k} {n}" for k, n in sorted(counts.items())))
    print(f"Test plan: {len(res.test_plan)} tests. Warnings: {len(res.warnings)}. Wrote {out}/report.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
