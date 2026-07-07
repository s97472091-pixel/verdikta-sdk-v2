"""Validate and upload work, then request Verdikta calldata for submission.

This example intentionally does not broadcast blockchain transactions. Verdikta
returns transaction objects with `to`, `data`, `value`, and `chainId`; sign and
broadcast them with your wallet tooling.

Usage:
    export VERDIKTA_API_KEY="your-bot-api-key"
    python examples/submit_work.py 123 0xYourHunterWallet ./submission.md
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from verdikta_sdk import ValidationError, VerdiktaClient


def _hunter_cid(upload_response: Dict[str, Any]) -> str:
    submission = upload_response.get("submission", {})
    cid = submission.get("hunterCid") or upload_response.get("hunterCid")
    if not cid:
        raise RuntimeError(f"Could not find hunterCid in response: {upload_response}")
    return str(cid)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_id", help="Verdikta job/bounty id")
    parser.add_argument("hunter", help="0x hunter wallet address")
    parser.add_argument("files", nargs="+", type=Path, help="Submission files")
    parser.add_argument("--narrative", default="Submitted through verdikta-sdk-python")
    args = parser.parse_args()

    with VerdiktaClient.from_env() as client:
        try:
            dry_run = client.dry_run_submission(args.job_id, files=args.files, hunter=args.hunter)
        except ValidationError as exc:
            print("Dry-run failed. Fix these issues before submitting:")
            print(json.dumps(exc.payload, indent=2))
            raise SystemExit(1)

        print("Dry-run response:")
        print(json.dumps(dry_run, indent=2))

        upload = client.upload_submission(
            args.job_id,
            files=args.files,
            hunter=args.hunter,
            submission_narrative=args.narrative,
            file_descriptions={path.name: "Work product file" for path in args.files},
        )
        hunter_cid = _hunter_cid(upload)
        print(f"Uploaded files. hunterCid={hunter_cid}")

        bundle = client.create_submission_bundle(
            args.job_id,
            hunter_address=args.hunter,
            hunter_cid=hunter_cid,
        )
        print("Next transaction bundle to sign/broadcast:")
        print(json.dumps(bundle, indent=2))


if __name__ == "__main__":
    main()
