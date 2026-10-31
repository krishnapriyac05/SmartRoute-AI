"""Compare two deterministic generator runs by exported-file checksum."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from backend.generator.generate import DEFAULT_SEED, generate


def verify(profile: str = "starter", seed: int = DEFAULT_SEED) -> bool:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        first = generate(profile, root / "first.db", root / "first", seed)
        second = generate(profile, root / "second.db", root / "second", seed)
        return first["files"] == second["files"] and first["counts"] == second["counts"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("starter", "full"), default="starter")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    if not verify(args.profile, args.seed):
        raise SystemExit("Reproducibility check failed")
    print(f"Reproducibility check passed: profile={args.profile}, seed={args.seed}")


if __name__ == "__main__":
    main()

