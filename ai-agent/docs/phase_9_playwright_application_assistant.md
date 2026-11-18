# Phase 9: Playwright Application Assistant

Phase 9 adds isolated browser preparation and a cryptographic Human-in-the-Loop
submission boundary. It does not silently submit applications.

## Browser isolation

`BrowserAutomationManager` creates a separate application-profile directory,
launches Chromium in its own context, verifies that no CAPTCHA or anti-bot
challenge is visible, and closes the browser/context after preparation.

The application assistant validates:

- First name, last name, and email are present.
- The selected PDF or DOCX file exists.
- The resume version is grounded.
- The resume version belongs to the selected job.
- The target URL is HTTP or HTTPS.

## Approval lifecycle

Approvals are stored in `<DATA_DIR>/db/application_approvals.sqlite3`:

1. `prepare` creates a pending request containing a hash of the full preview.
2. `approve` creates a `hitl_*` token with a configured expiration.
3. `submit` verifies the preview, token, expiration, and approval record.
4. The token is consumed exactly once immediately before the final-submit
   boundary.
5. If no submit control exists or CAPTCHA is detected, no click is executed.

Changing any approved field invalidates the token.

## API

- `POST /api/v1/applications/prepare`
- `POST /api/v1/applications/{approval_id}/approve`
- `POST /api/v1/applications/{approval_id}/submit`

The submit endpoint currently stops at the final submit control and never calls
`click()`. Portal-specific implementations must retain the approval verification
and exact-once consumption behavior before enabling a final click.
