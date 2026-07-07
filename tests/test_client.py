import json
from pathlib import Path

import httpx
import pytest

from verdikta_sdk import (
    AuthenticationError,
    NetworkError,
    NotFoundError,
    ValidationError,
    VerdiktaClient,
)


BASE_URL = "https://bounties.verdikta.org/api/"


def make_client(handler, api_key="test-key"):
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url=BASE_URL)
    return VerdiktaClient(api_key=api_key, http_client=http_client)


def test_list_jobs_sends_filters_and_api_key():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = request.headers
        seen["url"] = request.url
        return httpx.Response(200, json={"jobs": [{"id": 1, "title": "SDK bounty"}]})

    client = make_client(handler)
    response = client.list_jobs(
        status="OPEN",
        work_product_type=["code", "writing"],
        min_hours_left=3,
        min_bounty_usd=5,
        has_winner=False,
        search="sdk",
        limit=25,
        offset=10,
    )

    assert response["jobs"][0]["title"] == "SDK bounty"
    assert seen["headers"]["X-Bot-API-Key"] == "test-key"
    query = dict(seen["url"].params)
    assert query["status"] == "OPEN"
    assert query["workProductType"] == "code,writing"
    assert query["minHoursLeft"] == "3"
    assert query["minBountyUSD"] == "5"
    assert query["hasWinner"] == "false"
    assert query["search"] == "sdk"
    assert query["limit"] == "25"
    assert query["offset"] == "10"


def test_get_job_include_rubric():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["query"] = dict(request.url.params)
        return httpx.Response(200, json={"id": 7, "rubric": {"criteria": []}})

    client = make_client(handler)
    response = client.get_job(7, include_rubric=True)

    assert response["id"] == 7
    assert seen["path"] == "/api/jobs/7"
    assert seen["query"]["includeRubric"] == "true"


@pytest.mark.parametrize(
    "status_code,exc_type",
    [
        (400, ValidationError),
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, NotFoundError),
    ],
)
def test_error_mapping(status_code, exc_type):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "bad things happened"})

    client = make_client(handler)

    with pytest.raises(exc_type) as caught:
        client.get_job(999)

    assert "bad things happened" in str(caught.value)
    assert caught.value.status_code == status_code
    assert caught.value.payload["error"] == "bad things happened"


def test_network_error_is_wrapped():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    client = make_client(handler)

    with pytest.raises(NetworkError) as caught:
        client.list_jobs()

    assert "Could not reach Verdikta API" in str(caught.value)


def test_dry_run_submission_sends_multipart(tmp_path: Path):
    file_path = tmp_path / "submission.md"
    file_path.write_text("# hello", encoding="utf-8")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        seen["content_type"] = request.headers["content-type"]
        seen["body"] = body
        return httpx.Response(200, json={"valid": True})

    client = make_client(handler)
    response = client.dry_run_submission(123, files=[file_path], hunter="0x0000000000000000000000000000000000000001")

    assert response["valid"] is True
    assert "multipart/form-data" in seen["content_type"]
    assert b'name="hunter"' in seen["body"]
    assert b'0x0000000000000000000000000000000000000001' in seen["body"]
    assert b'filename="submission.md"' in seen["body"]
    assert b"# hello" in seen["body"]


def test_upload_submission_sends_file_descriptions_json(tmp_path: Path):
    file_path = tmp_path / "work.py"
    file_path.write_text("print('ok')", encoding="utf-8")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.read()
        return httpx.Response(
            200,
            json={
                "success": True,
                "submission": {"hunterCid": "bafy-example", "fileCount": 1},
            },
        )

    client = make_client(handler)
    response = client.upload_submission(
        123,
        files=[file_path],
        hunter="0x0000000000000000000000000000000000000001",
        submission_narrative="short note",
        file_descriptions={"work.py": "source code"},
    )

    assert response["submission"]["hunterCid"] == "bafy-example"
    assert b'name="submissionNarrative"' in seen["body"]
    assert b"short note" in seen["body"]
    assert b'name="fileDescriptions"' in seen["body"]
    assert json.dumps({"work.py": "source code"}).encode() in seen["body"]


def test_lookup_job_requires_exactly_one_identifier():
    client = make_client(lambda request: httpx.Response(200, json={}))

    with pytest.raises(ValueError):
        client.lookup_job()

    with pytest.raises(ValueError):
        client.lookup_job(bounty_id=1, tx_hash="0xabc")
