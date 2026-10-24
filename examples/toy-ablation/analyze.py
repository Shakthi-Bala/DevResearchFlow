"""Independently recompute the expected error for this fixed demonstration."""

import json
from pathlib import Path

metrics = json.loads(Path("runs/RUN-002/metrics.json").read_text())
data = json.loads(Path("configs/dataset.json").read_text())
expected = sum(value * value for value in data["x"]) / len(data["x"])
assert metrics == {"baseline_mse": 0.0, "ablated_mse": expected, "difference": expected}
print("Recomputed expected MSE: (1+4+9+16)/4 = 7.5")
