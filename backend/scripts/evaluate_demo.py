import argparse
import json
from pathlib import Path

from app.services.evaluation import evaluate_dataset, load_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate AI Search demo predictions.")
    parser.add_argument(
        "--cases",
        default="evals/demo_cases.json",
        help="Path to evaluation cases JSON.",
    )
    parser.add_argument(
        "--predictions",
        default="evals/sample_predictions.json",
        help="Path to predictions JSON.",
    )
    args = parser.parse_args()

    cases = load_json(Path(args.cases))
    predictions = load_json(Path(args.predictions))
    report = evaluate_dataset(cases, predictions)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
