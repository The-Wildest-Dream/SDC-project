# PostgreSQL Persistence

The application reads `DATABASE_URL` from the runtime environment. It does not print the connection URL, password, or raw database exceptions. SQL logging is disabled and SQLAlchemy hides query parameters. The connection explicitly uses SQLAlchemy's `postgresql+psycopg` dialect (psycopg 3).

The application uses Python and Streamlit. The Drizzle schema in the repository template is not the business schema.

## Development Commands

```bash
python db_manage.py check
python db_manage.py init
python db_manage.py seed
python db_manage.py counts
python verify_database.py
python -m unittest discover -s tests -v
sh start.sh
```

- `check` runs `SELECT 1` and returns a safe status without exposing credentials.
- `init` is a manual development-only command. It creates missing tables; it does not clear or recreate existing tables or migrate changed columns. Schema changes require a separately managed migration. Application startup does not run DDL.
- `seed` validates the fixed-seed synthetic data and inserts only missing IDs in a transaction. Repeating it does not overwrite existing data or add duplicate orders; it does not delete or replace quote and approval records.
- `counts` reads the counts of the four base data sets.
- `verify_database.py` is a development database check for idempotent import, transaction rollback, and database-unavailable behavior. It may create import-operation log entries.
- The unit test command runs pure logic tests.

In Replit, inspect tables through **Tools → Database → Development Database → My Data**. Business tables use the `public` schema. Never paste `DATABASE_URL` into this document, logs, or chat.

The database is shared by the application. There is no user login or real authorization. Demo-role values are not verified identities.

## Tables and Relationships

| Table | Primary key and relationships |
|---|---|
| `products` | Product ID; product costs, unit, currency, and update date |
| `customers` | Customer ID; name and cooperation date |
| `transactions` | Order ID; customer and product foreign keys; historical price/cost/unit/currency snapshots; actual payment date may be NULL |
| `inventory` | Product ID is both primary key and product foreign key; one inventory row per product |
| `inquiries` | Inquiry ID; customer and product foreign keys; quantity, unit, currency, lifecycle status |
| `inquiry_details` | Inquiry ID; one-to-one inquiry extension containing delivery date, validity date, and JSONB snapshot |
| `quote_workflows` | Quote ID; inquiry foreign key; unique inquiry/version pair, demo owner, state, and JSONB payload snapshot |
| `quote_versions` | Quote ID; inquiry foreign key; immutable submitted price, cost, margin, and cost snapshot |
| `approval_records` | Approval record ID; quote-version foreign key; actor, decision, comment, timestamp |
| `operation_logs` | Log ID; action, simulated actor, JSONB summary, timestamp |
| `payment_ledger` | Payment record ID; transaction/order foreign key, payment date, and amount; schema/service code exists, but a complete integrated partial-payment workflow is not yet available |

Customers and products can each relate to many transactions and inquiries. An inquiry can have multiple quote versions; each quote version can have multiple approval records. Foreign keys prevent deleting referenced data through implicit cascading. Database constraints enforce non-negative amounts, positive transaction quantities, inventory limits, valid dates, and unique quote versions.

Operation logs do not contain connection information or complete CSV payloads. Business writes and related log records are intended to commit in the same transaction.

## CSV Import Semantics

Imports merge by ID rather than replacing entire tables. New IDs are inserted, matching IDs updated, omitted rows retained, and no bulk-delete action is provided. The import validates headers and records, acquires a transaction-scoped import lock, reads current data, validates merged foreign keys and product unit/currency consistency, and then writes the batch. Validation or database failure rolls back the batch. Success feedback appears only after commit.

Order ID is the database primary key, so repeating the same synthetic seed import does not create duplicate orders. Demo seeding skips matching IDs instead of updating them.

Persisted business data is not stored in Streamlit `session_state`, written to temporary files, or silently restored from sample files. Page reads come from PostgreSQL. Session state is used for page controls, unsubmitted input, and UI feedback. A database failure is reported rather than silently replaced with sample data.
