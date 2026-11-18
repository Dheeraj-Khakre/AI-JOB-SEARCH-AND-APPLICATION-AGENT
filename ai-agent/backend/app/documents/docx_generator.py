"""ATS-Optimized DOCX Resume Generator powered by python-docx."""

from pathlib import Path
from typing import Any, Dict

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from app.core.exceptions import JobAgentException


class ATSDocxGenerator:
    """Generates clean, ATS-compliant Microsoft Word (.docx) resumes."""

    @classmethod
    def generate_docx(
        cls,
        resume_data: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Renders structured resume data into an ATS-friendly .docx document.
        Returns the absolute file path.
        """
        try:
            target_file = Path(output_path).resolve()
            target_file.parent.mkdir(parents=True, exist_ok=True)

            doc = Document()

            # Set 0.5-inch margins
            for section in doc.sections:
                section.top_margin = Inches(0.5)
                section.bottom_margin = Inches(0.5)
                section.left_margin = Inches(0.5)
                section.right_margin = Inches(0.5)

            # 1. Candidate Name
            contact = resume_data.get("contact_info", {})
            full_name = contact.get("name") or resume_data.get("full_name") or "Candidate Name"

            p_name = doc.add_paragraph()
            p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_name = p_name.add_run(full_name)
            run_name.font.name = "Arial"
            run_name.font.size = Pt(20)
            run_name.font.bold = True
            run_name.font.color.rgb = RGBColor(17, 24, 39)
            p_name.paragraph_format.space_after = Pt(2)

            # Contact Line
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
                p_contact = doc.add_paragraph()
                p_contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_contact = p_contact.add_run(" | ".join(contact_parts))
                run_contact.font.name = "Arial"
                run_contact.font.size = Pt(9.5)
                run_contact.font.color.rgb = RGBColor(75, 85, 99)
                p_contact.paragraph_format.space_after = Pt(10)

            def add_section_header(title: str):
                h = doc.add_heading(level=2)
                run_h = h.add_run(title.upper())
                run_h.font.name = "Arial"
                run_h.font.size = Pt(12)
                run_h.font.bold = True
                run_h.font.color.rgb = RGBColor(31, 41, 55)
                h.paragraph_format.space_before = Pt(8)
                h.paragraph_format.space_after = Pt(4)

            # 2. Summary
            summary = resume_data.get("summary")
            if summary:
                add_section_header("Professional Summary")
                p_sum = doc.add_paragraph()
                r_sum = p_sum.add_run(summary)
                r_sum.font.name = "Arial"
                r_sum.font.size = Pt(10)
                p_sum.paragraph_format.space_after = Pt(6)

            # 3. Skills
            skills = resume_data.get("skills", [])
            if skills:
                add_section_header("Technical Skills")
                p_sk = doc.add_paragraph()
                skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
                r_sk = p_sk.add_run(skills_str)
                r_sk.font.name = "Arial"
                r_sk.font.size = Pt(10)
                p_sk.paragraph_format.space_after = Pt(6)

            # 4. Experience
            experiences = resume_data.get("experience", [])
            if experiences:
                add_section_header("Professional Experience")
                for exp in experiences:
                    p_role = doc.add_paragraph()
                    title = (
                        exp.get("title")
                        or exp.get("role")
                        or exp.get("header_line")
                        or "Position"
                    )
                    company = exp.get("company", "")
                    r_title = p_role.add_run(title)
                    r_title.bold = True
                    r_title.font.name = "Arial"
                    r_title.font.size = Pt(10.5)

                    if company:
                        r_comp = p_role.add_run(f" | {company}")
                        r_comp.font.name = "Arial"
                        r_comp.font.size = Pt(10.5)

                    dates = (
                        f"{exp.get('start_date', '')} – "
                        f"{exp.get('end_date', 'Present')}"
                        if exp.get("start_date")
                        else ""
                    )
                    if dates:
                        r_dates = p_role.add_run(f" ({dates})")
                        r_dates.italic = True
                        r_dates.font.name = "Arial"
                        r_dates.font.size = Pt(9.5)
                    p_role.paragraph_format.space_after = Pt(2)

                    bullets = exp.get("bullet_points") or exp.get("bullets") or []
                    for b in bullets:
                        bp = doc.add_paragraph(style="List Bullet")
                        rb = bp.add_run(b)
                        rb.font.name = "Arial"
                        rb.font.size = Pt(9.5)
                        bp.paragraph_format.space_after = Pt(2)

            # 5. Education
            education = resume_data.get("education", [])
            if education:
                add_section_header("Education & Credentials")
                for edu in education:
                    p_edu = doc.add_paragraph()
                    deg = edu.get("degree", "Degree")
                    field = edu.get("field_of_study", "")
                    r_deg = p_edu.add_run(deg + (f" in {field}" if field else ""))
                    r_deg.bold = True
                    r_deg.font.name = "Arial"
                    r_deg.font.size = Pt(10)

                    inst = edu.get("institution", "University")
                    year = str(edu.get("graduation_year", ""))
                    if inst or year:
                        r_inst = p_edu.add_run(f" | {inst} ({year})")
                        r_inst.font.name = "Arial"
                        r_inst.font.size = Pt(9.5)
                    p_edu.paragraph_format.space_after = Pt(4)

            certifications = resume_data.get("certifications", [])
            if certifications:
                add_section_header("Certifications")
                for certification in certifications:
                    name = (
                        certification.get("name")
                        if isinstance(certification, dict)
                        else str(certification)
                    )
                    p_cert = doc.add_paragraph(style="List Bullet")
                    p_cert.add_run(name)

            projects = resume_data.get("projects", [])
            if projects:
                add_section_header("Technical Projects")
                for project in projects:
                    title = project.get("title", "Project")
                    p_project = doc.add_paragraph()
                    p_project.add_run(title).bold = True
                    description = project.get("description")
                    if description:
                        p_project.add_run(f" — {description}")

            # Save DOCX
            doc.save(str(target_file))
            return str(target_file)

        except Exception as e:
            raise JobAgentException(f"Failed to generate ATS DOCX resume: {str(e)}")
