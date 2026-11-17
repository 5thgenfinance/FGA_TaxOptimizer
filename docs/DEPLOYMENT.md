# Deployment guide - version 1.0.0

This guide covers releasing FGA Tax Optimizer 1.0.0 to Streamlit Community Cloud. It supplements PROJECT_PLAN.md, which is the design record. Where the two differ on release status, this file is newer.

## 1. Release status
- Version 1.0.0 is committed on branch `test` (app/version.py, pyproject.toml and CHANGELOG.md agree).
- Owner sign-off: manual checks in PROJECT_PLAN.md section 8 passed on 2026-11-17.
- `main` is not changed until the owner merges. On a private repository on the free GitHub plan, branch protection is not enforced, so this is a convention.
- PROJECT_PLAN.md still shows 0.5.0 in its header and status table. Update it when the plan is next edited; this guide is the release record until then.

## 2. Before the merge
1. Run `python -m pytest -q` on the `test` branch in a Python 3.12 environment. All tests must pass.
2. Run `python scripts/validate_tables.py`.
3. Start the app (`streamlit run streamlit_app.py`) and confirm the footer and the Status tab show Version 1.0.0.
4. Enter the golden case with legacy mode on and confirm total tax $22,559 and amount due $6,059 (PROJECT_PLAN.md section 8).
5. Upload each cross-check scenario and compare the displayed results with its expected results.
6. Confirm the 'Download Excel Version' button downloads `TaxRetirementOptimizer.xlsx`.

## 3. Merge and tag
1. Open a pull request from `test` to `main` and review the changed files.
2. Merge it (owner only).
3. Tag the merge commit `v1.0.0` and, if wanted, create a GitHub release from the CHANGELOG 1.0.0 entry.

## 4. Streamlit Community Cloud settings
- Repository: `5thgenfinance/FGA_TaxOptimizer`. Branch: `main`. Main file path: `streamlit_app.py`.
- Python version: 3.12.
- Dependencies come from `requirements.txt` (pydantic, streamlit, reportlab, openpyxl).
- Push to `main` redeploys. Use 'Reload tables' in the sidebar if the app is already running after a table change.
- A private repository can back a private app. Each account has a limited number of private apps; check that the slot is free (PROJECT_PLAN.md section 11, item 7).

## 5. Access control (decide before real client data)
The app has no sign-in of its own. The hosted app handles client data in the forms, the exported JSON and the PDF report, so decide on access control before first real use (PROJECT_PLAN.md section 11, item 3).

| Option | What it gives | Effort |
|---|---|---|
| Restrict viewers in app settings (Sharing: only specific people) | Named email addresses only; no code change | Minutes |
| Shared password from `st.secrets`, checked at the top of `streamlit_app.py` | One password for everyone; cannot tell users apart | Small code change |
| Built-in sign-in (`st.login`, OpenID Connect) | Per-user identity; can limit to listed emails | Provider setup plus code |

Rules for any option:
- Store passwords and client secrets only in the Community Cloud Secrets settings. Never commit a `secrets.toml` file.
- Keep the app private until access control is in place.
- Exported JSON and PDF files contain client data; store and send them securely.

## 6. After deployment
1. Open the hosted app and check the footer version, the Status tab (no validation errors, supported years 2026 and 2027) and one calculation.
2. Confirm the app is private and that the viewer list or password works from a signed-out browser.
3. Record the app URL in the README.

## 7. Rollback
- Revert the merge commit on `main` (or redeploy the previous commit). Community Cloud redeploys on push.
- Scenario files are exported by users, so a rollback does not lose saved work.

## 8. Known limits in 1.0.0
- Filing status Separate is not supported for ordinary tax, long-term gains or the standard deduction.
- No tax-exempt interest input; Social Security provisional income uses the listed inputs only.
- The 2027 SALT cap (40,804; 20,402 separate) is derived from the statute's 1% step, not read from an IRS document. Verify it before relying on 2027 AMT results.
- State tax, IRMAA and ACA subsidy cliffs are not modeled. The What-if tab does not model them either.
- The senior deduction is folded into the standard deduction, as in the workbook. Results are the same for standard-deduction filers.
- The results are planning estimates, not tax return preparation.

## 9. Annual maintenance
See PROJECT_PLAN.md section 10. Each new tax year is a MINOR release (for example 1.1.0).
