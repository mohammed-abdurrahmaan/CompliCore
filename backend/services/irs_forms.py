"""
IRS Form 1094-C and 1095-C generation logic.
Handles code determination, data assembly, and PDF rendering.
"""
from datetime import datetime, timezone
from typing import Optional
import io

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


# --- IRS Line 14 Offer Codes ---
OFFER_CODES = {
    "1A": "Qualifying Offer: MV, affordable, self-only <= FPL threshold",
    "1B": "MEC providing MV offered to employee only",
    "1C": "MEC providing MV offered to employee and dependents",
    "1D": "MEC providing MV offered to employee and spouse",
    "1E": "MEC providing MV offered to employee, spouse, and dependents",
    "1F": "MEC NOT providing MV offered",
    "1G": "Offer to employee who was not full-time",
    "1H": "No offer of coverage",
}

# --- IRS Line 16 Safe Harbor / Other Codes ---
SAFE_HARBOR_CODES = {
    "2A": "Employee not employed during the month",
    "2B": "Employee not full-time during the month",
    "2C": "Employee enrolled in coverage",
    "2D": "Employee in limited non-assessment period",
    "2F": "W-2 Safe Harbor",
    "2G": "FPL Safe Harbor",
    "2H": "Rate of Pay Safe Harbor",
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def determine_line14_code(employee: dict, plan: dict = None) -> str:
    """Determine the Line 14 Offer of Coverage code for an employee."""
    is_ft = employee.get("is_full_time", False)
    offered_mec = employee.get("offered_mec", False)

    if not is_ft:
        return "1G" if offered_mec else "1H"

    if not offered_mec:
        return "1H"

    mv_meets = True
    if plan:
        mv_meets = plan.get("mv_meets_minimum", True)

    has_dependents = employee.get("num_dependents", 0) > 0
    has_spouse = bool(employee.get("spouse_name"))

    if not mv_meets:
        return "1F"

    # Check if qualifying offer (affordable + MV + self-only <= FPL)
    premium = employee.get("employee_monthly_premium", 0)
    fpl_threshold = 129.89  # 2026 monthly FPL safe harbor
    if premium <= fpl_threshold and mv_meets:
        return "1A"

    if has_spouse and has_dependents:
        return "1E"
    elif has_dependents:
        return "1C"
    elif has_spouse:
        return "1D"
    else:
        return "1B"


def determine_line16_code(employee: dict) -> str:
    """Determine the Line 16 Safe Harbor code for an employee."""
    if not employee.get("is_full_time", False):
        return "2B"

    if employee.get("enrolled", False):
        return "2C"

    # Check affordability safe harbors
    premium = employee.get("employee_monthly_premium", 0)
    w2_wages = employee.get("w2_wages", 0) or employee.get("annual_salary", 0)
    hourly_rate = employee.get("hourly_rate", 0)

    affordability_pct = 9.96

    # FPL Safe Harbor
    fpl_threshold = round(15060 * affordability_pct / 100 / 12, 2)
    if premium <= fpl_threshold:
        return "2G"

    # W-2 Safe Harbor
    if w2_wages > 0:
        w2_threshold = round(w2_wages * affordability_pct / 100 / 12, 2)
        if premium <= w2_threshold:
            return "2F"

    # Rate of Pay Safe Harbor
    if hourly_rate > 0:
        rop_threshold = round(hourly_rate * 130 * affordability_pct / 100, 2)
        if premium <= rop_threshold:
            return "2H"

    return ""


def generate_1095c_data(employee: dict, employer: dict, plan: dict, tax_year: int) -> dict:
    """Generate Form 1095-C data for a single employee."""
    line14 = determine_line14_code(employee, plan)
    line16 = determine_line16_code(employee)
    premium = employee.get("employee_monthly_premium", 0)

    monthly_data = []
    for month in range(1, 13):
        monthly_data.append({
            "month": month,
            "month_name": MONTH_NAMES[month - 1],
            "line14_code": line14,
            "line14_description": OFFER_CODES.get(line14, ""),
            "line15_premium": round(premium, 2),
            "line16_code": line16,
            "line16_description": SAFE_HARBOR_CODES.get(line16, ""),
        })

    # Part III - Covered Individuals (if self-insured)
    covered_individuals = []
    if employee.get("enrolled"):
        covered_individuals.append({
            "name": employee.get("name", ""),
            "ssn_last4": employee.get("ssn_last4", ""),
            "relationship": "Self",
            "all_12_months": True,
        })
        if employee.get("spouse_name"):
            covered_individuals.append({
                "name": employee["spouse_name"],
                "ssn_last4": "",
                "relationship": "Spouse",
                "all_12_months": True,
            })
        for dep in employee.get("dependents", []):
            covered_individuals.append({
                "name": dep.get("name", ""),
                "ssn_last4": "",
                "relationship": "Dependent",
                "all_12_months": True,
            })

    return {
        "form_type": "1095-C",
        "tax_year": tax_year,
        "part1": {
            "employee_name": employee.get("name", ""),
            "employee_ssn_last4": employee.get("ssn_last4", ""),
            "employee_address": employee.get("address", ""),
            "employer_name": employer.get("name", ""),
            "employer_ein": employer.get("ein", ""),
            "employer_address": employer.get("address", ""),
            "employer_contact_phone": employer.get("contact_email", ""),
        },
        "part2": {
            "monthly_data": monthly_data,
            "all_12_months_same": True,
            "line14_all_year": line14,
            "line15_all_year": round(premium, 2),
            "line16_all_year": line16,
        },
        "part3": {
            "covered_individuals": covered_individuals,
            "is_self_insured": len(covered_individuals) > 0,
        },
        "employee_id": employee.get("id", ""),
        "employer_id": employer.get("id", ""),
    }


def generate_1094c_data(employer: dict, employees: list, plans: list, tax_year: int) -> dict:
    """Generate Form 1094-C data for an employer."""
    ft_employees = [e for e in employees if e.get("is_full_time")]
    pt_employees = [e for e in employees if not e.get("is_full_time")]
    pt_hours = sum(e.get("monthly_hours", 0) for e in pt_employees)
    fte = round(pt_hours / 120, 2)
    total_fte = len(ft_employees) + fte
    is_ale = total_fte >= 50

    # Monthly counts
    monthly_counts = []
    for month in range(1, 13):
        ft_count = len(ft_employees)
        total_count = len(employees)
        monthly_counts.append({
            "month": month,
            "month_name": MONTH_NAMES[month - 1],
            "ft_employee_count": ft_count,
            "total_employee_count": total_count,
            "aggregated_group": False,
            "section_4980h_transition_relief": "",
        })

    mec_offered_count = sum(1 for e in ft_employees if e.get("offered_mec"))
    mec_pct = round((mec_offered_count / len(ft_employees) * 100), 1) if ft_employees else 0

    return {
        "form_type": "1094-C",
        "tax_year": tax_year,
        "part1": {
            "employer_name": employer.get("name", ""),
            "employer_ein": employer.get("ein", ""),
            "employer_address": employer.get("address", ""),
            "contact_name": employer.get("name", ""),
            "contact_phone": employer.get("contact_email", ""),
        },
        "part2": {
            "total_1095c_forms": len(ft_employees),
            "is_ale_member": is_ale,
            "is_authoritative_transmittal": True,
            "total_fte": round(total_fte, 2),
            "mec_offered_to_pct": mec_pct,
            "transition_relief": False,
            "plan_start_month": 1,
        },
        "part3": {
            "monthly_data": monthly_counts,
        },
        "part4": {
            "other_ale_members": [],
        },
        "summary": {
            "total_employees": len(employees),
            "full_time_employees": len(ft_employees),
            "part_time_employees": len(pt_employees),
            "fte_from_part_time": fte,
            "total_fte": round(total_fte, 2),
            "is_ale": is_ale,
            "plans_count": len(plans),
            "mec_offered_count": mec_offered_count,
            "mec_coverage_pct": mec_pct,
        },
        "employer_id": employer.get("id", ""),
    }


def render_1094c_pdf(form_data: dict) -> bytes:
    """Render Form 1094-C as a PDF document."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("FormTitle", parent=styles["Title"], fontSize=16, spaceAfter=6)
    subtitle_style = ParagraphStyle("FormSubtitle", parent=styles["Normal"], fontSize=10,
                                    textColor=colors.grey, spaceAfter=12)
    heading_style = ParagraphStyle("SectionHead", parent=styles["Heading2"], fontSize=12,
                                   spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#1a365d"))
    normal = styles["Normal"]

    elements = []

    # Title
    elements.append(Paragraph("Form 1094-C", title_style))
    elements.append(Paragraph(
        f"Transmittal of Employer-Provided Health Insurance Offer and Coverage Information Returns &mdash; Tax Year {form_data['tax_year']}",
        subtitle_style))

    # Part I - ALE Member
    elements.append(Paragraph("Part I &mdash; Applicable Large Employer Member (ALE Member)", heading_style))
    p1 = form_data["part1"]
    info_data = [
        ["Employer Name:", p1.get("employer_name", "")],
        ["EIN:", p1.get("employer_ein", "")],
        ["Address:", p1.get("employer_address", "")],
        ["Contact:", p1.get("contact_phone", "")],
    ]
    t = Table(info_data, colWidths=[1.8 * inch, 4.5 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))

    # Part II
    elements.append(Paragraph("Part II &mdash; ALE Member Information", heading_style))
    p2 = form_data["part2"]
    info2 = [
        ["Total 1095-C Forms Filed:", str(p2.get("total_1095c_forms", 0))],
        ["Is ALE Member:", "Yes" if p2.get("is_ale_member") else "No"],
        ["Authoritative Transmittal:", "Yes" if p2.get("is_authoritative_transmittal") else "No"],
        ["Total FTE Count:", str(p2.get("total_fte", 0))],
        ["MEC Offered %:", f"{p2.get('mec_offered_to_pct', 0)}%"],
    ]
    t2 = Table(info2, colWidths=[2.2 * inch, 4.1 * inch])
    t2.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 10))

    # Part III - Monthly
    elements.append(Paragraph("Part III &mdash; ALE Member Information &mdash; Monthly", heading_style))
    header = ["Month", "FT Employees", "Total Employees", "Aggregated Group"]
    rows = [header]
    for m in form_data["part3"]["monthly_data"]:
        rows.append([
            m["month_name"],
            str(m["ft_employee_count"]),
            str(m["total_employee_count"]),
            "Yes" if m["aggregated_group"] else "No",
        ])
    t3 = Table(rows, colWidths=[1.2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a365d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
    ]))
    elements.append(t3)

    doc.build(elements)
    return buffer.getvalue()


def render_1095c_pdf(form_data: dict) -> bytes:
    """Render Form 1095-C as a PDF matching the official IRS form layout."""
    from reportlab.pdfgen import canvas as pdfcanvas

    buffer = io.BytesIO()
    c = pdfcanvas.Canvas(buffer, pagesize=letter)
    w, h = letter  # 612 x 792

    # Margins and layout constants
    LM = 36  # left margin
    RM = w - 36  # right margin
    TM = h - 30  # top margin start
    BW = RM - LM  # box width

    # Colors
    DARK = colors.HexColor("#1a202c")
    GREY = colors.HexColor("#4a5568")
    LIGHT_GREY = colors.HexColor("#a0aec0")
    FILL_BG = colors.HexColor("#f7fafc")
    HEADER_BG = colors.HexColor("#1a365d")

    def draw_box(x, y, bw, bh):
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        c.rect(x, y, bw, bh)

    def draw_thick_box(x, y, bw, bh):
        c.setStrokeColor(colors.black)
        c.setLineWidth(1.5)
        c.rect(x, y, bw, bh)

    def text_at(x, y, txt, size=8, bold=False, color=DARK):
        c.setFillColor(color)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(x, y, str(txt))

    p1 = form_data.get("part1", {})
    p2 = form_data.get("part2", {})
    p3 = form_data.get("part3", {})
    tax_year = form_data.get("tax_year", 2026)

    # ========== HEADER ==========
    y = TM
    # Form number block
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(LM, y, "Form")
    c.setFont("Helvetica-Bold", 22)
    c.drawString(LM, y - 22, "1095-C")
    c.setFont("Helvetica", 6)
    c.drawString(LM, y - 32, "Department of the Treasury")
    c.drawString(LM, y - 40, "Internal Revenue Service")

    # Title
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(w / 2, y - 6, "Employer-Provided Health Insurance")
    c.drawCentredString(w / 2, y - 18, "Offer and Coverage")
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(w / 2, y - 28, "Do not attach to your tax return. Keep for your records.")
    c.drawCentredString(w / 2, y - 37, "Go to www.irs.gov/Form1095C for instructions and the latest information.")

    # VOID / CORRECTED boxes (right side)
    vx = RM - 120
    draw_box(vx, y - 6, 10, 10)
    text_at(vx + 14, y - 4, "VOID", 7, True)
    draw_box(vx, y - 22, 10, 10)
    text_at(vx + 14, y - 20, "CORRECTED", 7, True)

    # OMB and Tax Year
    text_at(RM - 60, y, "OMB No. 1545-2251", 6, False, GREY)
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(RM, y - 22, f"20{str(tax_year)[-2:]}")
    c.setFont("Helvetica", 6)
    c.drawRightString(RM, y - 32, f"Tax Year {tax_year}")

    y -= 52
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.line(LM, y, RM, y)

    # ========== PART I: Employee & Employer Information ==========
    y -= 14
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    # Part I header with black background
    c.setFillColor(HEADER_BG)
    c.rect(LM, y - 2, BW, 14, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(LM + 4, y + 1, "Part I")
    c.setFont("Helvetica-Bold", 8)
    c.drawString(LM + 40, y + 1, "Employee")
    mid_x = LM + BW * 0.52
    c.drawString(mid_x, y + 1, "Applicable Large Employer Member (Employer)")

    y -= 16
    row_h = 32
    half_w = BW * 0.52

    # Row 1: Employee Name (1) | SSN (2) | Employer Name (7) | EIN (8)
    draw_box(LM, y - row_h, half_w * 0.65, row_h)
    draw_box(LM + half_w * 0.65, y - row_h, half_w * 0.35, row_h)
    draw_box(mid_x, y - row_h, (RM - mid_x) * 0.6, row_h)
    draw_box(mid_x + (RM - mid_x) * 0.6, y - row_h, (RM - mid_x) * 0.4, row_h)

    text_at(LM + 3, y - 8, "1 Name of employee (first, middle initial, last)", 5.5, False, GREY)
    text_at(LM + 3, y - 22, p1.get("employee_name", ""), 9, True)
    text_at(LM + half_w * 0.65 + 3, y - 8, "2 Social security number (SSN)", 5.5, False, GREY)
    ssn = f"XXX-XX-{p1.get('employee_ssn_last4', '****')}"
    text_at(LM + half_w * 0.65 + 3, y - 22, ssn, 9, True)
    text_at(mid_x + 3, y - 8, "7 Name of employer", 5.5, False, GREY)
    text_at(mid_x + 3, y - 22, p1.get("employer_name", ""), 9, True)
    ein_x = mid_x + (RM - mid_x) * 0.6
    text_at(ein_x + 3, y - 8, "8 Employer identification number (EIN)", 5.5, False, GREY)
    text_at(ein_x + 3, y - 22, p1.get("employer_ein", ""), 9, True)
    y -= row_h

    # Row 2: Employee Address (3) | Employer Address (9) | Phone (10)
    draw_box(LM, y - row_h, half_w, row_h)
    draw_box(mid_x, y - row_h, (RM - mid_x) * 0.65, row_h)
    draw_box(mid_x + (RM - mid_x) * 0.65, y - row_h, (RM - mid_x) * 0.35, row_h)

    text_at(LM + 3, y - 8, "3 Street address (including apartment no.)", 5.5, False, GREY)
    text_at(LM + 3, y - 22, p1.get("employee_address", ""), 8)
    text_at(mid_x + 3, y - 8, "9 Street address (including room or suite no.)", 5.5, False, GREY)
    text_at(mid_x + 3, y - 22, p1.get("employer_address", ""), 8)
    phone_x = mid_x + (RM - mid_x) * 0.65
    text_at(phone_x + 3, y - 8, "10 Contact telephone number", 5.5, False, GREY)
    text_at(phone_x + 3, y - 22, p1.get("employer_contact_phone", ""), 8)
    y -= row_h

    # Row 3: City/State/Zip (4,5,6) | City/State/Zip (11,12,13)
    third_w = half_w / 3
    draw_box(LM, y - row_h, third_w, row_h)
    draw_box(LM + third_w, y - row_h, third_w, row_h)
    draw_box(LM + 2 * third_w, y - row_h, half_w - 2 * third_w, row_h)

    er_third = (RM - mid_x) / 3
    draw_box(mid_x, y - row_h, er_third, row_h)
    draw_box(mid_x + er_third, y - row_h, er_third, row_h)
    draw_box(mid_x + 2 * er_third, y - row_h, (RM - mid_x) - 2 * er_third, row_h)

    text_at(LM + 3, y - 8, "4 City or town", 5.5, False, GREY)
    text_at(LM + third_w + 3, y - 8, "5 State or province", 5.5, False, GREY)
    text_at(LM + 2 * third_w + 3, y - 8, "6 Country and ZIP or foreign postal code", 5.5, False, GREY)
    text_at(mid_x + 3, y - 8, "11 City or town", 5.5, False, GREY)
    text_at(mid_x + er_third + 3, y - 8, "12 State or province", 5.5, False, GREY)
    text_at(mid_x + 2 * er_third + 3, y - 8, "13 Country and ZIP", 5.5, False, GREY)
    y -= row_h

    y -= 8

    # ========== PART II: Employee Offer of Coverage ==========
    c.setFillColor(HEADER_BG)
    c.rect(LM, y - 2, BW, 14, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(LM + 4, y + 1, "Part II")
    c.drawString(LM + 42, y + 1, "Employee Offer of Coverage")

    y -= 18
    # Column layout: Label col + "All 12 Months" + 12 monthly cols
    label_w = 80
    all12_w = 52
    month_w = (BW - label_w - all12_w) / 12
    col_h = 36
    hdr_h = 14

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Column headers
    draw_box(LM, y - hdr_h, label_w, hdr_h)
    draw_box(LM + label_w, y - hdr_h, all12_w, hdr_h)
    c.setFont("Helvetica-Bold", 5.5)
    c.setFillColor(DARK)
    c.drawCentredString(LM + label_w + all12_w / 2, y - 10, "All 12")
    c.drawCentredString(LM + label_w + all12_w / 2, y - 4, "Months")

    for i, mn in enumerate(months):
        mx = LM + label_w + all12_w + i * month_w
        draw_box(mx, y - hdr_h, month_w, hdr_h)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawCentredString(mx + month_w / 2, y - 10, mn)
    y -= hdr_h

    monthly = p2.get("monthly_data", [])
    line14_all = p2.get("line14_all_year", "")
    line15_all = p2.get("line15_all_year", 0)
    line16_all = p2.get("line16_all_year", "")

    # Line 14 row
    draw_box(LM, y - col_h, label_w, col_h)
    c.setFont("Helvetica-Bold", 6)
    c.setFillColor(DARK)
    c.drawString(LM + 3, y - 10, "14 Offer of")
    c.drawString(LM + 3, y - 18, "Coverage (enter")
    c.drawString(LM + 3, y - 26, "required code)")

    draw_box(LM + label_w, y - col_h, all12_w, col_h)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(LM + label_w + all12_w / 2, y - 22, line14_all)

    for i in range(12):
        mx = LM + label_w + all12_w + i * month_w
        draw_box(mx, y - col_h, month_w, col_h)
        val = monthly[i]["line14_code"] if i < len(monthly) else ""
        c.setFont("Helvetica", 7)
        c.drawCentredString(mx + month_w / 2, y - 22, val)
    y -= col_h

    # Line 15 row
    draw_box(LM, y - col_h, label_w, col_h)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(LM + 3, y - 10, "15 Employee")
    c.drawString(LM + 3, y - 18, "Required")
    c.drawString(LM + 3, y - 26, "Contribution")

    draw_box(LM + label_w, y - col_h, all12_w, col_h)
    c.setFont("Helvetica", 8)
    c.drawCentredString(LM + label_w + all12_w / 2, y - 22, f"${line15_all:.2f}")

    for i in range(12):
        mx = LM + label_w + all12_w + i * month_w
        draw_box(mx, y - col_h, month_w, col_h)
        val = monthly[i]["line15_premium"] if i < len(monthly) else 0
        c.setFont("Helvetica", 6)
        c.drawCentredString(mx + month_w / 2, y - 15, "$")
        c.drawCentredString(mx + month_w / 2, y - 24, f"{val:.2f}")
    y -= col_h

    # Line 16 row
    draw_box(LM, y - col_h, label_w, col_h)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(LM + 3, y - 10, "16 Section 4980H")
    c.drawString(LM + 3, y - 18, "Safe Harbor and")
    c.drawString(LM + 3, y - 26, "Other Relief")

    draw_box(LM + label_w, y - col_h, all12_w, col_h)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(LM + label_w + all12_w / 2, y - 22, line16_all or "")

    for i in range(12):
        mx = LM + label_w + all12_w + i * month_w
        draw_box(mx, y - col_h, month_w, col_h)
        val = monthly[i]["line16_code"] if i < len(monthly) else ""
        c.setFont("Helvetica", 7)
        c.drawCentredString(mx + month_w / 2, y - 22, val or "")
    y -= col_h

    # Line 17 ZIP row (shorter)
    zip_h = 20
    draw_box(LM, y - zip_h, label_w, zip_h)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(LM + 3, y - 14, "17 ZIP Code")
    draw_box(LM + label_w, y - zip_h, BW - label_w, zip_h)
    y -= zip_h

    y -= 10

    # ========== PART III: Covered Individuals ==========
    covered = p3.get("covered_individuals", [])
    c.setFillColor(HEADER_BG)
    c.rect(LM, y - 2, BW, 14, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(LM + 4, y + 1, "Part III")
    c.drawString(LM + 46, y + 1, "Covered Individuals (if self-insured coverage)")
    y -= 18

    if covered:
        ci_cols = [BW * 0.35, BW * 0.15, BW * 0.2, BW * 0.15, BW * 0.15]
        ci_headers = ["Name", "SSN", "Relationship", "DOB", "All 12 Mo."]
        ci_row_h = 16

        # Header row
        cx = LM
        for j, hd in enumerate(ci_headers):
            draw_box(cx, y - ci_row_h, ci_cols[j], ci_row_h)
            c.setFillColor(colors.HexColor("#edf2f7"))
            c.rect(cx + 0.5, y - ci_row_h + 0.5, ci_cols[j] - 1, ci_row_h - 1, fill=1)
            c.setFillColor(DARK)
            c.setFont("Helvetica-Bold", 6)
            c.drawString(cx + 3, y - 11, hd)
            cx += ci_cols[j]
        y -= ci_row_h

        for ci in covered:
            cx = LM
            vals = [
                ci.get("name", ""),
                f"XXX-XX-{ci.get('ssn_last4', '****')}" if ci.get("ssn_last4") else "-",
                ci.get("relationship", ""),
                ci.get("dob", ""),
                "Yes" if ci.get("all_12_months") else "No",
            ]
            for j, v in enumerate(vals):
                draw_box(cx, y - ci_row_h, ci_cols[j], ci_row_h)
                c.setFont("Helvetica", 7)
                c.setFillColor(DARK)
                c.drawString(cx + 3, y - 11, str(v))
                cx += ci_cols[j]
            y -= ci_row_h
    else:
        text_at(LM + 4, y - 12, "No covered individuals listed (not self-insured or no enrollment).", 7, False, GREY)
        y -= 20

    # ========== FOOTER ==========
    y = 30
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.line(LM, y + 10, RM, y + 10)
    c.setFont("Helvetica", 5.5)
    c.setFillColor(GREY)
    c.drawString(LM, y, "For Privacy Act and Paperwork Reduction Act Notice, see separate instructions.")
    c.drawCentredString(w / 2, y, "Cat. No. 60705M")
    c.drawRightString(RM, y, f"Form 1095-C ({tax_year})")

    c.save()
    return buffer.getvalue()
