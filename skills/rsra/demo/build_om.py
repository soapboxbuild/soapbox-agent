#!/usr/bin/env python3
"""
Generates a compact (~6 page), fully pseudonymous Offering Memorandum for
the RSRA demo fixtures. All names, figures, and the sponsor are invented.

Real names/entities from the confidential reference document in ~/inbox are
scrubbed and do NOT appear anywhere in the output below. This asset is
relocated to Denver, CO so BPS (Energize Denver) and physical-risk (hail)
references make sense for the demo, and every financial/physical figure is
freshly authored — not copied from the reference.

Usage:
    .venv/bin/python build_om.py
Requires: reportlab (installed into a local .venv — see README.md)
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

OUT = "om_4400_prairie_crossing.pdf"

NAVY = colors.HexColor("#1b2a41")
GOLD = colors.HexColor("#b08d57")
LIGHT = colors.HexColor("#f4f1ea")
GREY = colors.HexColor("#5a5a5a")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", fontSize=26, leading=32, textColor=NAVY,
                           fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=6))
styles.add(ParagraphStyle(name="CoverSub", fontSize=13, leading=18, textColor=GOLD,
                           fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4))
styles.add(ParagraphStyle(name="CoverMeta", fontSize=11, leading=15, textColor=GREY,
                           alignment=TA_CENTER))
styles.add(ParagraphStyle(name="H1", fontSize=15, leading=19, textColor=NAVY,
                           fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=8))
styles.add(ParagraphStyle(name="H2", fontSize=11.5, leading=15, textColor=GOLD,
                           fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4))
styles.add(ParagraphStyle(name="Body", fontSize=9.6, leading=13.5, textColor=colors.black))
styles.add(ParagraphStyle(name="OMBullet", fontSize=9.6, leading=13.5, leftIndent=12,
                           bulletIndent=0, textColor=colors.black))
styles.add(ParagraphStyle(name="Footer", fontSize=7.5, textColor=GREY, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="Disclaimer", fontSize=7.5, leading=10, textColor=GREY))


def table(data, col_widths=None, header=True, small=False):
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8 if small else 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfcabb")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(
        letter[0] / 2, 0.5 * inch,
        "Confidential Offering Memorandum — 4400 Prairie Crossing — Stonebridge Capital  |  "
        f"Page {doc.page}"
    )
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(
        OUT, pagesize=letter,
        topMargin=0.7 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        title="4400 Prairie Crossing — Offering Memorandum (Demo Fixture)",
        author="Stonebridge Capital",
    )

    story = []

    # ---------- Cover ----------
    story.append(Spacer(1, 1.6 * inch))
    story.append(Paragraph("STONEBRIDGE CAPITAL", styles["CoverSub"]))
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("Offering Memorandum", styles["CoverTitle"]))
    story.append(Paragraph("Class B+ Suburban Infill Multifamily", styles["CoverSub"]))
    story.append(Spacer(1, 0.35 * inch))
    story.append(Paragraph("248 Units  |  Built 2006", styles["CoverMeta"]))
    story.append(Paragraph("4400 Prairie Crossing", styles["CoverMeta"]))
    story.append(Paragraph("Denver, Colorado 80238", styles["CoverMeta"]))
    story.append(Spacer(1, 1.4 * inch))
    story.append(HRFlowable(width="60%", thickness=0.75, color=GOLD, hAlign="CENTER"))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        "This is a fictional, pseudonymous demo fixture prepared for internal Soapbox "
        "RSRA (Rapid Sustainability Risk Assessment) product testing. No real property, "
        "sponsor, broker, or individual is represented. All names and figures are invented.",
        styles["Disclaimer"]
    ))
    story.append(PageBreak())

    # ---------- Page 2: Executive Summary ----------
    story.append(Paragraph("Executive Summary", styles["H1"]))
    story.append(Paragraph("Investment Overview", styles["H2"]))
    story.append(Paragraph(
        "Stonebridge Capital is pleased to offer 4400 Prairie Crossing, a 248-unit Class B+ "
        "garden-style multifamily community in the Central Park submarket of Denver, Colorado. "
        "Built in 2006 and situated on 13.2 acres, the property offers new ownership a stabilized, "
        "well-located asset with an identified value-add and sustainability capital program.",
        styles["Body"]
    ))
    story.append(Spacer(1, 6))
    story.append(table([
        ["Investment Summary", ""],
        ["Price", "Priced by Market"],
        ["Year Built", "2006"],
        ["Total Units", "248"],
        ["Net Rentable Area", "232,360 SF"],
        ["Average Unit Size", "937 SF"],
        ["Average Effective Rent", "$1,618 per unit | $1.73 per SF"],
        ["Occupancy (as of Jun 2026)", "92%"],
        ["Leased (as of Jun 2026)", "95%"],
        ["Trailing NOI", "$3,650,000 (est.)"],
        ["Implied Cap Rate", "~5.7%"],
    ], col_widths=[2.3 * inch, 3.7 * inch]))

    story.append(Paragraph("Investment Highlights", styles["H2"]))
    for b in [
        "Infill Denver location within the Central Park master-planned community, close to employment "
        "corridors, transit, and A-rated schools.",
        "Stabilized occupancy with embedded rent upside — in-place rents trail submarket comparables "
        "by an estimated 6-8%.",
        "Identified sustainability capital program (see Section 4) addresses aging central mechanical "
        "systems while qualifying for federal and utility incentives.",
        "Limited new competitive supply within a 2-mile radius.",
    ]:
        story.append(Paragraph(f"&bull;&nbsp;&nbsp;{b}", styles["OMBullet"]))

    story.append(PageBreak())

    # ---------- Page 3: Property Description ----------
    story.append(Paragraph("Property Description", styles["H1"]))
    story.append(Paragraph("Site & Construction", styles["H2"]))
    story.append(table([
        ["Attribute", "Detail"],
        ["Number of Buildings", "12 three-story garden buildings + clubhouse/leasing office"],
        ["Site Size", "13.2 acres (18.8 units/acre)"],
        ["Foundation", "Post-tensioned slab-on-grade"],
        ["Framing", "Wood frame"],
        ["Exterior Walls", "Brick veneer and cementitious fiber-cement siding"],
        ["Roofing", "Asphalt shingle, original 2006 install — approaching typical 20-yr replacement"],
        ["Windows", "Vinyl-framed double-pane, 2006-code (non-low-E)"],
        ["Parking", "Detached garages (48) + surface lot (398 spaces), 1.8 spaces/unit"],
    ], col_widths=[2.1 * inch, 3.9 * inch]))

    story.append(Paragraph("Unit Mix", styles["H2"]))
    story.append(table([
        ["Unit Type", "Units", "Avg SF", "Avg Effective Rent"],
        ["Studio", "24", "550", "$1,290"],
        ["1 Bed / 1 Bath", "124", "850", "$1,480"],
        ["2 Bed / 2 Bath", "76", "1,080", "$1,780"],
        ["3 Bed / 2 Bath", "24", "1,320", "$2,150"],
        ["Total / Weighted Avg.", "248", "937", "$1,618"],
    ], col_widths=[2.0 * inch, 1.1 * inch, 1.1 * inch, 1.8 * inch]))
    story.append(PageBreak())

    # ---------- Page 4: Mechanical / Sustainability-relevant description ----------
    story.append(Paragraph("Mechanical, Electrical & Building Systems", styles["H1"]))
    story.append(Paragraph(
        "The following systems summary is provided to support buyer capital planning and "
        "sustainability due diligence.",
        styles["Body"]
    ))
    story.append(Paragraph("Heating, Ventilation & Air Conditioning", styles["H2"]))
    for b in [
        "In-unit space heating and cooling: individual gas-fired furnaces paired with electric "
        "split-system condensers, original 2006 vintage, resident-metered.",
        "Common-area HVAC: packaged rooftop units serving the clubhouse and leasing office, "
        "replaced 2018.",
        "No central chiller plant; no known R-22 refrigerant systems remaining in service.",
    ]:
        story.append(Paragraph(f"&bull;&nbsp;&nbsp;{b}", styles["OMBullet"]))

    story.append(Paragraph("Domestic Hot Water", styles["H2"]))
    for b in [
        "Central natural gas-fired boiler plant (two boilers, original 2006 install) serves domestic "
        "hot water to all 248 units; landlord-paid, submetered to common area only.",
        "No documented boiler replacement or upgrade since original construction.",
    ]:
        story.append(Paragraph(f"&bull;&nbsp;&nbsp;{b}", styles["OMBullet"]))

    story.append(Paragraph("Envelope", styles["H2"]))
    for b in [
        "Wall assembly: 2x6 wood frame, R-13 batt insulation (2006 energy code minimum).",
        "Roof: asphalt shingle over vented attic, R-30 blown insulation, original install — nearing "
        "typical 20-year replacement window.",
        "Windows: vinyl-framed double-pane, non-low-E, original to construction.",
    ]:
        story.append(Paragraph(f"&bull;&nbsp;&nbsp;{b}", styles["OMBullet"]))

    story.append(Paragraph("Utility Structure", styles["H2"]))
    story.append(Paragraph(
        "Electricity: resident submetered (in-unit) via Xcel Energy Colorado; landlord pays common-area "
        "electric. Natural gas: landlord pays 100% (central DHW boiler plant) and residents are separately "
        "billed for in-unit furnace gas. Water/sewer: landlord-paid, billed back via RUBS.",
        styles["Body"]
    ))
    story.append(PageBreak())

    # ---------- Page 5: Financial Snapshot ----------
    story.append(Paragraph("Financial Analysis", styles["H1"]))
    story.append(Paragraph("Operating Summary (Trailing 12 Months, illustrative)", styles["H2"]))
    story.append(table([
        ["Line Item", "Annual ($)", "Per Unit ($)"],
        ["Gross Potential Rent", "4,815,000", "19,415"],
        ["Vacancy / Concessions Loss", "(385,000)", "(1,553)"],
        ["Other Income (RUBS, fees, parking)", "312,000", "1,258"],
        ["Effective Gross Income", "4,742,000", "19,121"],
        ["Operating Expenses", "(1,092,000)", "(4,403)"],
        ["  incl. Natural Gas (Common DHW Plant)", "(96,000)", "(387)"],
        ["  incl. Common-Area Electric", "(58,000)", "(234)"],
        ["Net Operating Income", "3,650,000", "14,718"],
    ], col_widths=[3.2 * inch, 1.5 * inch, 1.4 * inch]))

    story.append(Paragraph("Pricing Guidance", styles["H2"]))
    story.append(table([
        ["Metric", "Value"],
        ["Asking Price", "$64,000,000 (~$258,065/unit)"],
        ["Implied Going-In Cap Rate", "5.7%"],
        ["Terms", "All-cash preferred; conventional financing considered"],
    ], col_widths=[2.3 * inch, 3.7 * inch]))
    story.append(PageBreak())

    # ---------- Page 6: Area / Sustainability Read / Disclaimer ----------
    story.append(Paragraph("Area Overview & Sustainability Considerations", styles["H1"]))
    story.append(Paragraph("Denver / Central Park Submarket", styles["H2"]))
    story.append(Paragraph(
        "4400 Prairie Crossing is located in the Central Park submarket of northeast Denver, "
        "Colorado, within the City and County of Denver. The submarket benefits from proximity "
        "to the 40th & Colorado transit station, A-rated Denver Public Schools, and established "
        "retail along Central Park Boulevard.",
        styles["Body"]
    ))
    story.append(Paragraph("Regulatory Note", styles["H2"]))
    story.append(Paragraph(
        "The property is subject to the City and County of Denver's Energize Denver Building "
        "Performance Ordinance (buildings greater than 25,000 SF), which sets declining building-specific "
        "Energy Use Intensity (EUI) targets with interim and final compliance years. Buyers should "
        "confirm the property's current benchmarking status and any capital plan required to meet "
        "upcoming interim targets.",
        styles["Body"]
    ))
    story.append(Paragraph("Physical Risk Note", styles["H2"]))
    story.append(Paragraph(
        "The Denver front range is subject to elevated severe convective storm (hail) frequency. "
        "Prospective buyers should review current property and casualty coverage, including wind/hail "
        "deductible structure, as part of due diligence.",
        styles["Body"]
    ))
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cfcabb")))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "This Offering Memorandum is a fictional demo fixture created for Soapbox RSRA product "
        "testing purposes only. It does not describe any real property, transaction, sponsor, broker, "
        "or individual. Any resemblance to an actual address, entity, or person is coincidental. Not for "
        "distribution or investment use.",
        styles["Disclaimer"]
    ))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build()
    print(f"Wrote {OUT}")
