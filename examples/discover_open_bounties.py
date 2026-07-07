"""Discover open Verdikta bounties with filtering.

Usage:
    export VERDIKTA_API_KEY="your-bot-api-key"  # optional for public listing
    python examples/discover_open_bounties.py --min-usd 5 --type code --search sdk
"""

import argparse
from typing import Any, Dict, Iterable

from verdikta_sdk import VerdiktaClient


def _jobs_from_response(response: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    # Verdikta may return either {jobs: [...]} or a direct list under another key.
    if isinstance(response.get("jobs"), list):
        return response["jobs"]
    if isinstance(response.get("data"), list):
        return response["data"]
    if isinstance(response.get("results"), list):
        return response["results"]
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-usd", type=float, default=None, help="Minimum bounty USD value")
    parser.add_argument("--max-usd", type=float, default=None, help="Maximum bounty USD value")
    parser.add_argument("--min-hours-left", type=int, default=1, help="Minimum hours until deadline")
    parser.add_argument("--type", default=None, help="code, writing, research, or comma-separated values")
    parser.add_argument("--search", default=None, help="Keyword search")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    work_product_type = args.type.split(",") if args.type and "," in args.type else args.type

    with VerdiktaClient.from_env() as client:
        response = client.list_open_bounties(
            work_product_type=work_product_type,
            min_hours_left=args.min_hours_left,
            min_bounty_usd=args.min_usd,
            max_bounty_usd=args.max_usd,
            search=args.search,
            limit=args.limit,
        )

    for job in _jobs_from_response(response):
        job_id = job.get("id") or job.get("jobId") or job.get("bountyId")
        title = job.get("title", "Untitled bounty")
        reward = job.get("bountyUSD") or job.get("payoutUSD") or job.get("reward") or "unknown reward"
        deadline = job.get("deadline") or job.get("submissionDeadline") or "unknown deadline"
        print(f"#{job_id}: {title} | reward={reward} | deadline={deadline}")


if __name__ == "__main__":
    main()
