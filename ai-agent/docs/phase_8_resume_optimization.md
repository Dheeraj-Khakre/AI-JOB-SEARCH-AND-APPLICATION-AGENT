# Phase 8: Resume Optimization

Phase 8 provides the Agent 5 deterministic resume-tailoring workflow. It uses
the candidate master profile and analyzed JD to reorder verified skills,
preserve verified experience bullets, and render ATS-compatible PDF/DOCX
resume versions.

## Ground-truth rules

The optimizer treats `candidate_profiles.verified_*` facts as primary authority.
Parsed resume sections are used only as a fallback when no verified section
exists. It never invents employers, dates, credentials, technologies, projects,
or numerical impact metrics.

Tailoring applies the Google XYZ presentation principle where existing
candidate facts already support accomplishment, measurement, and action
language. Existing bullets are preserved rather than rewritten, because
rewriting would risk unsupported claims.

Before a version is saved, the grounding verifier checks:

- Every output skill exists in the verified skill or technology set.
- Every experience bullet is present in master-fact text.
- Experience role, employer, and dates exist in verified employment facts.
- Education and project credentials exist in verified profile facts.
- Every numeric metric appears in the master-fact text.

Unsupported output raises `HallucinationDetectedError` and prevents document
or database version creation.

## API

`POST /api/v1/resumes/optimize`

```json
{
  "resume_id": "resume UUID",
  "job_id": "job UUID",
  "version_label": "Target Company - Target Role"
}
```

The response includes the ATS coverage score, grounding report, tailored JSON,
tailored text, and generated PDF/DOCX paths. The existing
`POST /api/v1/resumes/versions/` endpoint also verifies user-provided tailoring
instead of trusting `grounding_verified=true`.

The LangGraph `optimize` workflow mode requires `resume_id` and
`selected_job_id`. It creates a resume version and PDF/DOCX files, then either
finishes or pauses for the existing human-review gate.
