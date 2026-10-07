import json
import os
from io import BytesIO

from flask import send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from werkzeug.utils import secure_filename


def _safe_pdf_name(filename: str) -> str:
    safe = secure_filename(filename or 'retinascan_report')
    if not safe:
        safe = 'retinascan_report'
    return safe


def generate_screening_pdf(
    output_dir: str,
    filename: str,
    predicted_class: str,
    confidence: float,
    probabilities,
    risk_result: dict,
    age,
    blood_sugar,
    blood_pressure,
    language: str,
    original_image_path: str,
    gradcam_image_path: str = None,
) -> str:
    """Create a professional PDF report for a screening result."""
    os.makedirs(output_dir, exist_ok=True)

    safe_name = _safe_pdf_name(filename)
    base_name = os.path.splitext(safe_name)[0]
    pdf_path = os.path.join(output_dir, f"{base_name}_screening_report.pdf")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TitleStyle',
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1f3c88'),
        spaceAfter=14,
    )
    heading_style = ParagraphStyle(
        name='HeadingStyle',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        textColor=colors.HexColor('#1f3c88'),
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        name='BodyStyle',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )

    story = []
    story.append(Paragraph('RETINASCAN', title_style))
    story.append(Paragraph('AI-Assisted Diabetic Retinopathy Screening', styles['Heading2']))
    story.append(Spacer(1, 0.2 * inch))

    patient_info = [
        ['Patient Information', ''],
        ['Age', str(age) if age else 'Not provided'],
        ['Blood Sugar (mg/dL)', str(blood_sugar) if blood_sugar else 'Not provided'],
        ['Blood Pressure (mmHg)', str(blood_pressure) if blood_pressure else 'Not provided'],
        ['Voice Language', language.upper() if language else 'EN'],
    ]
    patient_table = Table(patient_info, colWidths=[2.3 * inch, 3.4 * inch])
    patient_table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9f1ff')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
    )
    story.append(patient_table)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph('AI Screening Result', heading_style))
    story.append(Paragraph(f'Detected DR stage: {predicted_class}', body_style))
    story.append(Paragraph(f'Confidence: {float(confidence) * 100:.2f}%', body_style))

    prob_rows = [['Class', 'Probability']]
    for idx, name in enumerate(['Mild', 'Moderate', 'No_DR', 'Proliferate_DR', 'Severe']):
        value = float(probabilities[idx]) if idx < len(probabilities) else 0.0
        prob_rows.append([name, f'{value * 100:.2f}%'])
    probs_table = Table(prob_rows, colWidths=[2.5 * inch, 2.5 * inch])
    probs_table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef9ee')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ])
    )
    story.append(probs_table)
    story.append(Spacer(1, 0.3 * inch))

    risk_level = risk_result.get('risk_level', 'Low') if risk_result else 'Low'
    risk_score = risk_result.get('risk_score', 0) if risk_result else 0
    factors = risk_result.get('factors', []) if risk_result else []
    explanation = risk_result.get('explanation', '') if risk_result else ''
    recommendation = risk_result.get('recommendation', 'Continue routine eye-care follow-up and consult an eye-care professional if you have concerns.') if risk_result else 'Continue routine eye-care follow-up and consult an eye-care professional if you have concerns.'

    story.append(Paragraph('Risk Indication', heading_style))
    story.append(Paragraph(f'Risk Level: {risk_level}', body_style))
    story.append(Paragraph(f'Project-defined risk score: {risk_score}', body_style))
    for factor in factors:
        story.append(Paragraph(f'- {factor}', body_style))
    story.append(Paragraph(f'Explanation: {explanation}', body_style))
    story.append(Paragraph(f'Recommendation: {recommendation}', body_style))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph('Images', heading_style))
    if original_image_path and os.path.exists(original_image_path):
        original_img = Image(original_image_path, width=2.8 * inch, height=2.8 * inch)
        story.append(original_img)
        story.append(Paragraph('Original retinal image', body_style))
    if gradcam_image_path and os.path.exists(gradcam_image_path):
        grad_img = Image(gradcam_image_path, width=2.8 * inch, height=2.8 * inch)
        story.append(Spacer(1, 0.1 * inch))
        story.append(grad_img)
        story.append(Paragraph('Grad-CAM image', body_style))

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(
        'This is an AI-assisted screening result and a project-defined rule-based risk indication. It is not a final medical diagnosis or a clinically validated risk prediction. Please consult an eye-care professional for confirmation and appropriate follow-up.',
        ParagraphStyle(name='Disclaimer', fontName='Helvetica-Oblique', fontSize=9, leading=12, textColor=colors.HexColor('#555555')),
    ))

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    doc.build(story)
    return pdf_path


__all__ = ['generate_screening_pdf']
