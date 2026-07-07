"""Monitor Verdikta submission status and fetch evaluation results.

Usage:
    export VERDIKTA_API_KEY="your-bot-api-key"
    python examples/monitor_evaluation.py 123 --submission-id 4
"""

import argparse
import json
import time
from typing import Any, Dict, Iterable, Optional

from verdikta_sdk import APIError, NotFoundError, ValidationError, VerdiktaClient

TERMINAL_STATUSES = {"APPROVED", "REJECTED", "ACCEPTED_PENDING_CLAIM", "REJECTED_PENDING_FINALIZATION"}


def _submissions_from_response(response: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    if isinstance(response.get("submissions"), list):
        return response["submissions"]
    if isinstance(response.get("data"), list):
        return response["data"]
    if isinstance(response.get("results"), list):
        return response["results"]
    return []


def _find_submission(response: Dict[str, Any], submission_id: Optional[str]) -> Optional[Dict[str, Any]]:
    submissions = list(_submissions_from_response(response))
    if not submissions:
        return None
    if submission_id is None:
        return submissions[-1]
    for sub in submissions:
        current_id = str(sub.get("id") or sub.get("submissionId") or sub.get("subId"))
        if current_id == str(submission_id):
            return sub
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_id")
    parser.add_argument("--submission-id", default=None)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--max-polls", type=int, default=20)
    args = parser.parse_args()

    with VerdiktaClient.from_env() as client:
        for attempt in range(1, args.max_polls + 1):
            response = client.list_submissions(args.job_id)
            submission = _find_submission(response, args.submission_id)
            if submission is None:
                print("No matching submission found yet.")
            else:
                sub_id = submission.get("id") or submission.get("submissionId") or submission.get("subId")
                status = submission.get("status")
                print(f"Poll {attempt}: submission #{sub_id} status={status}")

                if str(status) in TERMINAL_STATUSES:
                    try:
                        evaluation = client.get_submission_evaluation(args.job_id, sub_id)
                        print(json.dumps(evaluation, indent=2))
                    except (NotFoundError, ValidationError, APIError) as exc:
                        print(f"Evaluation endpoint is not ready or not available yet: {exc}")
                    return

            if attempt < args.max_polls:
                time.sleep(args.poll_seconds)

    raise SystemExit("Timed out while waiting for a terminal status")


if __name__ == "__main__":
    main()
