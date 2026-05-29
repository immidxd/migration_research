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
    ah_crownlands, cities, countries, fix_ukr_gubernia_geom, gubernias, hawaii,
    hierarchy, intra_imperial, manchuria, ports, ri_1897, subdivisions,
    temporal_labels, treadgold_regions, ukr_aliases, umbrella_regions,
    zakarpattia,
)


SEEDERS = {
    "temporal": temporal_labels.run,
    "regions": umbrella_regions.run,
    "treadgold": treadgold_regions.run,
    "gubernias": gubernias.run,           # hand-drawn placeholders
    "ri_1897": ri_1897.run,               # real RiStat boundaries (preferred)
    "intra_imperial": intra_imperial.run,
    "ports": ports.run,
    "countries": countries.run,
    "subdivisions": subdivisions.run,     # US states + Canadian provinces (NE admin_1)
    "cities": cities.run,                 # key North American diaspora cities
    "manchuria": manchuria.run,           # CHGIS 1911 Three Eastern Provinces (local file)
    "hawaii": hawaii.run,                 # worked example: time-varying territory status
    "hierarchy": hierarchy.run,           # populate territories.parent_id (place tree)
    "ah_crownlands": ah_crownlands.run,   # real Galicia/Bukovina boundaries (HistoGIS 1910)
    "zakarpattia": zakarpattia.run,       # Transcarpathia = union of Hungarian komitats (HistoGIS 1835)
    "fix_ukr_gubernia_geom": fix_ukr_gubernia_geom.run,  # real Podilia/Volyn geom + rebuild umbrellas
    "ukr_aliases": ukr_aliases.run,       # UK/EN aliases for Ukrainian gubernias (multilingual search)
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
