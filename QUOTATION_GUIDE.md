# Inquiry, Costing, and Historical Price Guidance

Create an inquiry by selecting a customer and product, then entering quantity, delivery date, and quote-validity date. Product master data prefills the three unit production costs. Batch fixed costs and seller-paid batch logistics are entered for the inquiry. Changing or clearing product costs requires a reason; blank means unknown, while zero means a confirmed zero cost. Missing any of the five costs allows a draft inquiry but prevents approval submission. Quantity may be a positive decimal. Margin settings must satisfy `0 ≤ minimum margin ≤ target margin < 100%`.

Saving creates a unique `INQ` identifier and stores customer/product references, quantity, unit, currency, delivery date, validity, cost snapshot, source update date, and any supplied inquiry settings. Saving again creates a new inquiry rather than replacing the prior one. The Historical Prices page selects the latest saved inquiry in the current session; persisted inquiries can be selected again after restarting.

## Cost and Price Calculations

Base unit cost is:

`material + labor + manufacturing overhead + (batch fixed cost + seller-paid batch logistics) / quantity`

Target reference price is `unit cost / (1 - target margin / 100)`.
Minimum permitted unit price is `unit cost / (1 - minimum margin / 100)`.

Calculations use Python `Decimal` and do not round intermediate values. The default suggested price rounds the target price upward to the nearest cent. The manual proposed price displays its implied gross margin and order total.

Historical transactions are filtered by exact product ID, currency, and unit. Date and quantity bounds include endpoints. The page displays transaction count and P25/P50/P75 using an unweighted, linearly interpolated percentile. Fewer than 10 matches prompts a small-sample caution. No matches show a no-reference message without hiding available cost calculations.

The separate model reference predicts historical transaction price; it does not replace cost calculations or manual pricing. See [MODEL_GUIDE.md](MODEL_GUIDE.md). Historical transaction prices may already reflect their original payment terms. The current calculation does not add a payment premium to the historical or predicted price a second time.

## Payment-Term and Validity Inputs

The inquiry form contains demonstration fields for advance-payment percentage, balance term, annual cost-of-funds rate, default/maximum validity, stale-cost threshold, material-price movement, supplier quote expiry, and an optional customer-overdue validity policy toggle. These are per-inquiry interface inputs; a durable manager-maintained company-policy screen is not implemented.

The financing helper estimates a single balance collection. It estimates cash advanced as the greater of zero and base batch cost minus the immediate-payment reference total multiplied by the advance percentage. It then computes `estimated cash advanced × annual cost-of-funds rate × balance-term days / 365`. The estimate assumes production cost is funded in one amount at delivery and the advance uses the immediate-payment reference total. It is not the accounts receivable balance. The financing charge is included once in the saved finance-adjusted cost floor; it is not added again to the historical-price or model references. These are simplified demonstration assumptions, not a staged cash-flow forecast.

Validity guidance uses the selected cost update date, optional material-price movement, optional supplier expiry, and the entered demonstration thresholds. Missing information is explained and the default validity is used. Customer overdue status only influences validity when the explicit toggle is enabled; otherwise it is only a manager-review signal. The suggestion does not claim an AI conclusion.

The current customer payment summary is based on synthetic whole-order payment dates. `payment_ledger` and service code are present, but partial-payment entry/reporting is not fully integrated into the UI.

## Saving and Approval

The quote workflow saves a draft snapshot before submission. Submission revalidates the saved cost floor and state in the backend; it rejects missing costs, non-positive or below-floor price, expired validity, and repeated submission. “Submitted” means awaiting review, not approved. See [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) for the simulated-role approval lifecycle.

## Key Files

- `quotation_rules.py`: Decimal-based costs, margins, validation, and percentiles.
- `finance_rules.py`: demonstration funding-cost and validity rules.
- `inquiry_service.py`: inquiry persistence and source-cost snapshot.
- `workflow_service.py`: quote version, role/state validation, submission, and approval transactions.
- `quotation_ui.py`: cost explanation and supplementary reminders.
- `quote_page.py`, `history_page.py`: inquiry and historical-analysis pages.
- `inquiry_details`: one-to-one inquiry extension containing dates and JSONB snapshot.

## Checks

Use `python -m unittest discover -s tests -v` for pure logic tests. Manual inquiry and approval checks require the development database and Streamlit interface. Do not treat a unit test as evidence that an external deployment has been tested.
