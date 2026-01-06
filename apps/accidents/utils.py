import os
from io import BytesIO
from django.http import HttpResponse
from django.conf import settings
import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfgen import canvas

# =============================================================================
# 1. HELPER CLASS FOR PAGE NUMBERING
# =============================================================================
class NumberedCanvas(canvas.Canvas):
    """Custom Canvas to add 'Page X of Y' numbering."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.darkgrey)
        self.drawRightString(200 * mm, 15 * mm, f"Page {self._pageNumber} of {page_count}")

# =============================================================================
# 2. MAIN PDF GENERATION VIEW
# =============================================================================
def generate_incident_pdf(incident):
    """
    Generates a professional PDF matching the official Everest incident report format,
    with automatic page flow and repeating headers.
    """
    buffer = BytesIO()
    
    # Define margins and header height
    header_height = 1.6 * inch
    left_margin = 15*mm
    right_margin = 15*mm
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=right_margin,
        leftMargin=left_margin,
        topMargin=header_height + 22*mm, # Make space for the header
        bottomMargin=25*mm
    )

    story = []

    # Calculate drawable width for tables to ensure they fit on the page
    drawable_width = A4[0] - left_margin - right_margin

    # ========================================
    # FONT & STYLE DEFINITIONS
    # ========================================
    try:
        font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf')
        pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
    except Exception:
        # Fallback if font is not found
        pass

    primary_text_color = colors.HexColor('#212529')
    secondary_text_color = colors.HexColor('#495057')
    header_bg_color = colors.HexColor('#F8F9FA')
    border_color = colors.HexColor('#DEE2E6')

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='HeaderTitle', fontSize=10, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=primary_text_color))
    styles.add(ParagraphStyle(name='HeaderInfo', fontSize=9, fontName='Helvetica', alignment=TA_LEFT, textColor=secondary_text_color, leading=12))
    styles.add(ParagraphStyle(name='ReportTitle', fontSize=11, fontName='Helvetica-Bold', alignment=TA_LEFT, textColor=primary_text_color, spaceBefore=6))
    styles.add(ParagraphStyle(name='SectionHeader', fontSize=10, fontName='Helvetica-Bold', textColor=primary_text_color, spaceBefore=8, spaceAfter=4, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='Label', fontSize=9, fontName='Helvetica-Bold', textColor=primary_text_color, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='Value', fontSize=9, fontName='Helvetica', textColor=secondary_text_color, alignment=TA_LEFT, leading=12))
    styles.add(ParagraphStyle(name='FooterText', fontSize=8, fontName='Helvetica', textColor=colors.darkgrey, alignment=TA_CENTER))
    
    # ========================================
    # HEADER TABLE (Defined once)
    # ========================================
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.jpg')
    logo_img = Image(logo_path, width=2.2*inch, height=header_height) if os.path.exists(logo_path) else Paragraph("<b>EVEREST</b>", styles['HeaderTitle'])

    header_data = [
        [logo_img, Paragraph("<b>INTEGRATED MANAGEMENT SYSTEM [QEMS]</b>", styles['HeaderTitle']), Paragraph(f"DOC NO: EIL/IRI/EHS/F-02", styles['HeaderInfo'])],
        ['', Paragraph("<b>INCIDENT REPORT</b>", styles['HeaderTitle']), Paragraph(f"REV NO: 00 &<br/>DATE: 01-09-2021", styles['HeaderInfo'])],
    ]

    header_table = Table(
        header_data,
        colWidths=[drawable_width * 0.2875, drawable_width * 0.4875, drawable_width * 0.225],
        rowHeights=[0.8*inch, 0.8*inch]
    )

    header_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('SPAN', (0, 0), (0, 1)),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    # ========================================
    # PAGE TEMPLATE FUNCTION TO DRAW HEADER
    # ========================================
    def draw_header(canvas, doc):
        canvas.saveState()
        w, h = header_table.wrap(doc.width, doc.topMargin)
        header_table.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - h + 5*mm)
        canvas.restoreState()

    # ========================================
    # INCIDENT REPORT TITLE & REF NUMBER
    # ========================================
    story.append(Spacer(1, 4*mm))
    ref_number_data = [
        [Paragraph("<b>Incident Report</b>", styles['ReportTitle']), Paragraph(f"<b>Reference number:</b><br/>{incident.report_number}", styles['HeaderInfo'])]
    ]
    ref_number_table = Table(ref_number_data, colWidths=[drawable_width * 0.7, drawable_width * 0.3])
    ref_number_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(ref_number_table)

    # ========================================
    # EMPLOYEE & INCIDENT DETAILS (FULL DETAILS)
    # ========================================
    affected_user = incident.affected_person
    age_display = f"{affected_user.age} years" if affected_user and affected_user.age is not None else 'N/A'
    gender_display = affected_user.get_gender_display() if affected_user else 'N/A'
    dob_display = affected_user.date_of_birth.strftime('%d/%m/%Y') if affected_user and affected_user.date_of_birth else 'N/A'
    job_title_display = affected_user.job_title or 'N/A' if affected_user else 'N/A'
    employment_display = affected_user.get_employment_type_display() if affected_user else 'N/A'
    
    # Calculate column widths for a 4-column layout within drawable_width
    col_width_employee = drawable_width / 4
    employee_data = [
        [Paragraph("<b>Name of Employee:</b>", styles['Label']), Paragraph(incident.affected_person_name or 'N/A', styles['Value']), Paragraph("<b>Date of occurrence:</b>", styles['Label']), Paragraph(incident.incident_date.strftime('%d/%m/%Y'), styles['Value'])],
        [Paragraph("<b>Employee code:</b>", styles['Label']), Paragraph(incident.affected_person_employee_id or 'N/A', styles['Value']), Paragraph("<b>Time of accident:</b>", styles['Label']), Paragraph(incident.incident_time.strftime('%H:%M hrs'), styles['Value'])],
        [Paragraph("<b>Age of Employee:</b>", styles['Label']), Paragraph(age_display, styles['Value']), Paragraph("<b>Gender:</b>", styles['Label']), Paragraph(gender_display, styles['Value'])],
        [Paragraph("<b>Date of Birth:</b>", styles['Label']), Paragraph(dob_display, styles['Value']), Paragraph("<b>Job Title:</b>", styles['Label']), Paragraph(job_title_display, styles['Value'])],
        [Paragraph("<b>Employment Type:</b>", styles['Label']), Paragraph(employment_display, styles['Value']), Paragraph("<b>Department:</b>", styles['Label']), Paragraph(incident.affected_person_department.name if incident.affected_person_department else 'N/A', styles['Value'])],
        [Paragraph("<b>Plant:</b>", styles['Label']), Paragraph(f"{incident.plant.name} ({incident.plant.code})", styles['Value']), Paragraph("<b>Location:</b>", styles['Label']), Paragraph(f"{incident.location.name}", styles['Value'])],
        [Paragraph("<b>Zone:</b>", styles['Label']), Paragraph(f"{incident.zone.name} ({incident.zone.code})" if incident.zone else 'N/A', styles['Value']), '', ''],
    ]
    
    employee_table = Table(employee_data, colWidths=[col_width_employee] * 4)
    employee_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(employee_table)
    
    description_data = [
        [Paragraph("<b>Brief description of the incident:</b>", styles['Label'])],
        [Paragraph(incident.description.replace('\n', '<br/>'), styles['Value'])]
    ]
    description_table = Table(description_data, colWidths=[drawable_width])
    description_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
    ]))
    story.append(description_table)
    story.append(Spacer(1, 6*mm))
    
    
    
    # ========================================
    # AFFECTED BODY PARTS (SHOW ONLY SELECTED)
    # ========================================
  
    story.append(Paragraph("<b>AFFECTED BODY PARTS</b>", styles['SectionHeader']))
    selected_parts = incident.affected_body_parts or []

    if selected_parts:
        body_parts_data = []
        num_columns = 4 
        num_rows = (len(selected_parts) + num_columns - 1) // num_columns
        
        for i in range(num_rows):
            row_data = []
            for j in range(num_columns):
                part_index = i + j * num_rows
                if part_index < len(selected_parts):
                    part = selected_parts[part_index]
                    row_data.append(Paragraph(f"• {part}", styles['Value']))
                else:
                    row_data.append('') 
            body_parts_data.append(row_data)

        body_parts_table = Table(body_parts_data, colWidths=[drawable_width / num_columns] * num_columns)
        body_parts_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, border_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(body_parts_table)
    else:
        story.append(Paragraph("No specific body parts were reported as affected.", styles['Value']))
        
    story.append(Spacer(1, 8*mm))
    
    # ========================================
    # ADDITIONAL DETAILS & REPORTING
    # ========================================
    details_table_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ])

    col_width_details_label = drawable_width * 0.3
    col_width_details_value = drawable_width * 0.7

    story.append(Paragraph("<b>ADDITIONAL INCIDENT DETAILS</b>", styles['SectionHeader']))
    additional_data = [
        [Paragraph('<b>Incident Type:</b>', styles['Label']), Paragraph(incident.get_incident_type_display(), styles['Value'])],
        [Paragraph('<b>Nature of Injury:</b>', styles['Label']), Paragraph(incident.nature_of_injury.replace('\n', '<br/>') or 'N/A', styles['Value'])],
    ]
    additional_table = Table(additional_data, colWidths=[col_width_details_label, col_width_details_value])
    additional_table.setStyle(details_table_style)
    story.append(additional_table)
    story.append(Spacer(1, 6*mm))


    # ========================================================
    # UNSAFE ACTS & CONDITIONS (SHOW ONLY SELECTED)
    # ========================================================
    selected_acts = incident.unsafe_acts or []
    selected_conditions = incident.unsafe_conditions or []

    act_flowables = [Paragraph(f"• {act}", styles['Value']) for act in selected_acts if act != 'Other (explain)']
    if 'Other (explain)' in selected_acts and incident.unsafe_acts_other:
        act_flowables.append(Paragraph(f"• <b>Other:</b> {incident.unsafe_acts_other}", styles['Value']))
    if not act_flowables:
        act_flowables = [Paragraph("N/A", styles['Value'])]

    cond_flowables = [Paragraph(f"• {cond}", styles['Value']) for cond in selected_conditions if cond != 'Other (explain)']
    if 'Other (explain)' in selected_conditions and incident.unsafe_conditions_other:
        cond_flowables.append(Paragraph(f"• <b>Other:</b> {incident.unsafe_conditions_other}", styles['Value']))
    if not cond_flowables:
        cond_flowables = [Paragraph("N/A", styles['Value'])]

    unsafe_data = [
        [Paragraph("<b>Unsafe Act(s)</b>", styles['SectionHeader']), Paragraph("<b>Unsafe Condition(s)</b>", styles['SectionHeader'])],
        [act_flowables, cond_flowables]
    ]

    unsafe_table = Table(unsafe_data, colWidths=[drawable_width / 2, drawable_width / 2])
    unsafe_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border_color),
        ('BACKGROUND', (0, 0), (-1, 0), header_bg_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(unsafe_table)
    story.append(Spacer(1, 6*mm))
    
    # ========================================================
    # [NEW] ROOT CAUSE (PERSONAL & JOB FACTORS)
    # ========================================================
    # story.append(Paragraph("<b>ROOT CAUSE(S) OF THE INCIDENT</b>", styles['SectionHeader']))
    
    # personal_factors_flowables = [Paragraph("N/A", styles['Value'])]
    # job_factors_flowables = [Paragraph("N/A", styles['Value'])]

    # Safely check if investigation report exists
    has_investigation_report = hasattr(incident, 'investigation_report') and incident.investigation_report
    has_personal_factors = has_investigation_report and incident.investigation_report.personal_factors
    has_job_factors = has_investigation_report and incident.investigation_report.job_factors

    # Only create the root cause table if at least one factor list is not empty
    if has_personal_factors or has_job_factors:
        story.append(Paragraph("<b>ROOT CAUSE(S) OF THE INCIDENT</b>", styles['SectionHeader']))
        
        # Prepare Personal Factors content
        if has_personal_factors:
            personal_factors_flowables = [
                Paragraph(f"• {pf}", styles['Value']) 
                for pf in incident.investigation_report.personal_factors
            ]
        else:
            personal_factors_flowables = [Paragraph("N/A", styles['Value'])]

        # Prepare Job Factors content
        if has_job_factors:
            job_factors_flowables = [
                Paragraph(f"• {jf}", styles['Value']) 
                for jf in incident.investigation_report.job_factors
            ]
        else:
            job_factors_flowables = [Paragraph("N/A", styles['Value'])]

        root_cause_data = [
            [Paragraph("<b>Personal Factor(s)</b>", styles['SectionHeader']), Paragraph("<b>Job Factor(s)</b>", styles['SectionHeader'])],
            [personal_factors_flowables, job_factors_flowables]
        ]

        root_cause_table = Table(root_cause_data, colWidths=[drawable_width / 2, drawable_width / 2])
        root_cause_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, border_color),
            ('BACKGROUND', (0, 0), (-1, 0), header_bg_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(root_cause_table)

    # ========================================================
    action_items = incident.action_items.all()
    if action_items.exists():
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph("<b>ACTION ITEMS / CORRECTIVE ACTIONS</b>", styles['SectionHeader']))
        
        # Table Header
        action_items_header = [
            Paragraph("<b>Action Description</b>", styles['Label']),
            Paragraph("<b>Responsible Person</b>", styles['Label']),
            Paragraph("<b>Target Date</b>", styles['Label']),
            Paragraph("<b>Status</b>", styles['Label']),
        ]
        
        action_items_data = [action_items_header]
        
        # Table Rows
        for item in action_items:
            row_data = [
                Paragraph(item.action_description.replace('\n', '<br/>'), styles['Value']),
                Paragraph(item.responsible_person.get_full_name() if item.responsible_person else 'N/A', styles['Value']),
                Paragraph(item.target_date.strftime('%d/%m/%Y') if item.target_date else 'N/A', styles['Value']),
                Paragraph(item.get_status_display(), styles['Value']),
            ]
            action_items_data.append(row_data)

        # Define column widths
        action_col_widths = [
            drawable_width * 0.45,  # Description
            drawable_width * 0.25,  # Responsible Person
            drawable_width * 0.15,  # Target Date
            drawable_width * 0.15   # Status
        ]
        
        action_items_table = Table(action_items_data, colWidths=action_col_widths)
        action_items_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, border_color),
            ('BACKGROUND', (0, 0), (-1, 0), header_bg_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(action_items_table)

    
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("<b>INVESTIGATION STATUS</b>", styles['SectionHeader']))
    investigation_data = [
        [Paragraph('<b>Investigation Required:</b>', styles['Label']), Paragraph('Yes' if incident.investigation_required else 'No', styles['Value'])],
        [Paragraph('<b>Investigation Deadline:</b>', styles['Label']), Paragraph(incident.investigation_deadline.strftime('%d/%m/%Y') if incident.investigation_deadline else 'N/A', styles['Value'])],
        [Paragraph('<b>Investigation Completed:</b>', styles['Label']), Paragraph(incident.investigation_completed_date.strftime('%d/%m/%Y') if incident.investigation_completed_date else 'Pending', styles['Value'])],
        [Paragraph('<b>Investigator:</b>', styles['Label']), Paragraph(incident.investigator.get_full_name() if incident.investigator else 'Not Assigned', styles['Value'])],
        [Paragraph('<b>Status:</b>', styles['Label']), Paragraph(incident.get_status_display(), styles['Value'])],
    ]
    investigation_table = Table(investigation_data, colWidths=[col_width_details_label, col_width_details_value])
    investigation_table.setStyle(details_table_style)
    story.append(investigation_table)
    
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("<b>REPORTING INFORMATION</b>", styles['SectionHeader']))
    reporting_data = [
        [Paragraph('<b>Reported By:</b>', styles['Label']), Paragraph(incident.reported_by.get_full_name(), styles['Value'])],
        [Paragraph('<b>Reported Date:</b>', styles['Label']), Paragraph(incident.reported_date.strftime('%d/%m/%Y %H:%M'), styles['Value'])],
        [Paragraph('<b>Last Updated:</b>', styles['Label']), Paragraph(incident.updated_at.strftime('%d/%m/%Y %H:%M'), styles['Value'])],
    ]
    reporting_table = Table(reporting_data, colWidths=[col_width_details_label, col_width_details_value])
    reporting_table.setStyle(details_table_style)
    story.append(reporting_table)
    


    story.append(Spacer(1, 10*mm))
    
    footer_text = f"Document generated from EHS-360 System on {datetime.datetime.now().strftime('%d-%b-%Y at %H:%M hrs')}"
    story.append(Paragraph(footer_text, styles['FooterText']))
    
    # ========================================
    # BUILD THE PDF
    # ========================================
    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Incident_Report_{incident.report_number}.pdf"'
    response.write(pdf)
    
    return response