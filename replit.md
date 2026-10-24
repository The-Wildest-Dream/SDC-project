# SME Manufacturing Quotation Assistant

This is a Python + Streamlit competition demo using synthetic data. It uses SQLAlchemy, psycopg 3, and PostgreSQL. The historical transaction-price model is trained offline; the app does not train it at startup.

Run the app with `sh start.sh`. See `DATABASE_GUIDE.md` for database operations. The repository contains pnpm/Drizzle template components, but the quotation business schema is defined in Python; do not push the empty template schema over the application tables.

## Runtime

- Main application: Streamlit, `app.py`, launched by `start.sh`.
- Required runtime environment variable: `DATABASE_URL`.
- Python database access: SQLAlchemy with the `postgresql+psycopg` driver.
- Model training: `python train_price_model.py`; this is an explicit offline command.
- Development database commands: `python db_manage.py check|init|seed|counts`.

## Source Map

- `*_page.py`: Streamlit page modules.
- `data_service.py`, `quotation_rules.py`, `finance_rules.py`: validation and business calculations.
- `database.py`, `db_schema.py`, `workflow_service.py`: persistence and quote workflow.
- `models/historical_price/`: generated model/evaluation artifacts.
- `locales/`: static UI translations. Keep machine fields, internal state codes, and user-entered text unchanged.
- `DATA_GUIDE.md`, `DATABASE_GUIDE.md`, `MODEL_GUIDE.md`, `QUOTATION_GUIDE.md`, `WORKFLOW_GUIDE.md`: maintained technical guides.

## Product Constraints

- All demo data and selectable roles are synthetic; the role switch is not authentication.
- Price/cost decisions and approval must remain human-reviewed; stock/payment summaries are advisory.
- Preserve database field names and imported CSV headers.
- Never log or document database credentials. Do not use the unused template database tooling for Python business tables.
