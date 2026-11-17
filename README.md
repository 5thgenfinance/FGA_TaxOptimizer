# FGA Tax Optimizer

Fifth Generation Advisers' federal tax and retirement estimator, a Streamlit web app converted from the `TaxRetirementOptimizer.xlsx` workbook. Current version: **0.5.0** (see `CHANGELOG.md`).

It estimates one year's federal income tax: required minimum distribution, taxable Social Security, AGI, standard or itemized deduction, ordinary and capital-gains tax, net investment income tax, alternative minimum tax, and the amount due or refunded. It is a planning estimate, not tax, legal or investment advice.

## Documents
| Document | For |
|---|---|
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Advisers using the app: entering inputs, importing an Excel template or JSON, reading results, PDF report |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Developers: code layout, data flow, how to add an input or a tax year, testing, releases |
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | The specification and project plan: scope, tables, calculation order, known defects, open questions |
| [TaxRetirementOptimizer-Specification.md](TaxRetirementOptimizer-Specification.md) | As-built specification of the Excel workbook the app was converted from |
| [CHANGELOG.md](CHANGELOG.md) | What changed in each version |

## Run it locally
```
python -m venv .venv
.venv/Scripts/activate            # Windows PowerShell; on macOS/Linux: source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python -m streamlit run streamlit_app.py
```
The project targets Python 3.11 or newer (Streamlit Community Cloud is set to 3.12).

## Branches
`main` is what Streamlit Community Cloud deploys. Work happens on `test` and reaches `main` through a pull request that the owner merges.
