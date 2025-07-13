#!/usr/bin/env python3

# ruff: noqa: T201 `print` found
# ruff: noqa: PLR2004 Magic value used in comparison

from __future__ import annotations

import argparse
import gzip
import importlib.resources as pkg_resources
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from xemu_perf_renderer.util.data import FlatResults, load_results
from xemu_perf_renderer.util.test_suite_descriptor_loader import TestSuiteDescriptor, TestSuiteDescriptorLoader

logger = logging.getLogger(__name__)

_TREND_MIN_CHANGE_PERCENTAGE = 0.08

# Keep in sync with script
_NO_TREND = "N"
_STABLE_TREND = "S"
_IMPROVING_TREND = "I"
_WORSENING_TREND = "W"


def _flatten_test_suite_descriptor(
    test_suite_descriptor: TestSuiteDescriptor, source_repo_url_prefix: str | None
) -> dict[str, Any]:
    ret = {
        "class_name": test_suite_descriptor.class_name,
        "description": test_suite_descriptor.description,
        "tests": test_suite_descriptor.test_descriptions,
    }

    if source_repo_url_prefix:
        ret["source_file"] = f"{source_repo_url_prefix}/{test_suite_descriptor.source_file}"
    return ret


class FlatResultsRenderer(FlatResults):
    def __init__(self, flat_results: list[dict[str, Any]]):
        super().__init__(flat_results)
        self.analyze()

    def _calculate_slope(self, points: list[tuple[int, float]]) -> float:
        """Calculates the slope of the line of best fit for a set of points."""
        n = len(points)
        if n < 2:
            return 0.0

        sum_x = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        sum_xy = sum(p[0] * p[1] for p in points)
        sum_x_squared = sum(p[0] ** 2 for p in points)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = n * sum_x_squared - sum_x**2

        return numerator / denominator if denominator != 0 else 0.0

    def analyze(self):
        grouped_by_test_and_machine = defaultdict(list)
        for entry in self.flattened_results:
            key = (entry["test_name"], entry["machine_id_with_renderer"])
            grouped_by_test_and_machine[key].append(entry)

        for data_points in grouped_by_test_and_machine.values():
            if len(data_points) < 3:
                continue

            data_points.sort(key=lambda entry: entry["xemu_version"])
            regression_points = [(idx, entry["average_us_exmax"]) for idx, entry in enumerate(data_points)]
            slope = self._calculate_slope(regression_points)

            average_y = sum(p[1] for p in regression_points) / len(regression_points)
            threshold = average_y * _TREND_MIN_CHANGE_PERCENTAGE

            trend = _STABLE_TREND
            if slope > threshold:
                trend = _WORSENING_TREND
            elif slope < -threshold:
                trend = _IMPROVING_TREND

            for entry in data_points:
                entry["trend"] = trend

        for entry in self.flattened_results:
            if "trend" not in entry:
                entry["trend"] = _NO_TREND

    def render(
        self,
        output_dir: str,
        html_file_name: str,
        *,
        local_site_mode: bool = False,
        test_suite_descriptors: dict[str, Any] | None = None,
        source_repo_url_prefix: str | None = None,
    ):
        env = _get_jinja2_env()

        if test_suite_descriptors is None:
            test_suite_descriptors = {}

        os.makedirs(output_dir, exist_ok=True)

        results_data = {
            "results": self.flattened_results,
            "tags": self.friendly_names,
        }

        if local_site_mode:
            results_filename = "results.json"
            results_path = os.path.join(output_dir, results_filename)
            with open(results_path, "w", encoding="utf-8") as outfile:
                json.dump(results_data, outfile, indent=2)
        else:
            results_filename = "results.json.gz"
            results_path = os.path.join(output_dir, results_filename)
            with gzip.open(results_path, "wt", encoding="utf-8") as outfile:
                json.dump(results_data, outfile, indent=2)

        template_context = {
            "title": "xemu perf tester results",
            "results_filename": results_filename,
            "test_suite_descriptors": {
                key: _flatten_test_suite_descriptor(value, source_repo_url_prefix)
                for key, value in test_suite_descriptors.items()
            },
        }

        template = env.get_template("report_template.html.jinja2")
        html_output = template.render(template_context)
        with open(os.path.join(output_dir, html_file_name), "w", encoding="utf-8") as f:
            f.write(html_output)

        css_template = env.get_template("style.css.jinja2")
        with open(os.path.join(output_dir, "style.css"), "w", encoding="utf-8") as f:
            f.write(css_template.render(template_context))

        for js_template_file in ("script",):
            js_template = env.get_template(f"{js_template_file}.js.jinja2")
            with open(os.path.join(output_dir, f"{js_template_file}.js"), "w", encoding="utf-8") as f:
                f.write(js_template.render(template_context))

        # TODO: Just copy the files directly instead of nop rendering.
        for js_file in ("app", "data", "xemu_version"):
            js_template = env.get_template(f"{js_file}.js")
            with open(os.path.join(output_dir, f"{js_file}.js"), "w", encoding="utf-8") as f:
                f.write(js_template.render({}))

        logger.debug("Generated HTML report into '%s'", output_dir)


def _get_jinja2_env() -> Environment:
    try:
        template_dir_path = pkg_resources.files("xemu_perf_renderer") / "templates"
    except ModuleNotFoundError:
        script_dir = Path(__file__).parent
        template_dir_path = script_dir / "templates"

    return Environment(loader=FileSystemLoader(str(template_dir_path)), autoescape=True)


def entrypoint():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        "-v",
        help="Enables verbose logging information",
        action="store_true",
    )
    parser.add_argument("--output-dir", "-o", default=".", help="Directory into which site files will be generated")
    parser.add_argument("--output-html", default="index.html", help="Name of the HTML file to generate")
    parser.add_argument(
        "results",
        nargs="+",
        help="Path to the root of the results to process.",
    )
    parser.add_argument(
        "--local_site_mode",
        "-L",
        action="store_true",
        help="Emit artifacts suitable for running locally without a webserver",
    )
    parser.add_argument(
        "--test-descriptor-registry-url",
        default="https://raw.githubusercontent.com/abaire/xemu-perf-tests/pages_doxygen/xml/tests_registry.json",
        help="URL at which the JSON test suite registry describing tests may be publicly accessed.",
    )
    parser.add_argument(
        "--test-source-url-prefix",
        default="https://github.com/abaire/xemu-perf-tests/blob/main",
        help="URL at which the test suite source files may be accessed.",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    result_paths = [os.path.abspath(os.path.expanduser(p)) for p in args.results]
    for path in result_paths:
        if not os.path.isdir(path):
            logger.error("Results directory '%s' does not exist", path)
            return 1

    test_suite_descriptors = (
        TestSuiteDescriptorLoader(args.test_descriptor_registry_url).process()
        if args.test_descriptor_registry_url
        else {}
    )

    results = FlatResultsRenderer(load_results(result_paths))

    output_dir = os.path.abspath(os.path.expanduser(args.output_dir))
    results.render(
        output_dir,
        args.output_html,
        local_site_mode=args.local_site_mode,
        test_suite_descriptors=test_suite_descriptors,
        source_repo_url_prefix=args.test_source_url_prefix,
    )

    return 0


if __name__ == "__main__":
    sys.exit(entrypoint())
