#!/usr/bin/env python3

# ruff: noqa: T201 `print` found

from __future__ import annotations

import argparse
import glob
import importlib.resources as pkg_resources
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class FlatResults:
    def __init__(self, flat_results: list[dict[str, Any]]):
        self.flat_results = flat_results

        self.flattened_results = []
        for result in flat_results:
            machine_info = result["machine_info"]
            for test_result in result.get("results", []):
                self.flattened_results.append(
                    {
                        "suite": test_result["name"].split("::")[0] if "::" in test_result["name"] else "N/A",
                        "test_name": test_result["name"],
                        "average_us": test_result["average_us"],
                        "total_us": test_result["total_us"],
                        "max_us": test_result["max_us"],
                        "min_us": test_result["min_us"],
                        "iterations": test_result["iterations"],
                        "xemu_version": result["xemu_version"],
                        "renderer": result["renderer"],
                        "iso": result["iso"],
                        "os_system": machine_info["os_system"],
                        "cpu_manufacturer": machine_info["cpu_manufacturer"],
                        "gpu_vendor": result["gpu_vendor"],
                        "gpu_renderer": result["gpu_renderer"],
                    }
                )

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
        key, value = line.split(": ", maxsplit=1)
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
