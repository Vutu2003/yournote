"""Phase 09 fixtures for a controlled reading-workflow comparison."""

import json
from pathlib import Path


def load_scenarios():
    return json.loads(Path(__file__).with_name("scenarios.json").read_bytes())
