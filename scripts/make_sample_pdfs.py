"""Generate synthetic lab-report PDFs in two common layouts (for tests and demos).

These are invented reports from fictional labs. They are not real test results.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parents[1] / "samples" / "pdfs"
ST = getSampleStyleSheet()
TS = TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                 ("FONTSIZE", (0, 0), (-1, -1), 9)])


def wide_tof(path):
    """Fictional 'Lab X' style: one row per sample, TOF as a column."""
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    story = [
        Paragraph("<b>LAB X ANALYTICAL (fictional)</b>", ST["Title"]),
        Paragraph("Test Report No: R-002", ST["Normal"]),
        Paragraph("Issued: 2026-09-03", ST["Normal"]),
        Paragraph("Client: Sample Outdoor Co", ST["Normal"]),
        Paragraph("Method: Total organic fluorine by combustion ion chromatography (CIC)", ST["Normal"]),
        Paragraph("Expanded uncertainty (k=2): 20 %", ST["Normal"]),
        Spacer(1, 12),
        Table([["Sample", "Description", "TOF (mg/kg)", "LOQ (mg/kg)"],
               ["S-1", "Softshell shell fabric, polyester DWR", "48", "5"],
               ["S-2", "Lining mesh, polyester", "< 5", "5"]], style=TS),
        Spacer(1, 12),
        Paragraph("Results relate only to the items tested.", ST["Italic"]),
    ]
    doc.build(story)


def long_targeted(path):
    """Fictional 'Lab Y' style: one row per analyte, targeted LC-MS/MS in ug/kg."""
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    story = [
        Paragraph("<b>LAB Y TESTING SERVICES (fictional)</b>", ST["Title"]),
        Paragraph("Report Number: LY-2026-0457", ST["Normal"]),
        Paragraph("Report Date: 09/20/2026", ST["Normal"]),
        Paragraph("Method: EN 17681-1:2025 targeted PFAS by LC-MS/MS", ST["Normal"]),
        Paragraph("Measurement uncertainty: 25 % (k=2)", ST["Normal"]),
        Spacer(1, 12),
        Table([["Sample ID", "Description", "Analyte", "Result", "Unit", "RL"],
               ["Y-11", "Rain jacket shell, nylon ripstop C0 DWR", "PFHxA", "3.2", "ug/kg", "1.0"],
               ["Y-11", "Rain jacket shell, nylon ripstop C0 DWR", "PFOA", "ND", "ug/kg", "1.0"],
               ["Y-11", "Rain jacket shell, nylon ripstop C0 DWR", "Total fluorine", "30", "mg/kg", "5"],
               ["Y-12", "Kids pants cotton twill, stain repellent", "PFHxA", "41", "ug/kg", "1.0"],
               ["Y-12", "Kids pants cotton twill, stain repellent", "PFOA", "<1.0", "ug/kg", "1.0"]], style=TS),
    ]
    doc.build(story)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    wide_tof(OUT / "labx_R-002_tof.pdf")
    long_targeted(OUT / "laby_LY-2026-0457_targeted.pdf")
    print("wrote", *sorted(p.name for p in OUT.glob("*.pdf")))
