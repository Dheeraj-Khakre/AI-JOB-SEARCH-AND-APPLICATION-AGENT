"""Resume Document Parsers (PDF & DOCX) with Semantic Section Extraction."""

import io
import re
import zipfile
from typing import Any, Dict, List, Optional

from docx import Document
from pypdf import PdfReader

from app.core.exceptions import JobAgentException


class PDFResumeParser:
    """Extracts raw text from PDF documents using pypdf."""

    @staticmethod
    def extract_text(pdf_bytes: bytes) -> str:
        try:
            stream = io.BytesIO(pdf_bytes)
            reader = PdfReader(stream)
            extracted_pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_pages.append(text)
            return "\n".join(extracted_pages).strip()
        except Exception as e:
            raise JobAgentException(f"Failed to parse PDF document: {str(e)}")


class DOCXResumeParser:
    """Extracts raw text and structural paragraphs from DOCX documents using python-docx."""

    @staticmethod
    def extract_text(docx_bytes: bytes) -> str:
        try:
            stream = io.BytesIO(docx_bytes)
            doc = Document(stream)
            lines = []
            for p in doc.paragraphs:
                text = p.text.strip()
                if text:
                    lines.append(text)
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        lines.append(" | ".join(row_text))
            return "\n".join(lines).strip()
        except Exception as e:
            raise JobAgentException(f"Failed to parse DOCX document: {str(e)}")


class ResumeSectionExtractor:
    """Segments raw resume text into semantic resume sections using deterministic heuristics."""

    SECTION_HEADERS = {
        "summary": [
            r"^(professional\s+)?summary",
            r"^executive\s+summary",
            r"^career\s+profile",
            r"^about\s+me",
            r"^objective"
        ],
        "skills": [
            r"^technical\s+skills",
            r"^core\s+competencies",
            r"^skills(\s+&\s+proficiencies)?",
            r"^technologies",
            r"^skills\s+and\s+tools"
        ],
        "experience": [
            r"^work\s+experience",
            r"^professional\s+experience",
            r"^employment\s+history",
            r"^experience",
            r"^work\s+history"
        ],
        "education": [
            r"^education(\s+and\s+qualifications)?",
            r"^academic\s+background",
            r"^academic\s+history"
        ],
        "projects": [
            r"^(featured\s+|key\s+|selected\s+)?projects",
            r"^technical\s+projects",
            r"^open\s+source\s+contributions"
        ],
        "certifications": [
            r"^certifications?",
            r"^licenses?\s+(&|and)\s+certifications?",
            r"^courses\s+(&|and)\s+trainings?"
        ]
    }

    @classmethod
    def extract_sections(cls, text: str) -> Dict[str, Any]:
        """Splits unstructured text into named sections."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        sections: Dict[str, List[str]] = {
            "header": [],
            "summary": [],
            "skills": [],
            "experience": [],
            "education": [],
            "projects": [],
            "certifications": [],
            "other": []
        }

        current_section = "header"

        for line in lines:
            normalized_line = line.lower().strip()
            # Remove trailing colons or punctuation
            normalized_line = re.sub(r"[:\-_]+$", "", normalized_line).strip()

            detected_section = None
            for section_key, patterns in cls.SECTION_HEADERS.items():
                for pat in patterns:
                    if re.match(pat, normalized_line):
                        detected_section = section_key
                        break
                if detected_section:
                    break

            if detected_section:
                current_section = detected_section
                continue

            sections[current_section].append(line)

        # Extract contact information from header lines
        contact_info = cls._extract_contact_info(sections["header"])

        # Extract parsed skills
        parsed_skills = cls._extract_skills(sections["skills"])

        # Parse experience items
        parsed_experience = cls._extract_experience_items(sections["experience"])
        parsed_education = cls._extract_education_items(sections["education"])
        parsed_projects = cls._extract_project_items(sections["projects"])
        parsed_certifications = cls._extract_certification_items(
            sections["certifications"]
        )

        return {
            "contact_info": contact_info,
            "summary": " ".join(sections["summary"]).strip(),
            "skills": parsed_skills,
            "experience": parsed_experience,
            "education": parsed_education,
            "projects": parsed_projects,
            "certifications": parsed_certifications,
            "education_raw": "\n".join(sections["education"]),
            "projects_raw": "\n".join(sections["projects"]),
            "certifications_raw": "\n".join(sections["certifications"]),
            "raw_sections": {k: "\n".join(v) for k, v in sections.items()}
        }

    @staticmethod
    def _extract_contact_info(header_lines: List[str]) -> Dict[str, Optional[str]]:
        header_text = " ".join(header_lines)
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", header_text)
        phone_match = re.search(
            r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            header_text
        )
        linkedin_match = re.search(r"https?://(www\.)?linkedin\.com/in/[\w-]+", header_text)
        github_match = re.search(r"https?://(www\.)?github\.com/[\w-]+", header_text)

        # First line is usually candidate name
        candidate_name = header_lines[0] if header_lines else None

        return {
            "name": candidate_name,
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0) if phone_match else None,
            "linkedin_url": linkedin_match.group(0) if linkedin_match else None,
            "github_url": github_match.group(0) if github_match else None
        }

    @staticmethod
    def _extract_skills(skill_lines: List[str]) -> List[str]:
        raw_skill_text = " ".join(skill_lines)
        skills = []
        # Split labeled groups and then split their values by common delimiters.
        labeled_parts = re.split(r"\n|[,;•|]", raw_skill_text)
        tokens = []
        for part in labeled_parts:
            pieces = re.split(r"^\s*[^:]{1,30}:\s*", part)
            if len(pieces) > 1:
                tokens.extend(re.split(r"\s+|,", pieces[-1]))
            else:
                tokens.extend(re.split(r"\s+|,", part))
        for t in tokens:
            cleaned = re.sub(r"^[-–—*]\s*", "", t).strip()
            cleaned = re.sub(r"[:\[\]()]", "", cleaned).strip()
            # Remove labels like "Languages:", "Frameworks:"
            if cleaned and len(cleaned) < 40 and not cleaned.lower().startswith("proficient in"):
                skills.append(cleaned)
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for s in skills:
            if s.lower() not in seen:
                seen.add(s.lower())
                deduped.append(s)
        return deduped

    @staticmethod
    def _extract_experience_items(exp_lines: List[str]) -> List[Dict[str, Any]]:
        """Groups experience lines into chronological roles and bullets."""
        experiences = []
        current_exp: Optional[Dict[str, Any]] = None

        for line in exp_lines:
            # Check if line looks like a bullet
            is_bullet = bool(re.match(r"^[-•*–—]\s*", line))

            if not is_bullet and (re.search(r"\b(20\d\d|19\d\d)\b", line) or len(line.split()) < 8):
                # Likely a title/company/date line
                if current_exp:
                    experiences.append(current_exp)
                current_exp = {
                    "header_line": line,
                    "bullets": []
                }
            else:
                cleaned_bullet = re.sub(r"^[-•*–—]\s*", "", line).strip()
                if current_exp:
                    current_exp["bullets"].append(cleaned_bullet)
                else:
                    current_exp = {
                        "header_line": "Role",
                        "bullets": [cleaned_bullet]
                    }

        if current_exp:
            experiences.append(current_exp)

        return experiences

    @staticmethod
    def _extract_education_items(education_lines: List[str]) -> List[Dict[str, Any]]:
        education: List[Dict[str, Any]] = []
        for line in education_lines:
            clean = re.sub(r"^[-•*–—]\s*", "", line).strip()
            if not clean:
                continue
            education_match = re.search(
                r"(?P<degree>[^|,]+)"
                r"(?:\s+in\s+|\s*,\s*)(?P<field>[^|,(]+)"
                r"(?:\s+\|\s*(?P<institution>[^|]+))?",
                clean,
                re.IGNORECASE,
            )
            year_match = re.search(r"\b(19|20)\d{2}\b", clean)
            if education_match:
                education.append({
                    "degree": education_match.group("degree").strip(),
                    "field_of_study": education_match.group("field").strip(),
                    "institution": (
                        education_match.group("institution").strip()
                        if education_match.group("institution")
                        else ""
                    ),
                    "graduation_year": int(year_match.group(0)) if year_match else None,
                })
            else:
                education.append({
                    "degree": clean,
                    "field_of_study": "",
                    "institution": "",
                    "graduation_year": int(year_match.group(0)) if year_match else None,
                })
        return education

    @staticmethod
    def _extract_project_items(project_lines: List[str]) -> List[Dict[str, Any]]:
        projects: List[Dict[str, Any]] = []
        current: Optional[Dict[str, Any]] = None
        for line in project_lines:
            clean = re.sub(r"^[-•*–—]\s*", "", line).strip()
            if not clean:
                continue
            is_bullet = bool(re.match(r"^[-•*–—]\s*", line))
            if not is_bullet and len(line.split()) <= 12:
                if current:
                    projects.append(current)
                current = {
                    "title": clean,
                    "description": "",
                    "technologies": [],
                }
            elif current:
                current["description"] = (
                    f"{current['description']} {clean}".strip()
                    if current["description"]
                    else clean
                )
            else:
                projects.append({
                    "title": clean,
                    "description": "",
                    "technologies": [],
                })
        if current:
            projects.append(current)
        return projects

    @staticmethod
    def _extract_certification_items(
        certification_lines: List[str]
    ) -> List[Dict[str, str]]:
        certifications: List[Dict[str, str]] = []
        for line in certification_lines:
            clean = re.sub(r"^[-•*–—]\s*", "", line).strip()
            if clean:
                certifications.append({"name": clean})
        return certifications


class UnifiedResumeParser:
    """Unified entry point for parsing PDF and DOCX resume documents."""

    @classmethod
    def parse_document(cls, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        fn = filename.lower()
        if fn.endswith(".pdf"):
            if not file_bytes.startswith(b"%PDF-"):
                raise JobAgentException("The uploaded PDF file has an invalid PDF signature.")
            raw_text = PDFResumeParser.extract_text(file_bytes)
            file_type = "PDF"
        elif fn.endswith(".docx"):
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as archive:
                    if "[Content_Types].xml" not in archive.namelist():
                        raise JobAgentException(
                            "The uploaded DOCX file is not a valid Office document."
                        )
            except zipfile.BadZipFile as exc:
                raise JobAgentException(
                    "The uploaded DOCX file is not a valid Office document."
                ) from exc
            raw_text = DOCXResumeParser.extract_text(file_bytes)
            file_type = "DOCX"
        else:
            raise JobAgentException(
                f"Unsupported file format '{filename}'. "
                "Only PDF and DOCX are supported."
            )

        if not raw_text:
            raise JobAgentException("The uploaded resume document contains no readable text.")

        structured_sections = ResumeSectionExtractor.extract_sections(raw_text)

        return {
            "file_name": filename,
            "file_type": file_type,
            "raw_text": raw_text,
            "parsed_json": structured_sections
        }
