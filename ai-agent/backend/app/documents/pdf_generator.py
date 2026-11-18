"""ATS-Optimized PDF Resume Generator powered by ReportLab."""

from pathlib import Path
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from app.core.exceptions import JobAgentException


class ATSPdfGenerator:
    """Generates clean, single-column, ATS-parseable PDF resumes."""

    @classmethod
    def generate_pdf(
        cls,
        resume_data: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Renders structured resume data into an ATS-compliant PDF document.
        Ensures output directory exists and returns absolute file path.
        """
        try:
            target_file = Path(output_path).resolve()
            target_file.parent.mkdir(parents=True, exist_ok=True)

            doc = SimpleDocTemplate(
                str(target_file),
                pagesize=letter,
                leftMargin=0.5 * inch,
                rightMargin=0.5 * inch,
                topMargin=0.5 * inch,
                bottomMargin=0.5 * inch
            )

            styles = getSampleStyleSheet()

            # Custom ATS Styles
            name_style = ParagraphStyle(
                "ATSName",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                alignment=1,  # Centered
                textColor=colors.HexColor("#111827")
            )

            contact_style = ParagraphStyle(
                "ATSContact",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9.5,
                leading=13,
                alignment=1,  # Centered
                textColor=colors.HexColor("#4B5563")
            )

            heading_style = ParagraphStyle(
                "ATSSectionHeading",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=11.5,
                leading=15,
                textColor=colors.HexColor("#1F2937"),
                spaceBefore=8,
                spaceAfter=3,
                keepWithNext=True
            )

            body_style = ParagraphStyle(
                "ATSBody",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9.5,
                leading=13,
                textColor=colors.HexColor("#374151")
            )

            job_title_style = ParagraphStyle(
                "ATSJobTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#111827")
            )

            job_meta_style = ParagraphStyle(
                "ATSJobMeta",
                parent=styles["Normal"],
                fontName="Helvetica-Oblique",
                fontSize=9,
                leading=12,
                textColor=colors.HexColor("#4B5563")
            )

            bullet_style = ParagraphStyle(
                "ATSBullet",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=12.5,
                leftIndent=14,
                firstLineIndent=-10,
                textColor=colors.HexColor("#374151"),
                spaceAfter=2
            )

            story = []

            # 1. Candidate Name & Contact Info
            contact = resume_data.get("contact_info", {})
            full_name = contact.get("name") or resume_data.get("full_name") or "Candidate Name"
            story.append(Paragraph(full_name, name_style))
            story.append(Spacer(1, 3))

            contact_parts = []
            if contact.get("email"):
                contact_parts.append(contact["email"])
            if contact.get("phone"):
                contact_parts.append(contact["phone"])
            if contact.get("location"):
                contact_parts.append(contact["location"])
            elif contact.get("location_city") or contact.get("location_country"):
                loc = ", ".join(filter(None, [
                    contact.get("location_city"),
                    contact.get("location_country")
                ]))
                contact_parts.append(loc)
            if contact.get("linkedin_url"):
                contact_parts.append(contact["linkedin_url"])
            if contact.get("github_url"):
                contact_parts.append(contact["github_url"])

            if contact_parts:
                story.append(Paragraph(" | ".join(contact_parts), contact_style))
            story.append(Spacer(1, 6))

            def add_section_header(title: str):
                story.append(Paragraph(title.upper(), heading_style))
                story.append(HRFlowable(
                    width="100%",
                    thickness=0.75,
                    color=colors.HexColor("#D1D5DB"),
                    spaceBefore=2,
                    spaceAfter=5
                ))

            # 2. Professional Summary
            summary = resume_data.get("summary")
            if summary:
                add_section_header("Professional Summary")
                story.append(Paragraph(summary, body_style))
                story.append(Spacer(1, 4))

            # 3. Technical Skills
            skills = resume_data.get("skills", [])
            if skills:
                add_section_header("Core Technical Skills")
                if isinstance(skills, list):
                    skills_text = ", ".join(skills)
                else:
                    skills_text = str(skills)
                story.append(Paragraph(skills_text, body_style))
                story.append(Spacer(1, 4))

            # 4. Work Experience
            experiences = resume_data.get("experience", [])
            if experiences:
                add_section_header("Professional Experience")
                for exp in experiences:
                    # Role & Company line
                    title = (
                        exp.get("title")
                        or exp.get("role")
                        or exp.get("header_line")
                        or "Position"
                    )
                    company = exp.get("company", "")
                    dates = (
                        f"{exp.get('start_date', '')} – "
                        f"{exp.get('end_date', 'Present')}"
                        if exp.get("start_date")
                        else ""
                    )
                    location = exp.get("location", "")

                    header_line = f"<b>{title}</b>"
                    if company:
                        header_line += f" | {company}"
                    story.append(Paragraph(header_line, job_title_style))

                    meta_line = " | ".join(filter(None, [dates, location]))
                    if meta_line:
                        story.append(Paragraph(meta_line, job_meta_style))
                    story.append(Spacer(1, 2))

                    bullets = exp.get("bullet_points") or exp.get("bullets") or []
                    for b in bullets:
                        story.append(Paragraph(f"• {b}", bullet_style))
                    story.append(Spacer(1, 4))

            # 5. Education
            education = resume_data.get("education", [])
            if education:
                add_section_header("Education & Credentials")
                for edu in education:
                    deg = edu.get("degree", "Degree")
                    field = edu.get("field_of_study", "")
                    inst = edu.get("institution", "University")
                    year = str(edu.get("graduation_year", ""))

                    deg_line = f"<b>{deg}</b>" + (f" in {field}" if field else "")
                    story.append(Paragraph(deg_line, job_title_style))
                    sub_line = " | ".join(filter(None, [inst, year]))
                    if sub_line:
                        story.append(Paragraph(sub_line, job_meta_style))
                    story.append(Spacer(1, 3))

            # 6. Projects (if present)
            projects = resume_data.get("projects", [])
            if projects:
                add_section_header("Technical Projects")
                for proj in projects:
                    p_title = f"<b>{proj.get('title', 'Project')}</b>"
                    tech = ", ".join(proj.get("technologies", []))
                    if tech:
                        p_title += f" ({tech})"
                    story.append(Paragraph(p_title, job_title_style))
                    p_desc = proj.get("description", "")
                    if p_desc:
                        story.append(Paragraph(p_desc, body_style))
                    story.append(Spacer(1, 3))

            certifications = resume_data.get("certifications", [])
            if certifications:
                add_section_header("Certifications")
                for certification in certifications:
                    name = (
                        certification.get("name")
                        if isinstance(certification, dict)
                        else str(certification)
                    )
                    story.append(Paragraph(f"• {name}", bullet_style))

            # Build PDF
            doc.build(story)
            return str(target_file)

        except Exception as e:
            raise JobAgentException(f"Failed to generate ATS PDF resume: {str(e)}")
