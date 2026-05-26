"""CLI entrypoint for all seeders.

Usage:
    python -m backend.scripts.seed_all all
    python -m backend.scripts.seed_all periods regions ports
    python -m backend.scripts.seed_all countries   # downloads Natural Earth
"""
from __future__ import annotations

import argparse
import logging

from backend.scripts.seed import (
    countries, gubernias, intra_imperial, ports,
    temporal_labels, umbrella_regions,
)


SEEDERS = {
    "temporal": temporal_labels.run,
    "regions": umbrella_regions.run,
    "gubernias": gubernias.run,
    "intra_imperial": intra_imperial.run,
    "ports": ports.run,
    "countries": countries.run,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "targets",
        nargs="+",
        choices=["all", *SEEDERS.keys()],
        help="Which seeders to run.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    targets = list(SEEDERS) if "all" in args.targets else args.targets
    for name in targets:
        logging.info("=== running seeder: %s ===", name)
        SEEDERS[name]()


if __name__ == "__main__":
    main()
