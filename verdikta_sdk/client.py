"""Synchronous client for the Verdikta Bounties API."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple, Union, cast

import httpx

from .errors import (
    APIError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from .types import FileInput

JsonDict = Dict[str, Any]
Params = Dict[str, Union[str, int, float, bool]]
MultipartFile = Tuple[str, Tuple[str, Any]]


class VerdiktaClient:
    """Client for the Verdikta Bounties API.

    Parameters:
        api_key: Optional bot API key. When provided, the SDK sends it in the
            ``X-Bot-API-Key`` header.
        base_url: API base URL. Defaults to Verdikta production API.
        timeout: Request timeout in seconds.
        http_client: Optional preconfigured ``httpx.Client`` for tests or custom transports.
    """

    DEFAULT_BASE_URL = "https://bounties.verdikta.org/api"
    ENV_API_KEY = "VERDIKTA_API_KEY"

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(base_url=self.base_url, timeout=timeout)

    @classmethod
    def from_env(
        cls,
        *,
        env_var: str = ENV_API_KEY,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> "VerdiktaClient":
        """Create a client using ``VERDIKTA_API_KEY`` or a custom env var."""
        return cls(api_key=os.getenv(env_var), base_url=base_url, timeout=timeout)

    def __enter__(self) -> "VerdiktaClient":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        if self._owns_client:
            self._client.close()

    def list_jobs(
        self,
        *,
        status: Optional[str] = None,
        work_product_type: Optional[Union[str, Sequence[str]]] = None,
        min_hours_left: Optional[int] = None,
        max_hours_left: Optional[int] = None,
        min_bounty_usd: Optional[float] = None,
        max_bounty_usd: Optional[float] = None,
        class_id: Optional[int] = None,
        exclude_submitted_by: Optional[str] = None,
        has_winner: Optional[bool] = None,
        target_hunter: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> JsonDict:
        """List Verdikta bounties with filtering and pagination."""
        params: Params = {"limit": limit, "offset": offset}
        self._add_param(params, "status", status)
        if work_product_type is not None:
            if isinstance(work_product_type, str):
                params["workProductType"] = work_product_type
            else:
                params["workProductType"] = ",".join(work_product_type)
        self._add_param(params, "minHoursLeft", min_hours_left)
        self._add_param(params, "maxHoursLeft", max_hours_left)
        self._add_param(params, "minBountyUSD", min_bounty_usd)
        self._add_param(params, "maxBountyUSD", max_bounty_usd)
        self._add_param(params, "classId", class_id)
        self._add_param(params, "excludeSubmittedBy", exclude_submitted_by)
        self._add_param(params, "hasWinner", has_winner)
        self._add_param(params, "targetHunter", target_hunter)
        self._add_param(params, "search", search)
        return self._request("GET", "jobs", params=params)

    def list_open_bounties(self, **filters: Any) -> JsonDict:
        """Convenience wrapper around :meth:`list_jobs` with ``status='OPEN'``."""
        filters.setdefault("status", "OPEN")
        return self.list_jobs(**filters)

    def get_job(self, job_id: Union[int, str], *, include_rubric: bool = False) -> JsonDict:
        """Fetch bounty details by bounty/job id."""
        params: Params = {}
        if include_rubric:
            params["includeRubric"] = True
        return self._request("GET", f"jobs/{job_id}", params=params)

    def get_onchain_status(self, bounty_id: Union[int, str]) -> JsonDict:
        """Fetch the authoritative on-chain snapshot for a bounty id."""
        return self._request("GET", f"jobs/{bounty_id}/onchain-status")

    def get_rubric(self, job_id: Union[int, str]) -> JsonDict:
        """Fetch the rubric/evaluation criteria for a bounty."""
        return self._request("GET", f"jobs/{job_id}/rubric")

    def get_evaluation_package(self, job_id: Union[int, str]) -> JsonDict:
        """Fetch the full evaluation package for a bounty."""
        return self._request("GET", f"jobs/{job_id}/evaluation-package")

    def dry_run_submission(
        self,
        job_id: Union[int, str],
        *,
        files: Sequence[FileInput],
        hunter: str,
    ) -> JsonDict:
        """Validate submission files without paying or registering on-chain."""
        with self._build_files(files) as multipart_files:
            return self._request(
                "POST",
                f"jobs/{job_id}/submit/dry-run",
                data={"hunter": hunter},
                files=multipart_files,
            )

    def upload_submission(
        self,
        job_id: Union[int, str],
        *,
        files: Sequence[FileInput],
        hunter: str,
        submission_narrative: Optional[str] = None,
        file_descriptions: Optional[Mapping[str, str]] = None,
    ) -> JsonDict:
        """Upload submission files to IPFS and return a ``hunterCid``.

        This method maps to ``POST /jobs/:id/submit``. It does not sign or
        broadcast on-chain transactions. Use the returned ``hunterCid`` with
        ``create_submission_bundle`` or ``prepare_submission``.
        """
        data: Dict[str, str] = {"hunter": hunter}
        if submission_narrative is not None:
            data["submissionNarrative"] = submission_narrative
        if file_descriptions is not None:
            data["fileDescriptions"] = json.dumps(dict(file_descriptions))
        with self._build_files(files) as multipart_files:
            return self._request("POST", f"jobs/{job_id}/submit", data=data, files=multipart_files)

    def create_submission_bundle(
        self,
        job_id: Union[int, str],
        *,
        hunter_address: str,
        hunter_cid: Optional[str] = None,
        files: Optional[Sequence[FileInput]] = None,
        addendum: Optional[str] = None,
        alpha: Optional[int] = None,
        max_oracle_fee: Optional[str] = None,
        estimated_base_cost: Optional[str] = None,
        max_fee_based_scaling: Optional[str] = None,
    ) -> JsonDict:
        """Create a pre-encoded transaction bundle for the full submission flow.

        Provide either ``hunter_cid`` for already uploaded work or ``files`` to
        let Verdikta pin files as part of the bundle call.
        """
        if not hunter_cid and not files:
            raise ValueError("create_submission_bundle requires hunter_cid or files")

        payload: Dict[str, Any] = {"hunterAddress": hunter_address}
        self._add_payload(payload, "hunterCid", hunter_cid)
        self._add_payload(payload, "addendum", addendum)
        self._add_payload(payload, "alpha", alpha)
        self._add_payload(payload, "maxOracleFee", max_oracle_fee)
        self._add_payload(payload, "estimatedBaseCost", estimated_base_cost)
        self._add_payload(payload, "maxFeeBasedScaling", max_fee_based_scaling)

        if files:
            data = {key: str(value) for key, value in payload.items()}
            with self._build_files(files) as multipart_files:
                return self._request(
                    "POST",
                    f"jobs/{job_id}/submit/bundle",
                    data=data,
                    files=multipart_files,
                )
        return self._request("POST", f"jobs/{job_id}/submit/bundle", json=payload)

    def complete_submission_bundle(self, job_id: Union[int, str], *, tx_hash: str) -> JsonDict:
        """Parse step-1 transaction receipt and return exact calldata for later steps."""
        return self._request("POST", f"jobs/{job_id}/submit/bundle/complete", json={"txHash": tx_hash})

    def prepare_submission(
        self,
        job_id: Union[int, str],
        *,
        hunter: str,
        hunter_cid: str,
        addendum: str = "",
        alpha: int = 500,
        max_oracle_fee: str = "0.00002",
        estimated_base_cost: str = "0.00001",
        max_fee_based_scaling: str = "3",
    ) -> JsonDict:
        """Get encoded ``prepareSubmission`` calldata for step 1."""
        payload = {
            "hunter": hunter,
            "hunterCid": hunter_cid,
            "addendum": addendum,
            "alpha": alpha,
            "maxOracleFee": max_oracle_fee,
            "estimatedBaseCost": estimated_base_cost,
            "maxFeeBasedScaling": max_fee_based_scaling,
        }
        return self._request("POST", f"jobs/{job_id}/submit/prepare", json=payload)

    def confirm_submission(
        self,
        job_id: Union[int, str],
        *,
        submission_id: Union[int, str],
        hunter: str,
        hunter_cid: str,
        eval_wallet: Optional[str] = None,
        file_count: Optional[int] = None,
        files: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> JsonDict:
        """Register a prepared submission in the backend after step-1 succeeds on-chain."""
        payload: Dict[str, Any] = {
            "submissionId": submission_id,
            "hunter": hunter,
            "hunterCid": hunter_cid,
        }
        self._add_payload(payload, "evalWallet", eval_wallet)
        self._add_payload(payload, "fileCount", file_count)
        self._add_payload(payload, "files", files)
        return self._request("POST", f"jobs/{job_id}/submissions/confirm", json=payload)

    def start_submission(
        self,
        job_id: Union[int, str],
        submission_id: Union[int, str],
        *,
        hunter: str,
        eth_max_budget: Optional[str] = None,
    ) -> JsonDict:
        """Get encoded ``startPreparedSubmission`` calldata for step 2."""
        payload: Dict[str, Any] = {"hunter": hunter}
        self._add_payload(payload, "ethMaxBudget", eth_max_budget)
        return self._request("POST", f"jobs/{job_id}/submissions/{submission_id}/start", json=payload)

    def finalize_submission(
        self,
        job_id: Union[int, str],
        submission_id: Union[int, str],
        *,
        hunter: str,
    ) -> JsonDict:
        """Get encoded ``finalizeSubmission`` calldata for step 3."""
        return self._request(
            "POST",
            f"jobs/{job_id}/submissions/{submission_id}/finalize",
            json={"hunter": hunter},
        )

    def timeout_submission(self, job_id: Union[int, str], submission_id: Union[int, str]) -> JsonDict:
        """Get encoded timeout calldata for stuck evaluations when eligible."""
        return self._request("POST", f"jobs/{job_id}/submissions/{submission_id}/timeout", json={})

    def list_submissions(self, job_id: Union[int, str]) -> JsonDict:
        """List submissions for a bounty with simplified statuses."""
        return self._request("GET", f"jobs/{job_id}/submissions")

    def get_submission_evaluation(self, job_id: Union[int, str], submission_id: Union[int, str]) -> JsonDict:
        """Fetch the full AI evaluation report for a finalized submission."""
        return self._request("GET", f"jobs/{job_id}/submissions/{submission_id}/evaluation")

    def diagnose_submission(self, job_id: Union[int, str], submission_id: Union[int, str]) -> JsonDict:
        """Run Verdikta's diagnostic checks for a submission."""
        return self._request("GET", f"jobs/{job_id}/submissions/{submission_id}/diagnose")

    def refresh_submission(self, job_id: Union[int, str], submission_id: Union[int, str]) -> JsonDict:
        """Sync a submission's backend status from blockchain state."""
        return self._request("POST", f"jobs/{job_id}/submissions/{submission_id}/refresh", json={})

    def lookup_job(
        self,
        *,
        bounty_id: Optional[Union[int, str]] = None,
        tx_hash: Optional[str] = None,
        evaluation_cid: Optional[str] = None,
    ) -> JsonDict:
        """Discover the API job for an on-chain bounty, tx hash, or evaluation CID."""
        supplied = [bounty_id is not None, tx_hash is not None, evaluation_cid is not None]
        if sum(supplied) != 1:
            raise ValueError("lookup_job requires exactly one of bounty_id, tx_hash, or evaluation_cid")
        params: Params = {}
        self._add_param(params, "bountyId", bounty_id)
        self._add_param(params, "txHash", tx_hash)
        self._add_param(params, "evaluationCid", evaluation_cid)
        return self._request("GET", "jobs/lookup", params=params)

    def eth_price(self) -> JsonDict:
        """Fetch Verdikta's cached ETH/USD price."""
        return self._request("GET", "jobs/eth-price")

    def list_classes(self, *, status: Optional[str] = None, provider: Optional[str] = None) -> JsonDict:
        """List Verdikta AI evaluation classes."""
        params: Params = {}
        self._add_param(params, "status", status)
        self._add_param(params, "provider", provider)
        return self._request("GET", "classes", params=params)

    def get_class(self, class_id: Union[int, str]) -> JsonDict:
        """Get one Verdikta AI evaluation class."""
        return self._request("GET", f"classes/{class_id}")

    def list_class_models(self, class_id: Union[int, str]) -> JsonDict:
        """List available models for a Verdikta class."""
        return self._request("GET", f"classes/{class_id}/models")

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Optional[Mapping[str, Any]] = None,
        data: Optional[Mapping[str, Any]] = None,
        files: Optional[Sequence[MultipartFile]] = None,
    ) -> JsonDict:
        headers = {"User-Agent": "verdikta-sdk-python/0.1.0"}
        if self.api_key:
            headers["X-Bot-API-Key"] = self.api_key

        try:
            response = self._client.request(
                method,
                path.lstrip("/"),
                params={k: self._stringify_bool(v) for k, v in (params or {}).items()},
                json=json,
                data=data,
                files=files,
                headers=headers,
            )
        except httpx.RequestError as exc:
            raise NetworkError(f"Could not reach Verdikta API: {exc}") from exc

        if response.is_success:
            return self._parse_json(response)

        payload = self._safe_payload(response)
        message = self._error_message(response, payload)
        exc_cls = self._exception_for_status(response.status_code)
        raise exc_cls(message, status_code=response.status_code, payload=payload)

    @staticmethod
    def _parse_json(response: httpx.Response) -> JsonDict:
        if response.content == b"":
            return {}
        try:
            parsed = response.json()
        except ValueError as exc:
            raise APIError("Verdikta API returned a non-JSON response", status_code=response.status_code) from exc
        if isinstance(parsed, dict):
            return cast(JsonDict, parsed)
        return {"data": parsed}

    @staticmethod
    def _safe_payload(response: httpx.Response) -> Mapping[str, Any]:
        try:
            parsed = response.json()
        except ValueError:
            return {"message": response.text}
        if isinstance(parsed, dict):
            return cast(Mapping[str, Any], parsed)
        return {"data": parsed}

    @staticmethod
    def _error_message(response: httpx.Response, payload: Mapping[str, Any]) -> str:
        for key in ("error", "message", "details", "reason", "hint"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        return response.reason_phrase or "Verdikta API request failed"

    @staticmethod
    def _exception_for_status(status_code: int) -> type[APIError]:
        if status_code in (401, 403):
            return AuthenticationError
        if status_code == 404:
            return NotFoundError
        if status_code == 429:
            return RateLimitError
        if status_code in (400, 422):
            return ValidationError
        return APIError

    @staticmethod
    def _add_param(params: Params, key: str, value: Optional[Union[str, int, float, bool]]) -> None:
        if value is not None:
            params[key] = value

    @staticmethod
    def _add_payload(payload: Dict[str, Any], key: str, value: Any) -> None:
        if value is not None:
            payload[key] = value

    @staticmethod
    def _stringify_bool(value: Any) -> Any:
        if isinstance(value, bool):
            return "true" if value else "false"
        return value

    @contextmanager
    def _build_files(self, files: Sequence[FileInput]) -> Iterator[List[MultipartFile]]:
        if not files:
            raise ValueError("At least one file is required")

        opened: List[Any] = []
        multipart_files: List[MultipartFile] = []
        try:
            for item in files:
                if isinstance(item, (str, Path)):
                    path = Path(item)
                    fp = path.open("rb")
                    opened.append(fp)
                    multipart_files.append(("files", (path.name, fp)))
                    continue

                filename = item[0]
                fp = item[1]
                if len(item) == 3:
                    content_type = item[2]
                    multipart_files.append(("files", (filename, fp, content_type)))
                else:
                    multipart_files.append(("files", (filename, fp)))
            yield multipart_files
        finally:
            for fp in opened:
                fp.close()
