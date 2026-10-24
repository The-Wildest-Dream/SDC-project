# Demonstration Quote Approval Workflow

All data and roles are for a competition demonstration. Sales A and Sales B map to the simulated Sales role; Manager maps to the simulated Manager role. The selector is not identity authentication or production-grade access control. Backend business functions validate the supplied demo role, ownership, and quote state; this does not make the demo suitable for real authorization or sensitive business.

## Workflow

1. Select Sales A and create/save an inquiry.
2. Open Historical Prices, review available cost and price references, enter a manual quote, and save the quote draft.
3. In Quote Records, the owning sales role can edit its own draft: quantity, delivery date, validity, costs, margin settings, and manual price. A reason is required when changing costs. Submit the saved draft for approval.
4. Switch to Manager. Select the pending version in Approvals, enter a required review comment, and approve or reject.
5. Return to Quote Records. Filter by customer, product, creation date, and state; inspect versions, cost/reference snapshots, comments, and timestamps. Download CSV or printable HTML.
6. The owning sales role can create a new version from an approved/rejected version. The prior version remains unchanged; the new draft must be submitted and approved again. Pending versions cannot be edited.

State changes, approval records, and operation logs are written in one transaction. Row locks protect state transitions. Repeated submission, approval, or creating another revision from a stale version is rejected.

## Saved Snapshots and Exports

Each submitted quote version preserves its saved names, quantity, unit, currency, validity, cost source/input, manual price, reference basis, and available model/prediction details. Inquiry payment-term and validity inputs are stored in the inquiry snapshot and copied into the quote payload. Later master-data updates do not rewrite saved quote versions.

The CSV and HTML exports include quote and inquiry identifiers, version, status, customer, product, quantity, unit, currency, unit price, total, validity, delivery date, payment-term fields when present, and a demo notice. Unapproved versions are marked as draft/not approved. HTML output escapes displayed values; CSV output guards spreadsheet formulas. Export content comes from the selected saved version, not unsaved form values.

## Data and Legacy Compatibility

`quote_workflows` stores owner, state, version, and quote payload; the inquiry/version pair is unique. On submission, `quote_versions` stores the immutable price/cost snapshot. Approval comments and decisions are stored in `approval_records`. The legacy `inquiries.status` represents inquiry lifecycle; the four quote states are stored in `quote_workflows`.

In a development environment, `python db_manage.py init` creates missing tables. `python migrate_legacy_quotes.py` is a separate compatibility helper for pre-existing quotes. It preserves old quote rows, assigns legacy rows to the simulated Sales A owner when no owner existed, and does not invent missing historical reference data. These are not production migration commands.

## Dashboard

The dashboard counts pending quote versions from the database and displays the latest 10 versions. Inventory checks compare the latest non-rejected version per inquiry against on-hand minus reserved stock. They do not aggregate different quote versions, promise inventory, trigger purchases, or commit to a delivery date. Empty states are displayed when no records or warnings exist.

## Main Modules

- `demo_roles.py`: simulated role and ownership checks.
- `workflow_service.py`: quote version, draft, submission, approval, and revision transactions.
- `records_page.py`, `approval_page.py`, `dashboard_page.py`: quote records, approval, and dashboard pages.
- `quote_exports.py`: CSV and printable HTML export.
- `verify_workflow.py`: development database workflow verification; it creates synthetic test quote records and leaves them in the database.
