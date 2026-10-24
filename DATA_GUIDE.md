# Synthetic Data Guide

All generated records are synthetic and do not represent real companies or customers. Valid business data is stored in PostgreSQL and read from the database after page navigation or an application restart. See [DATABASE_GUIDE.md](DATABASE_GUIDE.md) for initialization and persistence behavior.

## Reproducible Generation

Run `python generate_data.py` from the project root. It writes four UTF-8-with-BOM CSV example files to `sample_data/`. Re-running the generator replaces those sample files only; it does not modify imported database records.

Run `python generate_myr_data.py` to create a separate MYR bundle:
`sample_data/MYR_模拟数据_产品.csv`, `MYR_模拟数据_客户.csv`,
`MYR_模拟数据_历史交易.csv`, and `MYR_模拟数据_库存.csv`.
It uses seed `20261024`, fixed reference date `2026-10-23`, four separate
`P_MY_*` products, six separate `C_MY_*` customers, and 80 transactions per
product (320 total). Costs are independently specified in MYR; each synthetic
unit cost varies from 85% to 115% of its MYR material/labor/overhead total,
and the synthetic transaction price is drawn from an independent MYR gross
margin range of 12%–32%, with small random variation. These are fictional
Malaysian manufacturing scenarios, not verified market prices or converted
CNY amounts. Generation validates references and only writes the four review
CSVs; it does not connect to or import into the database.

The random seed is `20261023`; the fixed reference date is `2026-10-23`. The generator does not use the system date.

- Six synthetic manufacturing products; material cost ranges from 10 to 80, labor from 3 to 20, and manufacturing overhead from 2 to 10, rounded to two decimal places.
- Twelve synthetic customers, with a cooperation start date of 2024-01-01. The last customer has only three assigned transactions to demonstrate a small sample.
- 300 transaction records dated from 2025-10-24 through 2026-10-23, with quantities from 10 to 500.
- Historical unit cost is 85%–115% of the product's material, labor, and overhead sum. Transaction price is generated from a synthetic gross margin between 10% and 35%.
- Contract terms are randomly selected from 15, 30, 45, and 60 days. Candidate payment dates are 5 days early, on time, or 3, 10, 30, or 60 days late. Approximately 18% are randomly marked unpaid; candidates after the reference date are also stored as unpaid, so the final unpaid share can be higher.
- Inventory on hand ranges from 100 to 2,000; reserved quantity is between zero and on-hand quantity.
- Currency defaults to CNY. Units are either pieces (`件`) or kilograms (`千克`). Random generation uses a local fixed seed.

## CSV Format and Validation

Download examples from Data Center and preserve the Chinese machine-readable headers. Historical transaction CSVs also require `单位` and `币种` snapshot columns. These CSV contracts are intentionally not translated.

Supported currencies include CNY, USD, EUR, and MYR; values are not converted between currencies. A transaction's unit and currency must match its referenced product. All fields are required except `实际付款日期`. Dates use `YYYY-MM-DD`.

Primary keys are product ID, customer ID, and order ID; inventory is unique by product ID. Numeric values must be finite. Prices and costs must be non-negative, transaction quantity must be positive, and inventory quantities may be zero. Validation checks foreign-key references, date ordering, reserved quantity limits, and consistency of referenced product currency and unit.

Data Center merges rows by ID: new IDs are inserted, matching IDs updated, and omitted rows retained. Multiple CSV types can be imported together. The user must confirm the files contain team-generated synthetic data. The entire batch is validated and saved in a database transaction; an error prevents the whole batch from being applied. Errors include type, row, field, and reason. CSV row numbers are physical file lines (header is line 1); cross-table errors may identify the existing table and record index.

The data-center import permits decimal transaction quantities; the inquiry interface permits positive decimal quantities as well.

## Shared Data Access

- `shared_data.get_data()` reads current valid data from PostgreSQL; it does not use a session-scoped business-data cache.
- `shared_data.import_data()` validates and merges a batch transactionally.
- `data_service.comparable_transactions()` compares only the same product ID, currency, and unit.
- Inquiry cost fields are prefilled from the selected product and may be adjusted for that inquiry.
- The historical-price page only shows transactions matching product, currency, and unit.
- `train_price_model.py` reads the fixed-seed CNY generator and the separate MYR CSV files. The two currencies and product/unit groups remain separate; uploading CSV data never retrains the model.
- `data_service.py` and `generate_data.py` can be used independently of Streamlit.

## Legacy Customer Payment Summary

The current summary uses the synthetic historical transaction's whole-order `实际付款日期`; it does not yet provide a complete partial-payment UI.

For a selected analysis date at end of day, transactions dated after the cutoff are excluded. Orders are due when the agreed payment date is on or before the cutoff. The on-time rate counts orders paid by the cutoff on or before the agreed due date divided by due orders; unpaid due orders remain in the denominator. When there are no due orders, the rate is unavailable. Current overdue unpaid means the agreed due date is before the cutoff and the order is unpaid or was paid after the cutoff. Historical overdue days are accumulated only for orders paid by the cutoff and are floored at zero. Unpaid overdue days are shown separately.

Fewer than 10 due transactions triggers a small-sample warning. This is a demonstration threshold, not evidence that 10 observations are statistically reliable. Payment history is not an integrity rating and does not automatically set credit limits, payment terms, or delivery-before-payment decisions.

## Verification

Run `python -m unittest discover -s tests -v` for the repository's unit suite. Database-backed CSV behavior requires the development database configured as described in [DATABASE_GUIDE.md](DATABASE_GUIDE.md).
