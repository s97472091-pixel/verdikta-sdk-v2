# verdikta-sdk

Python SDK for the [Verdikta Bounties API](https://bounties.verdikta.org/api/docs). It wraps bounty discovery, bounty details/rubrics, submission validation/upload, transaction bundle preparation, status monitoring, and evaluation retrieval.

> Package import name: `verdikta_sdk`  
> PyPI package name: `verdikta-sdk`

## Features

- Python 3.8+ compatible
- Typed public methods and PEP 561 marker (`py.typed`)
- `X-Bot-API-Key` authentication support
- Friendly exception hierarchy for API, auth, validation, 404, rate-limit, and network failures
- Multipart file upload helpers for dry-runs and submissions
- Convenience wrappers for the main Verdikta bounty flow:
  - discover/list jobs
  - read job details and rubrics
  - dry-run submission files
  - upload submission files and get `hunterCid`
  - create prepared transaction bundle/calldata
  - monitor submissions
  - retrieve finalized evaluation reports

## Installation

### From GitHub

```bash
pip install git+https://github.com/s97472091-pixel/verdikta-sdk-v2.git
```

Replace `yourname` after you publish the repository.

### From local checkout

```bash
git clone https://github.com/s97472091-pixel/verdikta-sdk-v2.git
cd verdikta-sdk
python -m pip install .
```

### Development install

```bash
python -m pip install -e ".[dev]"
pytest
```

### Build for PyPI

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

## Authentication setup

Verdikta uses the `X-Bot-API-Key` header for bot/API access.

Set the API key in your shell:

```bash
export VERDIKTA_API_KEY="your-bot-api-key"
```

Windows PowerShell:

```powershell
$env:VERDIKTA_API_KEY="your-bot-api-key"
```

Then create a client:

```python
from verdikta_sdk import VerdiktaClient

client = VerdiktaClient.from_env()
```

Or pass the key directly when needed:

```python
from verdikta_sdk import VerdiktaClient

client = VerdiktaClient(api_key="your-bot-api-key")
```

Never commit API keys, `.env` files, private keys, or wallet seed phrases.

## Quickstart

### 1. Discover open bounties

```python
from verdikta_sdk import VerdiktaClient

with VerdiktaClient.from_env() as client:
    jobs = client.list_open_bounties(
        work_product_type=["code", "writing"],
        min_hours_left=2,
        min_bounty_usd=5,
        search="SDK",
        limit=10,
    )

print(jobs)
```

CLI example:

```bash
python examples/discover_open_bounties.py --min-usd 5 --type code --search sdk
```

### 2. Read bounty details and rubric

```python
from verdikta_sdk import VerdiktaClient

job_id = 123

with VerdiktaClient.from_env() as client:
    job = client.get_job(job_id, include_rubric=True)
    rubric = client.get_rubric(job_id)

print(job)
print(rubric)
```

### 3. Validate and upload submission work

```python
from pathlib import Path
from verdikta_sdk import ValidationError, VerdiktaClient

job_id = 123
hunter = "0xYourHunterWallet"
files = [Path("submission.md")]

with VerdiktaClient.from_env() as client:
    try:
        dry_run = client.dry_run_submission(job_id, files=files, hunter=hunter)
    except ValidationError as exc:
        print("Fix validation errors before submitting:")
        print(exc.payload)
        raise

    upload = client.upload_submission(
        job_id,
        files=files,
        hunter=hunter,
        submission_narrative="Python SDK bounty submission",
        file_descriptions={"submission.md": "Main work product"},
    )

hunter_cid = upload["submission"]["hunterCid"]
print("hunterCid:", hunter_cid)
```

CLI example:

```bash
python examples/submit_work.py 123 0xYourHunterWallet ./submission.md
```

### 4. Prepare transaction bundle for on-chain submission

`POST /jobs/:id/submit` only uploads/pins files and returns a `hunterCid`. To complete a Verdikta submission, you still need to sign and broadcast on-chain transactions. The SDK can request Verdikta's prepared transaction objects for you:

```python
from verdikta_sdk import VerdiktaClient

job_id = 123
hunter = "0xYourHunterWallet"
hunter_cid = "bafy..."

with VerdiktaClient.from_env() as client:
    bundle = client.create_submission_bundle(
        job_id,
        hunter_address=hunter,
        hunter_cid=hunter_cid,
    )

print(bundle["transaction"])  # contains to, data, value, chainId
```

Sign and broadcast `transaction` with your wallet tooling. Verdikta transaction objects use `transaction.data` for calldata, not `data.calldata`.

### 5. Monitor status and retrieve evaluation results

```python
from verdikta_sdk import APIError, VerdiktaClient

job_id = 123
submission_id = 4

with VerdiktaClient.from_env() as client:
    submissions = client.list_submissions(job_id)
    print(submissions)

    try:
        evaluation = client.get_submission_evaluation(job_id, submission_id)
        print(evaluation)
    except APIError as exc:
        print("Evaluation is not available yet:", exc)
```

CLI example:

```bash
python examples/monitor_evaluation.py 123 --submission-id 4 --poll-seconds 30
```

## API reference

### Client creation

#### `VerdiktaClient(api_key=None, base_url=..., timeout=30.0, http_client=None)`

Creates a synchronous Verdikta API client.

#### `VerdiktaClient.from_env(env_var="VERDIKTA_API_KEY", base_url=..., timeout=30.0)`

Creates a client using an API key from the environment.

#### `client.close()`

Closes the underlying HTTP connection pool. You can also use `with VerdiktaClient.from_env() as client:`.

### Bounty discovery and details

#### `client.list_jobs(...)`

Wraps `GET /jobs`.

Supported filters:

- `status`: `OPEN`, `EXPIRED`, `AWARDED`, `CLOSED`, `CANCELLED`
- `work_product_type`: string or sequence, e.g. `"code"` or `["code", "writing"]`
- `min_hours_left`, `max_hours_left`
- `min_bounty_usd`, `max_bounty_usd`
- `class_id`
- `exclude_submitted_by`
- `has_winner`
- `target_hunter`: wallet address, `any`, or `none`
- `search`
- `limit`, `offset`

#### `client.list_open_bounties(**filters)`

Convenience wrapper around `list_jobs(status="OPEN", **filters)`.

#### `client.get_job(job_id, include_rubric=False)`

Wraps `GET /jobs/:id`.

#### `client.get_onchain_status(bounty_id)`

Wraps `GET /jobs/:id/onchain-status`. Use this when cached API details may be stale or when you need blockchain-authoritative status.

#### `client.get_rubric(job_id)`

Wraps `GET /jobs/:id/rubric`.

#### `client.get_evaluation_package(job_id)`

Wraps `GET /jobs/:id/evaluation-package`.

#### `client.lookup_job(bounty_id=None, tx_hash=None, evaluation_cid=None)`

Wraps `GET /jobs/lookup`. Exactly one identifier is required.

### Submission validation, upload, and transaction preparation

#### `client.dry_run_submission(job_id, files, hunter)`

Wraps `POST /jobs/:id/submit/dry-run` as multipart form data. It validates files without paying or registering on-chain.

#### `client.upload_submission(job_id, files, hunter, submission_narrative=None, file_descriptions=None)`

Wraps `POST /jobs/:id/submit` as multipart form data. Returns a `hunterCid` in the Verdikta response.

Important: this only uploads/pins files. It does not complete the on-chain submission.

#### `client.create_submission_bundle(job_id, hunter_address, hunter_cid=None, files=None, addendum=None, alpha=None, max_oracle_fee=None, estimated_base_cost=None, max_fee_based_scaling=None)`

Wraps `POST /jobs/:id/submit/bundle`. Provide either `hunter_cid` or `files`. Returns Verdikta transaction data/templates for the submission flow.

#### `client.complete_submission_bundle(job_id, tx_hash)`

Wraps `POST /jobs/:id/submit/bundle/complete`. Use after broadcasting step 1.

#### `client.prepare_submission(job_id, hunter, hunter_cid, addendum="", alpha=500, max_oracle_fee="0.00002", estimated_base_cost="0.00001", max_fee_based_scaling="3")`

Wraps `POST /jobs/:id/submit/prepare`. Returns encoded `prepareSubmission` calldata.

#### `client.confirm_submission(job_id, submission_id, hunter, hunter_cid, eval_wallet=None, file_count=None, files=None)`

Wraps `POST /jobs/:id/submissions/confirm`. Call after step 1 succeeds on-chain so Verdikta backend reflects the new submission.

#### `client.start_submission(job_id, submission_id, hunter, eth_max_budget=None)`

Wraps `POST /jobs/:id/submissions/:subId/start`. Returns encoded payable calldata for starting evaluation.

#### `client.finalize_submission(job_id, submission_id, hunter)`

Wraps `POST /jobs/:id/submissions/:subId/finalize`. Returns encoded calldata for finalization when oracle results are ready.

#### `client.timeout_submission(job_id, submission_id)`

Wraps `POST /jobs/:id/submissions/:subId/timeout`. Use only for eligible stuck evaluations.

### Monitoring and evaluation retrieval

#### `client.list_submissions(job_id)`

Wraps `GET /jobs/:id/submissions`.

#### `client.get_submission_evaluation(job_id, submission_id)`

Wraps `GET /jobs/:id/submissions/:subId/evaluation`.

#### `client.diagnose_submission(job_id, submission_id)`

Wraps `GET /jobs/:id/submissions/:subId/diagnose`.

#### `client.refresh_submission(job_id, submission_id)`

Wraps `POST /jobs/:id/submissions/:subId/refresh`.

### Utility endpoints

#### `client.eth_price()`

Wraps `GET /jobs/eth-price`.

#### `client.list_classes(status=None, provider=None)`

Wraps `GET /classes`.

#### `client.get_class(class_id)`

Wraps `GET /classes/:classId`.

#### `client.list_class_models(class_id)`

Wraps `GET /classes/:classId/models`.

## Error handling

All SDK-specific exceptions inherit from `VerdiktaError`.

```python
from verdikta_sdk import (
    APIError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    VerdiktaClient,
)

with VerdiktaClient.from_env() as client:
    try:
        job = client.get_job(123)
    except AuthenticationError:
        print("Missing or invalid API key")
    except NotFoundError:
        print("Job not found")
    except ValidationError as exc:
        print("Bad request", exc.payload)
    except RateLimitError:
        print("Too many requests")
    except NetworkError:
        print("Network problem")
    except APIError as exc:
        print("Other API error", exc.status_code, exc.payload)
```

## File upload formats

`files` can be a list of paths:

```python
client.upload_submission(123, files=["submission.md", "report.pdf"], hunter="0x...")
```

Or file-like tuples:

```python
with open("submission.md", "rb") as fp:
    client.upload_submission(
        123,
        files=[("submission.md", fp, "text/markdown")],
        hunter="0x...",
    )
```

## Known limitations and gotchas

1. **No wallet signing is built in.** This SDK wraps Verdikta's HTTP API and returns transaction objects. You must sign/broadcast on Base with your own wallet tooling.
2. **`POST /jobs/:id/submit` is not the whole submission flow.** It uploads work files and returns `hunterCid`; it does not register or start the on-chain submission by itself.
3. **Use dry-run before real submission.** `dry_run_submission` catches many file/readability issues before you pay gas or oracle prepay.
4. **Do not upload zip/archive/binary bundles for evaluation.** Verdikta expects oracle-readable work files such as text, code, markdown, PDF, docx, and images. Archives may be rejected or skipped.
5. **Calldata location matters.** Verdikta transaction responses use `transaction.data`; do not look for `data.calldata`.
6. **Some false flags are normal state, not API failures.** For example, `canTimeout=false` or `canClose=false` means the action is not eligible yet.
7. **Finalize is required.** Oracle acceptance does not automatically pay the hunter. You must call/finalize when the evaluation is ready.
8. **Bounty id vs API job id can drift.** Use `lookup_job` or `get_onchain_status` when diagnosing ID mismatch.
9. **ETH fee fields accept dual units on Verdikta endpoints.** Decimal strings like `"0.00002"` are ETH; bare integer strings like `"20000000000000"` are wei.
10. **No secrets are stored by the SDK.** Keep API keys in environment variables and never commit wallet credentials.

## Tests

```bash
python -m pip install -e ".[dev]"
pytest
```

The tests use `httpx.MockTransport`, so they do not hit the live Verdikta API.

## Publishing checklist

1. Create a public GitHub repo, for example `verdikta-sdk`.
2. Update `project.urls.Repository` and `project.urls.Issues` in `pyproject.toml`.
3. Push the code:

```bash
git init
git add .
git commit -m "Initial Verdikta Python SDK"
git branch -M main
git remote add origin https://github.com/s97472091-pixel/verdikta-sdk-v2.git
git push -u origin main
```

4. Verify GitHub install:

```bash
python -m pip install git+https://github.com/s97472091-pixel/verdikta-sdk-v2.git
```

5. Optional PyPI publish:

```bash
python -m build
python -m twine upload dist/*
```

## License

MIT
