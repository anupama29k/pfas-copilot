"""SQLite storage. One database file; every row belongs to an audit."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("PFAS_DB", Path(__file__).resolve().parents[1] / "data" / "pfas.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS audits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS products (
  audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
  sku TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL,
  severe_wet INTEGER NOT NULL DEFAULT 0, markets TEXT NOT NULL,
  PRIMARY KEY (audit_id, sku)
);
CREATE TABLE IF NOT EXISTS materials (
  audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
  material_id TEXT NOT NULL, sku TEXT NOT NULL, component TEXT, material_type TEXT,
  finish TEXT, supplier TEXT, declared_intentional TEXT DEFAULT 'unknown',
  PRIMARY KEY (audit_id, material_id)
);
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
  filename TEXT, kind TEXT, lab TEXT, report_id TEXT, report_date TEXT, method TEXT,
  uncertainty_rel REAL, layout TEXT, warnings TEXT, uploaded_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  audit_id INTEGER NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
  document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
  material_id TEXT, sample_ref TEXT, description TEXT,
  lab TEXT, report_id TEXT, method TEXT, analyte TEXT NOT NULL,
  value_ppm REAL, below_loq INTEGER DEFAULT 0, loq_ppm REAL, uncertainty_rel REAL,
  result_date TEXT, raw_result TEXT, confidence REAL DEFAULT 1.0, notes TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'confirmed'   -- confirmed | needs_review | rejected
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def tx():
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init():
    with tx() as con:
        con.executescript(SCHEMA)


def rows(con, sql, *args) -> list[dict]:
    return [dict(r) for r in con.execute(sql, args).fetchall()]
