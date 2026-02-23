import os
from io import BytesIO
from django.http import HttpResponse
from django.conf import settings
import datetime
from django.db.models import Q
from .models import Incident

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.pdfgen import canvas

# =============================================================================
# 1. Helper class for page numbering
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
# 2. Main PDF Generation Function
# =============================================================================
def generate_incident_pdf(incident):
    """
    Generates a professional PDF matching the official incident report format,
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
    # Font & Style Definitions
    # ========================================
    try:
        # Ensure the font file is available at this path in your project
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
    styles.add(ParagraphStyle(name='SectionHeader', fontSize=10, fontName='Helvetica-Bold', textColor=primary_text_color, spaceBefore=10, spaceAfter=4, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='Label', fontSize=9, fontName='Helvetica-Bold', textColor=primary_text_color, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='Value', fontSize=9, fontName='Helvetica', textColor=secondary_text_color, alignment=TA_LEFT, leading=12))
    styles.add(ParagraphStyle(name='FooterText', fontSize=8, fontName='Helvetica', textColor=colors.darkgrey, alignment=TA_CENTER))

    # Helper function to handle empty values and format strings
    def get_val(value, default='N/A'):
        if value:
            # If it's a string, strip whitespace and replace newlines with <br/> for ReportLab
            if isinstance(value, str):
                return value.strip().replace('\n', '<br/>')
            return value
        return default

    # ========================================
    # Header Table (Defined once)
    # ========================================
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.jpg')
    logo_img = Image(logo_path, width=2.2*inch, height=header_height) if os.path.exists(logo_path) else Paragraph("<b>COMPANY LOGO</b>", styles['HeaderTitle'])

    header_data = [
        [logo_img, Paragraph("<b>INJURY'S MANAGEMENT SYSTEM [QEMS]</b>", styles['HeaderTitle']), Paragraph(f"DOC NO: EIL/IRI/EHS/F-02", styles['HeaderInfo'])],
        ['', Paragraph("<b>INJURY REPORT</b>", styles['HeaderTitle']), Paragraph(f"REV NO: 00 &<br/>DATE: 01-09-2021", styles['HeaderInfo'])],
    ]
    header_table = Table(header_data, colWidths=[drawable_width * 0.2875, drawable_width * 0.4875, drawable_width * 0.225], rowHeights=[0.8*inch, 0.8*inch])
    header_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border_color), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('SPAN', (0, 0), (0, 1)), ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    # ========================================
    # Page Template Function to draw the header
    # ========================================
    def draw_header(canvas, doc):
        canvas.saveState()
        w, h = header_table.wrap(doc.width, doc.topMargin)
        header_table.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - h + 5*mm)
        canvas.restoreState()

    # ========================================
    # Incident Report Title & Reference Number
    # ========================================
    story.append(Spacer(1, 4*mm))
    ref_number_data = [
        [Paragraph("<b>Injury Report</b>", styles['ReportTitle']), Paragraph(f"<b>Reference number:</b><br/>{incident.report_number}", styles['HeaderInfo'])]
    ]
    ref_number_table = Table(ref_number_data, colWidths=[drawable_width * 0.7, drawable_width * 0.3])
    ref_number_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border_color), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(ref_number_table)

    # ========================================
    # Employee & Incident Full Details
    # ========================================
    story.append(Paragraph("<b>SECTION 1: INJURY & PERSONNEL DETAILS</b>", styles['SectionHeader']))
    
    # Get values directly from the incident model for manual entries
    dob_display = incident.affected_date_of_birth.strftime('%d/%m/%Y') if incident.affected_date_of_birth else 'N/A'
    doj_display = incident.affected_date_of_joining.strftime('%d/%m/%Y') if incident.affected_date_of_joining else 'N/A'
    age_display = f"{incident.affected_age} years" if incident.affected_age is not None else 'N/A'

    # 4-column layout for better space utilization
    col_width = drawable_width / 4
    employee_data = [
        [Paragraph("<b>Name of Employee:</b>", styles['Label']), Paragraph(get_val(incident.affected_person_name), styles['Value']), Paragraph("<b>Date of occurrence:</b>", styles['Label']), Paragraph(incident.incident_date.strftime('%d/%m/%Y'), styles['Value'])],
        [Paragraph("<b>Employee code:</b>", styles['Label']), Paragraph(get_val(incident.affected_person_employee_id), styles['Value']), Paragraph("<b>Time of accident:</b>", styles['Label']), Paragraph(incident.incident_time.strftime('%H:%M hrs'), styles['Value'])],
        [Paragraph("<b>Employment Type:</b>", styles['Label']), Paragraph(get_val(incident.get_affected_employment_category_display()), styles['Value']), Paragraph("<b>Department:</b>", styles['Label']), Paragraph(get_val(incident.affected_person_department.name if incident.affected_person_department else ''), styles['Value'])],
        [Paragraph("<b>Date of Birth:</b>", styles['Label']), Paragraph(dob_display, styles['Value']), Paragraph("<b>Age of Employee:</b>", styles['Label']), Paragraph(age_display, styles['Value'])],
        [Paragraph("<b>Date of Joining:</b>", styles['Label']), Paragraph(doj_display, styles['Value']), Paragraph("<b>Gender:</b>", styles['Label']), Paragraph(get_val(incident.get_affected_gender_display()), styles['Value'])],
        [Paragraph("<b>Job Title:</b>", styles['Label']), Paragraph(get_val(incident.affected_job_title), styles['Value']), Paragraph("<b>Plant:</b>", styles['Label']), Paragraph(get_val(incident.plant.name), styles['Value'])],
        [Paragraph("<b>Zone:</b>", styles['Label']), Paragraph(get_val(incident.zone.name if incident.zone else ''), styles['Value']), Paragraph("<b>Location:</b>", styles['Label']), Paragraph(get_val(incident.location.name), styles['Value'])],
        [Paragraph("<b>Sub-Location:</b>", styles['Label']), Paragraph(get_val(incident.sublocation.name if incident.sublocation else ''), styles['Value']), Paragraph("<b>Additional Details:</b>", styles['Label']), Paragraph(get_val(incident.additional_location_details), styles['Value'])],
    ]
    
    employee_table = Table(employee_data, colWidths=[col_width] * 4)
    employee_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border_color), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(employee_table)
    
    description_data = [
        [Paragraph("<b>Brief description of the Injury / Sequence of events:</b>", styles['Label'])],
        [Paragraph(get_val(incident.description), styles['Value'])]
    ]
    description_table = Table(description_data, colWidths=[drawable_width])
    description_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border_color), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('BACKGROUND', (0,0), (-1,0), header_bg_color)
    ]))
    story.append(description_table)
    
    # ========================================
    # Injury Details & Affected Body Parts
    # ========================================
    story.append(Paragraph("<b>SECTION 2: INJURY & CAUSAL FACTORS</b>", styles['SectionHeader']))

    injury_data = [
        [Paragraph('<b>Injury Type:</b>', styles['Label']), Paragraph(get_val(incident.incident_type.name if incident.incident_type else 'N/A'), styles['Value'])],
        [Paragraph('<b>Nature of Injury:</b>', styles['Label']), Paragraph(get_val(incident.nature_of_injury), styles['Value'])],
    ]
    injury_table = Table(injury_data, colWidths=[drawable_width * 0.25, drawable_width * 0.75])
    injury_table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 1, border_color), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    story.append(injury_table)

    selected_parts = incident.affected_body_parts or []
    if selected_parts:
        story.append(Spacer(1, 2*mm))
        body_parts_data = [[Paragraph("<b>Affected Body Parts:</b>", styles['Label']), Paragraph(", ".join(selected_parts), styles['Value'])]]
        body_parts_table = Table(body_parts_data, colWidths=[drawable_width * 0.25, drawable_width * 0.75])
        body_parts_table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 1, border_color), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story.append(body_parts_table)

    story.append(Spacer(1, 4*mm))

    # ========================================================
    # Unsafe Acts & Conditions
    # ===========================================================
    selected_acts = incident.unsafe_acts or []
    selected_conditions = incident.unsafe_conditions or []

    act_flowables = [Paragraph(f"• {act}", styles['Value']) for act in selected_acts if act != 'Other (explain)']
    if 'Other (explain)' in selected_acts and incident.unsafe_acts_other:
        act_flowables.append(Paragraph(f"• <b>Other:</b> {get_val(incident.unsafe_acts_other)}", styles['Value']))
    if not act_flowables: act_flowables = [Paragraph("N/A", styles['Value'])]

    cond_flowables = [Paragraph(f"• {cond}", styles['Value']) for cond in selected_conditions if cond != 'Other (explain)']
    if 'Other (explain)' in selected_conditions and incident.unsafe_conditions_other:
        cond_flowables.append(Paragraph(f"• <b>Other:</b> {get_val(incident.unsafe_conditions_other)}", styles['Value']))
    if not cond_flowables: cond_flowables = [Paragraph("N/A", styles['Value'])]

    unsafe_data = [
        [Paragraph("<b>Unsafe Act(s) Identified</b>", styles['Label']), Paragraph("<b>Unsafe Condition(s) Identified</b>", styles['Label'])],
        [act_flowables, cond_flowables]
    ]
    unsafe_table = Table(unsafe_data, colWidths=[drawable_width / 2, drawable_width / 2])
    unsafe_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, border_color), ('BACKGROUND', (0, 0), (-1, 0), header_bg_color), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(unsafe_table)
    
    # ========================================================
    # Investigation Report (if it exists)
    # ========================================================
    if hasattr(incident, 'investigation_report') and incident.investigation_report:
        story.append(PageBreak())
        story.append(Paragraph("<b>SECTION 3: INVESTIGATION FINDINGS</b>", styles['SectionHeader']))
        investigation = incident.investigation_report
        
        invest_details_data = [
            [Paragraph("<b>Investigation Date:</b>", styles['Label']), Paragraph(investigation.investigation_date.strftime('%d/%m/%Y'), styles['Value']), Paragraph("<b>Lead Investigator:</b>", styles['Label']), Paragraph(get_val(investigation.investigator.get_full_name()), styles['Value'])],
            [Paragraph("<b>Investigation Team Members Emails:</b>", styles['Label']), Paragraph(get_val(investigation.investigation_team), styles['Value']), '', ''],
        ]
        invest_details_table = Table(invest_details_data, colWidths=[col_width] * 4)
        invest_details_table.setStyle(TableStyle([('GRID', (0,0),(-1,-1),1,border_color), ('VALIGN',(0,0),(-1,-1),'TOP'), ('SPAN', (1, 1), (3, 1)), ('LEFTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story.append(invest_details_table)

        # Single-column table for long text fields in the investigation report
        single_col_table_data = [
            [Paragraph("<b>Sequence of Events (during investigation):</b>", styles['Label'])], [Paragraph(get_val(investigation.sequence_of_events), styles['Value'])],
            [Paragraph("<b>Root Cause Analysis:</b>", styles['Label'])], [Paragraph(get_val(investigation.root_cause_analysis), styles['Value'])],
            [Paragraph("<b>Immediate Corrective Actions Taken:</b>", styles['Label'])], [Paragraph(get_val(investigation.immediate_corrective_actions), styles['Value'])],
            [Paragraph("<b>Preventive Measures Recommended:</b>", styles['Label'])], [Paragraph(get_val(investigation.preventive_measures), styles['Value'])],
            [Paragraph("<b>Witness Statements Summary:</b>", styles['Label'])], [Paragraph(get_val(investigation.witness_statements), styles['Value'])],
            [Paragraph("<b>Evidence Collected:</b>", styles['Label'])], [Paragraph(get_val(investigation.evidence_collected), styles['Value'])],
        ]
        single_col_table = Table(single_col_table_data, colWidths=[drawable_width])
        single_col_table.setStyle(TableStyle([
            ('GRID', (0,0),(-1,-1),1,border_color), ('VALIGN',(0,0),(-1,-1),'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 6), 
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 0), (0, 0), header_bg_color), ('BACKGROUND', (0, 2), (0, 2), header_bg_color), 
            ('BACKGROUND', (0, 4), (0, 4), header_bg_color), ('BACKGROUND', (0, 6), (0, 6), header_bg_color),
            ('BACKGROUND', (0, 8), (0, 8), header_bg_color), ('BACKGROUND', (0, 10), (0, 10), header_bg_color)
        ]))
        story.append(single_col_table)
        story.append(Spacer(1, 4*mm))

        # Personal and Job Factors
        has_personal_factors = hasattr(investigation, 'personal_factors') and investigation.personal_factors
        has_job_factors = hasattr(investigation, 'job_factors') and investigation.job_factors
        if has_personal_factors or has_job_factors:
            personal_factors_flowables = [Paragraph(f"• {pf}", styles['Value']) for pf in investigation.personal_factors] if has_personal_factors else [Paragraph("N/A", styles['Value'])]
            job_factors_flowables = [Paragraph(f"• {jf}", styles['Value']) for jf in investigation.job_factors] if has_job_factors else [Paragraph("N/A", styles['Value'])]
            
            root_cause_data = [
                [Paragraph("<b>Identified Personal Factor(s)</b>", styles['Label']), Paragraph("<b>Identified Job Factor(s)</b>", styles['Label'])],
                [personal_factors_flowables, job_factors_flowables]
            ]
            root_cause_table = Table(root_cause_data, colWidths=[drawable_width / 2, drawable_width / 2])
            root_cause_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, border_color), ('BACKGROUND', (0, 0), (-1, 0), header_bg_color), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(root_cause_table)

    # ========================================================
    # Action Items
    # ========================================================
    action_items = incident.action_items.all()
    if action_items.exists():
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph("<b>SECTION 4: CORRECTIVE & PREVENTIVE ACTION ITEMS</b>", styles['SectionHeader']))
        
        action_items_header = [Paragraph("<b>Action Description</b>", styles['Label']), Paragraph("<b>Responsible Person(s)</b>", styles['Label']), Paragraph("<b>Target Date</b>", styles['Label']), Paragraph("<b>Status</b>", styles['Label'])]
        action_items_data = [action_items_header]
        
        for item in action_items:
            # Correctly handle ManyToManyField for responsible persons
            responsible_names = ", ".join([user.get_full_name() for user in item.responsible_person.all()])
            row_data = [
                Paragraph(get_val(item.action_description), styles['Value']),
                Paragraph(get_val(responsible_names, 'Not Assigned'), styles['Value']),
                Paragraph(item.target_date.strftime('%d/%m/%Y') if item.target_date else 'N/A', styles['Value']),
                Paragraph(item.get_status_display(), styles['Value']),
            ]
            action_items_data.append(row_data)

        action_col_widths = [drawable_width * 0.45, drawable_width * 0.25, drawable_width * 0.15, drawable_width * 0.15]
        action_items_table = Table(action_items_data, colWidths=action_col_widths)
        action_items_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, border_color), ('BACKGROUND', (0, 0), (-1, 0), header_bg_color), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(action_items_table)

    # ========================================================
    # Closure Information (if incident is closed)
    # ========================================================
    if incident.status == 'CLOSED':
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph("<b>SECTION 5: INJURY CLOSURE DETAILS</b>", styles['SectionHeader']))
        
        # Using a single-column table style for long remarks
        closure_details_data = [
            [Paragraph("<b>Closure Date:</b>", styles['Label']), Paragraph(incident.closure_date.strftime('%d/%m/%Y %H:%M') if incident.closure_date else 'N/A', styles['Value'])],
            [Paragraph("<b>Closed By:</b>", styles['Label']), Paragraph(get_val(incident.closed_by.get_full_name() if incident.closed_by else ''), styles['Value'])],
            [Paragraph("<b>Is Recurrence Possible?</b>", styles['Label']), Paragraph("Yes" if incident.is_recurrence_possible else "No", styles['Value'])],
        ]
        closure_details_table = Table(closure_details_data, colWidths=[drawable_width * 0.25, drawable_width * 0.75])
        closure_details_table.setStyle(TableStyle([('GRID', (0,0),(-1,-1),1,border_color),('VALIGN',(0,0),(-1,-1),'TOP'), ('LEFTPADDING', (0,0),(-1,-1),6), ('TOPPADDING', (0,0),(-1,-1),4), ('BOTTOMPADDING', (0,0),(-1,-1),4)]))
        story.append(closure_details_table)

        closure_remarks_data = [
            [Paragraph("<b>Final Preventive Measures Implemented:</b>", styles['Label'])], [Paragraph(get_val(incident.preventive_measures), styles['Value'])],
            [Paragraph("<b>Lessons Learned:</b>", styles['Label'])], [Paragraph(get_val(incident.lessons_learned), styles['Value'])],
            [Paragraph("<b>Final Closure Remarks:</b>", styles['Label'])], [Paragraph(get_val(incident.closure_remarks), styles['Value'])],
        ]
        
        closure_remarks_table = Table(closure_remarks_data, colWidths=[drawable_width])
        closure_remarks_table.setStyle(TableStyle([
            ('GRID', (0,0),(-1,-1),1,border_color), ('VALIGN',(0,0),(-1,-1),'TOP'), ('LEFTPADDING', (0,0),(-1,-1),6), ('TOPPADDING', (0,0),(-1,-1),4), ('BOTTOMPADDING', (0,0),(-1,-1),4),
            ('BACKGROUND', (0, 0), (0, 0), header_bg_color), ('BACKGROUND', (0, 2), (0, 2), header_bg_color), ('BACKGROUND', (0, 4), (0, 4), header_bg_color)
        ]))
        story.append(closure_remarks_table)


    # ========================================================
    # Reporting & Administrative Information
    # ========================================================
    story.append(PageBreak())
    story.append(Paragraph("<b>SECTION 6: ADMINISTRATIVE DETAILS</b>", styles['SectionHeader']))
    reporting_data = [
        [Paragraph('<b>Current Status:</b>', styles['Label']), Paragraph(incident.get_status_display(), styles['Value'])],
        [Paragraph('<b>Reported By:</b>', styles['Label']), Paragraph(incident.reported_by.get_full_name(), styles['Value'])],
        [Paragraph('<b>Reported Date:</b>', styles['Label']), Paragraph(incident.reported_date.strftime('%d/%m/%Y %H:%M'), styles['Value'])],
        [Paragraph('<b>Last Updated:</b>', styles['Label']), Paragraph(incident.updated_at.strftime('%d/%m/%Y %H:%M'), styles['Value'])],
        [Paragraph('<b>Investigation Required:</b>', styles['Label']), Paragraph('Yes' if incident.investigation_required else 'No', styles['Value'])],
        [Paragraph('<b>Investigation Deadline:</b>', styles['Label']), Paragraph(incident.investigation_deadline.strftime('%d/%m/%Y') if incident.investigation_deadline else 'N/A', styles['Value'])],
        [Paragraph('<b>Investigation Completed On:</b>', styles['Label']), Paragraph(incident.investigation_completed_date.strftime('%d/%m/%Y') if incident.investigation_completed_date else 'Pending', styles['Value'])],
    ]
    reporting_table = Table(reporting_data, colWidths=[drawable_width * 0.25, drawable_width * 0.75])
    reporting_table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 1, border_color), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    story.append(reporting_table)

    story.append(Spacer(1, 10*mm))
    
    footer_text = f"Document generated from EHS-360 System on {datetime.datetime.now().strftime('%d-%b-%Y at %H:%M hrs')}"
    story.append(Paragraph(footer_text, styles['FooterText']))
    
    # ========================================
    # Build the PDF
    # ========================================
    doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=NumberedCanvas)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Injury_Report_{incident.report_number}.pdf"'
    response.write(pdf)
    
    
    return response

#Displaying incident based on the user's role
def get_incidents_for_user(user):
    if user.is_superuser:
        return Incident.objects.all()

    role_name = user.role.name.upper()

    if role_name == 'ADMIN':
        return Incident.objects.all()

    if role_name == 'PLANT HEAD':
        plants = user.get_all_plants()
        return Incident.objects.filter(plant__in=plants)

    if role_name == 'LOCATION HEAD':
        locations = user.get_all_locations()
        return Incident.objects.filter(location__in=locations)

    return Incident.objects.filter(reported_by=user)