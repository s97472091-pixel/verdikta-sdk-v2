# Verdikta Developer SDK (Python) — Submission

## Public repository

Repository: `REPLACE_WITH_PUBLIC_GITHUB_URL`

## Installability

Install from GitHub:

```bash
pip install git+REPLACE_WITH_PUBLIC_GITHUB_URL.git
```

Optional PyPI install after publication:

```bash
pip install verdikta-sdk
```

Local install from this package:

```bash
python -m pip install .
```

## What was built

This submission provides a Python 3.8+ SDK for the Verdikta Bounties API. The package name is `verdikta-sdk` and the import name is `verdikta_sdk`.

Implemented coverage includes:

- `GET /jobs` with filtering and pagination
- `GET /jobs/:id`
- `GET /jobs/:id/rubric`
- `POST /jobs/:id/submit/dry-run`
- `POST /jobs/:id/submit`
- `POST /jobs/:id/submit/bundle`
- `POST /jobs/:id/submit/bundle/complete`
- `POST /jobs/:id/submit/prepare`
- `POST /jobs/:id/submissions/confirm`
- `POST /jobs/:id/submissions/:subId/start`
- `POST /jobs/:id/submissions/:subId/finalize`
- `POST /jobs/:id/submissions/:subId/timeout`
- `GET /jobs/:id/submissions`
- `GET /jobs/:id/submissions/:subId/evaluation`
- `GET /jobs/:id/submissions/:subId/diagnose`
- `POST /jobs/:id/submissions/:subId/refresh`
- `GET /jobs/:id/onchain-status`
- `GET /jobs/:id/evaluation-package`
- `GET /jobs/lookup`
- `GET /jobs/eth-price`
- `GET /classes`, `GET /classes/:classId`, `GET /classes/:classId/models`

## Required examples

The repository includes three working examples:

1. `examples/discover_open_bounties.py` — discover open bounties with filtering.
2. `examples/submit_work.py` — dry-run, upload work files, and request Verdikta transaction bundle/calldata.
3. `examples/monitor_evaluation.py` — monitor submission status and retrieve evaluation results.

## README coverage

The README includes:

- Installation instructions from GitHub, local checkout, and PyPI build/publish flow
- Authentication setup using `VERDIKTA_API_KEY` and `X-Bot-API-Key`
- Quickstart code snippets
- API reference for all implemented SDK methods
- Known limitations and gotchas, including the current Verdikta flow where `/submit` only uploads/pins files and the on-chain steps still need wallet signing/broadcasting

## Technical requirements checklist

- Python 3.8+ compatible: yes (`requires-python = ">=3.8"`)
- Proper error handling: yes (`AuthenticationError`, `ValidationError`, `NotFoundError`, `RateLimitError`, `NetworkError`, `APIError`)
- Type hints throughout: yes, with `py.typed`
- No hardcoded API keys or secrets: yes, API key is environment/config input only
- Packaging best practices: yes, `pyproject.toml`, package metadata, optional dev dependencies, GitHub Actions test workflow
- Tests for core functionality: yes, pytest tests with `httpx.MockTransport`; no live API calls required

## Test result

Local test run:

```text
10 passed
```

## Notes

The SDK intentionally does not manage private keys or broadcast transactions. Verdikta returns transaction objects containing `to`, `data`, `value`, and `chainId`; the user should sign and broadcast these with their own wallet tooling.
