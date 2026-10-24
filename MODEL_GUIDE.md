# Synthetic Historical Price Prediction Prototype

This CPU-based scikit-learn prototype predicts historical transaction unit price. It is not an optimal-profit pricing model, a customer purchase-probability model, or a claim of commercial benefit. Metrics on synthetic data validate only the prototype workflow.

## Training and Evaluation

From the repository root:

```bash
python train_price_model.py
python -m unittest discover -s tests -v
```

Training does not connect to PostgreSQL or use database imports. It reads the 300 fixed-seed CNY transactions from `generate_data.generate()` and the 320 MYR transactions from the four reviewable `sample_data/MYR_模拟数据_*.csv` files. Run `python generate_myr_data.py` first if those files are missing. Regenerate them only when intentionally changing the MYR dataset. CSV imports do not retrain the model, and the web app does not train on page refresh, startup, or publish.

Artifacts:

- `models/historical_price/model.joblib`: model pipelines and metadata.
- `models/historical_price/evaluation.json`: training time, data SHA-256 version, feature list, algorithm, library version, date split, sample counts, and per-group evaluation.
- The Historical Prices page displays evaluation information for the selected product group.

Load only a trusted model artifact produced by this project. Loading an untrusted `joblib` file can execute code. Training writes a temporary file and atomically replaces the model artifact to avoid a partial model.

## Features and Time Split

Rows from both synthetic sources are sorted by transaction date and order ID. A chronological cutoff near the 80th percentile separates training and test sets; records from the same date are kept together. The current recorded run used cutoff `2026-08-13`, with 496 training rows and 124 test rows. Metadata records both generator seeds, the hash of the combined rows, and the separate MYR CSV source.

Separate models are fitted per product ID, currency, and unit. Numeric input features are quantity, historical unit cost, ordinal date, and month. Product/currency/unit select the applicable model. Transaction price is the target, never an input. Actual payment date and other post-transaction outcomes are excluded.

For these synthetic data, historical unit cost means the sum of material, labor, and manufacturing overhead at the time; inference uses the corresponding saved inquiry production-cost inputs, not batch fixed or logistics allocation. The inquiry creation date is used as the prediction date.

Each group's `StandardScaler` and `Ridge(alpha=1)` pipeline is fitted only on training rows. The test set is only transformed and predicted; it is not used to tune or refit the model. The baseline is the median transaction price from the same group's training set, evaluated on the same test rows using MAE. MAE is reported separately in each group's currency; currencies are not pooled. Groups with fewer than 20 training rows or 5 test rows are not served.

Recorded evaluation (lower MAE is better; each value uses that product's currency):

| Product ID | Currency | Baseline MAE | Model MAE | Result |
|---|---|---:|---:|---|
| P001 | CNY | 6.4500 | 7.5625 | Model did not beat baseline |
| P002 | CNY | 5.9346 | 3.6515 | Model MAE lower |
| P003 | CNY | 13.4467 | 10.7611 | Model MAE lower |
| P004 | CNY | 5.8117 | 4.1854 | Model MAE lower |
| P005 | CNY | 6.0617 | 6.5109 | Model did not beat baseline |
| P006 | CNY | 7.4408 | 5.5226 | Model MAE lower |
| P_MY_001 | MYR | 2.6636 | 2.3087 | Model MAE lower |
| P_MY_002 | MYR | 0.4667 | 0.2990 | Model MAE lower |
| P_MY_003 | MYR | 0.7900 | 0.4028 | Model MAE lower |
| P_MY_004 | MYR | 1.4614 | 0.6866 | Model MAE lower |

On this fixed synthetic test split, model MAE is lower than the median baseline for 8 of 10 groups; it is worse for CNY products P001 and P005. These synthetic-data metrics validate prototype wiring only; they do not establish real Malaysian market accuracy, commercial benefit, optimal pricing, or customer purchase probability. Predictions do not automatically replace a manually entered quote.

## Applicability and Fallback

Quantity and historical cost must be within that group's training ranges. The inquiry date must fall from the training start date through 180 days after the training end date. These are prototype applicability bounds, not guarantees of accuracy.

When a group is missing or below the sample threshold, an input is missing/out of range, the model is absent/damaged, or the scikit-learn version differs, the page explains why no prediction is shown and retains available cost and historical references. “No comparable historical reference” does not prevent displaying a valid cost calculation.

The app snapshots the prediction, reason, and model data version in the quote reference when available. To refresh the artifact, run training explicitly and redeploy the project with the generated model. There is no online training or model-upload feature. A RunPod worker image must also be rebuilt and the endpoint updated to serve the new artifact; see `runpod/README.md`.
