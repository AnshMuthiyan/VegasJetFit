#!/usr/bin/env python3
"""Assemble the Tuesday AMRVAC comparison figures into a meeting PDF."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "plots" / "tuesday_bubble_comparison_2026_09_29"
DEFAULT_PDF = FIGURES / "AMRVAC_bubble_model_comparison_for_Tuesday_2026_09_29.pdf"
GREEN = colors.HexColor("#14795e")
ORANGE = colors.HexColor("#d56b1d")
INK = colors.HexColor("#202a30")
MUTED = colors.HexColor("#596770")


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TitleCustom", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=21, leading=24, textColor=INK, spaceAfter=8),
        "deck": ParagraphStyle("DeckCustom", parent=base["Normal"], fontSize=10, leading=14,
                               textColor=MUTED, alignment=TA_CENTER, spaceAfter=12),
        "h1": ParagraphStyle("H1Custom", parent=base["Heading1"], fontName="Helvetica-Bold",
                             fontSize=12.5, leading=15, textColor=INK, spaceBefore=8, spaceAfter=6),
        "body": ParagraphStyle("BodyCustom", parent=base["BodyText"], fontName="Helvetica",
                               fontSize=9.3, leading=13.4, textColor=INK, spaceAfter=7),
        "bullet": ParagraphStyle("BulletCustom", parent=base["BodyText"], fontName="Helvetica",
                                 fontSize=9.3, leading=13.4, leftIndent=14, firstLineIndent=-9,
                                 textColor=INK, spaceAfter=6),
        "caption": ParagraphStyle("CaptionCustom", parent=base["BodyText"], fontName="Helvetica",
                                  fontSize=8.6, leading=11.5, textColor=MUTED, spaceAfter=7),
        "small": ParagraphStyle("SmallCustom", parent=base["BodyText"], fontName="Helvetica",
                                fontSize=8.1, leading=11, textColor=MUTED, spaceAfter=5),
        "table": ParagraphStyle("TableCustom", parent=base["Normal"], fontName="Helvetica",
                                fontSize=8.1, leading=10, textColor=INK),
    }


def figure(path: Path, width: float):
    item = Image(str(path))
    aspect = item.imageHeight / item.imageWidth
    item.drawWidth = width
    item.drawHeight = width * aspect
    item.hAlign = "CENTER"
    return item


def table(rows: list[list[str]], widths: list[float], style):
    data = [[Paragraph(str(cell), style) for cell in row] for row in rows]
    item = Table(data, colWidths=widths, repeatRows=1, hAlign="CENTER")
    item.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0ef")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, GREEN),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9f8")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return item


def page_frame(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(GREEN)
    canvas.rect(0, height - 0.12 * inch, width, 0.12 * inch, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.60 * inch, height - 0.39 * inch,
                      "AMRVAC wind-bubble profiles  |  Tuesday 29 September 2026")
    canvas.drawRightString(width - 0.60 * inch, 0.38 * inch, f"{doc.page}")
    canvas.restoreState()


def build(pdf_path: Path):
    s = styles()
    story = []
    add = story.append
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, leftMargin=0.60 * inch,
                            rightMargin=0.60 * inch, topMargin=0.65 * inch,
                            bottomMargin=0.60 * inch, title="AMRVAC bubble model comparison for Tuesday",
                            author="Jonathan Keohane research group")

    add(Paragraph("What radius are we fitting?", s["title"]))
    add(Paragraph("AMRVAC profiles compared with Jonathan's simple termination-shock bubble and Ansh's outer-wall shell", s["deck"]))
    add(HRFlowable(width="100%", thickness=1, color=GREEN, spaceAfter=8))
    add(Paragraph("Bottom line", s["h1"]))
    for text in (
        "<b>The radii are not interchangeable.</b>  AMRVAC's outer-rise marker lies 9.4-25.2 times farther out than its first shock.  Jonathan's R_t is intended to mark the first shock; Ansh's R_pole marks the outer shell edge.",
        "<b>The models omit different physics.</b>  Jonathan retains the free wind and termination-shock jump.  Ansh replaces the entire interior with a fixed 0.01 cm^-3 cavity and captures a swept-up outer wall.",
        "<b>Neither is a universal AMRVAC surrogate.</b>  The simple model has lower log-density residual in 11 of 12 simulations, but can move its fitted R_t away from the actual shock to compensate for missing cavity structure.",
    ):
        add(Paragraph("&#8226; " + text, s["bullet"]))
    add(Paragraph("Representative profile scores", s["h1"]))
    add(table([
        ["AMRVAC case", "Jonathan: R_t free", "Jonathan: R_t at shock", "Ansh: fixed cavity"],
        ["p4_n22", "0.960 dex", "0.973 dex", "0.966 dex"],
        ["p5_n21", "0.304 dex", "0.973 dex", "0.404 dex"],
        ["p6_n19", "0.922 dex", "0.930 dex", "2.497 dex"],
    ], [1.34 * inch, 1.74 * inch, 1.92 * inch, 1.98 * inch], s["table"]))
    add(Spacer(1, 7))
    add(figure(FIGURES / "all_12_residuals.png", 7.15 * inch))
    add(Paragraph("RMS differences in log10 density over the same radial window; smaller is a closer match to the simulation.  These are not GRB-data fit statistics or model-selection probabilities.", s["caption"]))
    add(PageBreak())

    add(Paragraph("Where the radial laws agree and fail", s["h1"]))
    add(Paragraph("Black is the selected AMRVAC snapshot.  Solid green and orange are the two globally optimized laws; dashed green fixes Jonathan's R_t to the simulated first shock and fits only n_t.", s["caption"]))
    add(figure(FIGURES / "representative_profiles.png", 5.85 * inch))
    add(Paragraph("Vertical gray lines mark the AMRVAC first shock (dashed) and onset of the outer rise (dotted).  A wall can match while the wind/cavity does not; the large p6_n19 interior discrepancy exposes Ansh's fixed cavity floor.", s["caption"]))
    add(PageBreak())

    descriptions = {
        "p4": "Lower ambient-pressure cases.  Both simplified laws match the dense outer rise more readily than the long, depleted interior; the termination shock remains a distinct feature in AMRVAC.",
        "p5": "Intermediate pressure.  Some profiles have a comparatively flat interior, which makes a constant-cavity approximation look better, but it still has no wind termination shock.",
        "p6": "Higher ambient-pressure cases.  p6_n19 is the clearest failure of a universal 0.01 cm^-3 cavity; the correct outer-wall position does not repair the missing dense inner structure.",
    }
    for pressure in ("p4", "p5", "p6"):
        add(Paragraph(f"All four {pressure} AMRVAC cases", s["h1"]))
        add(Paragraph(descriptions[pressure], s["body"]))
        add(figure(FIGURES / f"{pressure}_profiles.png", 7.15 * inch))
        add(Paragraph("Equivalent density n = rho/(1.3 m_p) is displayed on common physical axes within each panel.  Every model shares the AMRVAC ambient density; radii and interior normalization are optimized as described in the methods note.", s["caption"]))
        add(PageBreak())

    add(Paragraph("Why the radius parameter matters", s["h1"]))
    add(figure(FIGURES / "radius_correspondence.png", 7.15 * inch))
    add(Paragraph("Black circle/triangle: simulation first shock/outer-rise onset.  Green diamond: Jonathan's best whole-profile R_t.  Orange square/triangle: Ansh's fitted shell inner/outer boundaries.  The gray interval is a simulated radial span, not an error bar.", s["caption"]))
    add(Paragraph("Interpretation", s["h1"]))
    add(Paragraph("The AMRVAC outer-rise/first-shock radius ratio is 9.4-25.2 (median 17.7).  The globally fitted Jonathan R_t divided by the simulated first-shock radius ranges from 0.31 to 2.50 (median 0.91).  Anchoring R_t to the shock increases median profile RMS from 0.387 to 0.973 dex: the simple law often needs a different radius to approximate the *whole* profile.  That is a model-shape limitation, not evidence that the simulated shock moves.", s["body"]))
    add(Paragraph("Recommendation", s["h1"]))
    add(Paragraph("Keep R_t explicitly tied to the progenitor wind termination shock.  Develop a fast profile with that inner coordinate plus a distinct shocked-wind cavity and outer wall, calibrating any radial relationship to the simulation grid.  Do not seed Ansh's R_pole from an R_t posterior by renaming it.  Validate the profile itself before a GRB MCMC comparison.", s["body"]))
    add(Paragraph("Method and scope", s["h1"]))
    add(Paragraph("Twelve checksum-verified selected May 1 AMRVAC VTUs; 256 equally weighted log-radius samples per case; known ambient mass density fixed; three seeded differential-evolution starts.  Jonathan fits R_t and n_t; Ansh fits R_pole and shell fraction eps with q=1 and n_cav fixed at 0.01 cm^-3.  For shape comparison both use n = rho/(1.3 m_p); Ansh's unmodified adapter defaults to mu=1.0.  No GRB observations, light curves, MCMC, or model-selection penalty are included.  Source metrics and scripts accompany this PDF in the share folder.", s["small"]))

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=page_frame, onLaterPages=page_frame)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_PDF)
    args = parser.parse_args()
    build(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
