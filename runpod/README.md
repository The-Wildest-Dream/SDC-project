# RunPod Serverless inference worker

This worker wraps the existing trusted model artifact and `price_model.predict_price`.
It does not train a model, implement a second prediction algorithm, connect to
PostgreSQL, or contain API/database credentials. Inference runs on CPU; GPU is
neither required nor claimed.

## Build

Run these commands from the repository root. The build context must be the
repository root because the image copies the existing inference module and
trained model artifact:

```bash
docker build -f runpod/Dockerfile -t <your-registry>/sdc-price-worker:latest .
docker push <your-registry>/sdc-price-worker:latest
```

Create a RunPod Serverless endpoint that uses the pushed image. Its startup
command is already configured as `python /app/runpod/handler.py`; no model
retraining or database access is needed. Choose a CPU-capable worker. The
example `runpod/test_input.json` is a valid request for the checked-in model.
In the RunPod console, create a Serverless Endpoint, select the pushed container
image, and set a worker count/idle policy appropriate for your demo. Copy the
endpoint ID for the Replit-side client. The worker uses the image's default
startup command; it does not need an API key or PostgreSQL connection.

Example request body sent to the endpoint:

```json
{
  "input": {
    "product": "P001",
    "currency": "CNY",
    "unit": "件",
    "quantity": 100,
    "cost": 50,
    "day": "2026-10-23"
  }
}
```

The response has `prediction`, `prediction_status`, `model_version`,
`error_reason`, `reason`, and `metadata`. `model_version` is the existing
artifact's synthetic-data version hash. Out-of-scope values use
`prediction_status: "unavailable"` with a reason; they are not replaced by a
new algorithm.

To send the sample request directly after the endpoint is ready, put your
credentials in your local shell environment (do not commit or paste them into
the project) and run:

```bash
curl -sS -X POST \
  "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/run" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  --data @runpod/test_input.json
```

The response includes a job `id`. Poll
`https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/status/<job-id>` using the same
Authorization header until its status is `COMPLETED`; inspect the `output`
object for the prediction or an unavailable reason. This remote test submits a
billable Serverless job.

## Replit-side client

`runpod_client.py` is a standalone client and is intentionally not connected to
the current Streamlit page. To prepare a later integration, configure
`RUNPOD_API_KEY` through Replit Secrets and set `RUNPOD_ENDPOINT_ID` as an
environment variable. Optional settings are:

- `RUNPOD_TOTAL_TIMEOUT_SECONDS` (default 180)
- `RUNPOD_REQUEST_TIMEOUT_SECONDS` (default 30)
- `RUNPOD_POLL_INTERVAL_SECONDS` (default 2)

Call `runpod_client.predict_price(...)`. It returns the existing application's
three-item `(value, reason, metadata)` shape. The returned metadata includes
`prediction_source`: `runpod`, `local_fallback`, or `unavailable`. The local
fallback is explicit through the `allow_local_fallback` argument (default
`True`); pass `False` to surface RunPod unavailability instead. Missing RunPod
configuration never changes the behavior of the production page because the
client is not wired into it.

## Tests

From the repository root:

```bash
python -m unittest discover -s tests -v
```

Tests use mocked HTTP responses and the actual local model artifact; they do not
require RunPod credentials or submit a billable remote job. They compare the
worker's result with the existing local inference result for the same input.

## Model and data safety

The Docker image copies only the trusted project inference code and checked-in
`models/historical_price/model.joblib`. It never copies `.env`, secrets, or a
database URL. Only the existing inference function's product/currency/unit,
quantity, historical unit cost, and date features are used. Features and
applicability ranges remain enforced by the reused project logic.
