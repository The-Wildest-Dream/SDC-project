# RunPod Serverless inference worker

This worker wraps the existing trusted model artifact and `price_model.predict_price`.
It does not train a model, implement a second prediction algorithm, connect to
PostgreSQL, or contain API/database credentials. Inference runs on CPU; GPU is
neither required nor claimed.

## Build

Run these commands from the repository root after training. The build context
must be the repository root because the image copies the project's inference
module, updated trusted model, and matching evaluation metadata. Use a new,
versioned tag so it is clear which artifact the endpoint is serving:

```bash
export REGISTRY_HOST=YOUR_REGISTRY_HOST
export IMAGE_NAMESPACE=YOUR_REGISTRY_NAMESPACE
export IMAGE_NAME=sdc-price-worker
export IMAGE_TAG="${REGISTRY_HOST}/${IMAGE_NAMESPACE}/${IMAGE_NAME}:myr-20261024-v1"
docker login "$REGISTRY_HOST"
docker build -f runpod/Dockerfile -t "$IMAGE_TAG" .
docker push "$IMAGE_TAG"
```

For Docker Hub, use `REGISTRY_HOST=docker.io` and your account or organization
as `IMAGE_NAMESPACE`. For another registry, use its hostname and namespace.
Use the registry's normal interactive login; do not put credentials in the
project. In RunPod, open the existing Serverless Endpoint, edit its container
image to the exact `IMAGE_TAG` pushed above, save the endpoint template, and
deploy/restart the endpoint so workers are recreated from that image. Keep its
existing handler/start command (`python /app/runpod/handler.py`) and CPU-capable
worker configuration. Do not create or replace an endpoint unless that is
intentional. If you instead create a new endpoint, update the Replit
`RUNPOD_ENDPOINT_ID` Secret to that endpoint ID; do not put credentials in this
repository. This image contains the newly trained MYR and existing CNY groups.

After redeployment, `runpod/test_input.json` remains a supported CNY request;
`runpod/test_input_myr.json` exercises the MYR model group.

## Replit handoff

In the Replit Shell, from the project root, run:

```bash
python generate_myr_data.py
python train_price_model.py
```

Review `models/historical_price/evaluation.json` and the four MYR CSVs. The
Streamlit app loads the resulting local model artifact from this workspace.
Keep the existing Replit `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` Secrets
unchanged when updating the image on the same endpoint. Do not print their
values. After changing the Python code or model artifact, republish the app
manually if you want the published app to use this version. A newly created
RunPod endpoint requires updating only the endpoint-ID Secret.

Example existing CNY request body sent to the endpoint:

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

To verify MYR after the endpoint image has been updated, use the same request
and polling steps with `--data @runpod/test_input_myr.json`. This makes a real,
potentially billable Serverless inference request; do not run it against the
old image and treat an unsupported MYR result as a model failure.

## Replit-side client

The historical price page calls `runpod_client.predict_price(...)`. Configure
`RUNPOD_API_KEY` through Replit Secrets and set `RUNPOD_ENDPOINT_ID` as an
environment variable in the Replit app. Optional settings are:

- `RUNPOD_TOTAL_TIMEOUT_SECONDS` (default 180)
- `RUNPOD_REQUEST_TIMEOUT_SECONDS` (default 30)
- `RUNPOD_POLL_INTERVAL_SECONDS` (default 2)

Call `runpod_client.predict_price(...)`. It returns the existing application's
three-item `(value, reason, metadata)` shape. The returned metadata includes
`prediction_source`: `runpod`, `local_fallback`, or `unavailable`. The current
page explicitly enables local fallback so a temporary endpoint failure does
not block the quotation workflow; the interface labels the source. Pass
`allow_local_fallback=False` in verification code to ensure the result is
actually remote.

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
