#!/usr/bin/env python3

# ruff: noqa: T201 `print` found
# ruff: noqa: PLR2004 Magic value used in comparison

from __future__ import annotations

import argparse
import glob
import importlib.resources as pkg_resources
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

_TREND_MIN_CHANGE_PERCENTAGE = 0.08

# Keep in sync with script
_NO_TREND = "N"
_STABLE_TREND = "S"
_IMPROVING_TREND = "I"
_WORSENING_TREND = "W"


class FlatResults:
    def __init__(self, flat_results: list[dict[str, Any]]):
        def _patch_gpu_renderer(gpu: str, cpu: str) -> str:
            """Replace generic integrated graphics messages with CPU info."""
            return cpu if gpu == "AMD Radeon (TM) Graphics" else gpu

        self.flattened_results = []
        for result in flat_results:
            machine_info = result["machine_info"]
            for test_result in result.get("results", []):
                iterations = test_result["iterations"]
                max_us = test_result["max_us"]
                total_us = test_result["total_us"]
                average_us = test_result["average_us"]
                average_excluiding_max = (total_us - max_us) / (iterations - 1) if iterations > 1 else average_us

                flattened = {
                    "suite": test_result["name"].split("::")[0] if "::" in test_result["name"] else "N/A",
                    "test_name": test_result["name"],
                    "average_us": average_us,
                    "average_us_exmax": average_excluiding_max,
                    "total_us": total_us,
                    "max_us": max_us,
                    "min_us": test_result["min_us"],
                    "iterations": iterations,
                    "xemu_version": result["xemu_version"],
                    "renderer": result["renderer"],
                    "iso": result["iso"],
                    "os_system": machine_info["os_system"],
                    "cpu_manufacturer": machine_info["cpu_manufacturer"],
                    "cpu_freq_max": machine_info["cpu_freq_max"],
                    "gpu_vendor": result["gpu_vendor"],
                    "gpu_renderer": _patch_gpu_renderer(result["gpu_renderer"], machine_info["cpu_manufacturer"]),
                    "machine_id": result["machine_id"],
                    "machine_id_with_renderer": result["machine_id_with_renderer"],
                }

                raw_results = sorted(test_result.get("raw_results", []))
                if raw_results and len(raw_results) > 3:
                    flattened["inner_max_us"] = raw_results[-2]
                    flattened["inner_min_us"] = raw_results[1]

                self.flattened_results.append(flattened)

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

    def render(self, output_dir: str, html_file_name: str):
        env = _get_jinja2_env()

        os.makedirs(output_dir, exist_ok=True)

        template_context = {
            "title": "xemu perf tester results",
            "results_data": self.flattened_results,
        }

        template = env.get_template("report_template.html.jinja2")
        html_output = template.render(template_context)
        with open(os.path.join(output_dir, html_file_name), "w", encoding="utf-8") as f:
            f.write(html_output)

        css_template = env.get_template("style.css.jinja2")
        with open(os.path.join(output_dir, "style.css"), "w", encoding="utf-8") as f:
            f.write(css_template.render(template_context))

        js_template = env.get_template("script.js.jinja2")
        with open(os.path.join(output_dir, "script.js"), "w", encoding="utf-8") as f:
            f.write(js_template.render(template_context))

        logger.debug("Generated HTML report into '%s'", output_dir)


def _get_jinja2_env() -> Environment:
    try:
        template_dir_path = pkg_resources.files("xemu_perf_renderer") / "templates"
    except ModuleNotFoundError:
        script_dir = Path(__file__).parent
        template_dir_path = script_dir / "templates"

    return Environment(loader=FileSystemLoader(str(template_dir_path)), autoescape=True)


def _expand_gpu_info(result: dict[str, Any]):
    result["gpu_vendor"] = None
    result["gpu_renderer"] = None
    result["gpu_gl_version"] = None
    result["gpu_glsl_version"] = None

    for line in result["xemu_machine_info"].splitlines():
        entry = line.split(": ", maxsplit=1)
        if len(entry) != 2:
            continue

        key, value = entry
        if key == "GL_VENDOR":
            result["gpu_vendor"] = value
        elif key == "GL_RENDERER":
            result["gpu_renderer"] = value
        elif key == "GL_VERSION":
            result["gpu_gl_version"] = value
        elif key == "GL_SHADING_LANGUAGE_VERSION":
            result["gpu_glsl_version"] = value


def load_results(results_dir: str) -> list[dict[str, Any]]:
    results_dir = os.path.abspath(os.path.expanduser(results_dir))

    results = []
    for result_file in glob.glob("**/*.json", root_dir=results_dir, recursive=True):
        with open(os.path.join(results_dir, result_file), "rb") as infile:
            result = json.load(infile)
            _expand_gpu_info(result)
            # The stable machine ID + renderer backend is the json file without the ".json"
            result["machine_id_with_renderer"] = os.path.basename(result_file)[:-5]
            # The renderer backend is one of "-GL" or "-VK"
            result["machine_id"] = os.path.basename(result_file)[:-8]
            results.append(result)

    return results


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
        help="Path to the root of the results to process.",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    if not os.path.isdir(args.results):
        logger.error("Results directory '%s' does not exist", args.results)
        return 1

    results = FlatResults(load_results(args.results))

    output_dir = os.path.abspath(os.path.expanduser(args.output_dir))
    results.render(output_dir, args.output_html)

    return 0


if __name__ == "__main__":
    sys.exit(entrypoint())
