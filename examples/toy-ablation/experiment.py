"""Tiny deterministic ablation; the runner captures execution and evidence."""

import argparse
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail", action="store_true")
    args = parser.parse_args()
    print("Evaluating deterministic synthetic points", flush=True)
    if args.fail:
        raise SystemExit("Injected demonstration failure before metrics")
    data = json.loads(Path("configs/dataset.json").read_text())
    config = json.loads(Path("configs/ablation.json").read_text())
    x, y = data["x"], data["y"]
    baseline = sum((config["baseline_slope"] * v - t) ** 2 for v, t in zip(x, y)) / len(x)
    ablated = sum((config["ablated_slope"] * v - t) ** 2 for v, t in zip(x, y)) / len(x)
    metrics = {"baseline_mse": baseline, "ablated_mse": ablated, "difference": ablated - baseline}
    (Path(os.environ["DRF_RUN_DIR"]) / "metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
