from __future__ import annotations

# ruff: noqa: T201 `print` found
# ruff: noqa: PLR2004 Magic value used in comparison
import argparse
import logging
import os
import sys

import pandas as pd

from xemu_perf_renderer.util.data import FlatResults, load_results

logger = logging.getLogger(__name__)


def rank_versions(df: pd.DataFrame) -> pd.Series:
    df["baseline_perf"] = df.groupby(["machine_id", "suite", "test_name"])["average_us_exmax"].transform("mean")
    df["normalized_perf"] = df["average_us_exmax"] / df["baseline_perf"]

    return df.groupby("xemu_version")["normalized_perf"].mean().sort_values()


def entrypoint():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        "-v",
        help="Enables verbose logging information",
        action="store_true",
    )
    parser.add_argument(
        "results",
        nargs="+",
        help="Path to the root of the results to process.",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    result_paths = [os.path.abspath(os.path.expanduser(p)) for p in args.results]
    for path in result_paths:
        if not os.path.isdir(path):
            logger.error("Results directory '%s' does not exist", path)
            return 1

    results = FlatResults(load_results(result_paths))

    try:
        performance_df = pd.DataFrame(results.flattened_results)

        version_ranking = rank_versions(performance_df.copy())
        print(version_ranking)

    except FileNotFoundError:
        print("Error: The 'perf_data' directory was not found. Please create it and add your JSON files.")

    return 0


if __name__ == "__main__":
    sys.exit(entrypoint())
