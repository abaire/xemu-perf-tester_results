from __future__ import annotations

# ruff: noqa: PLR2004 Magic value used in comparison
import glob
import json
import os
from typing import Any


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


def load_results(results_dirs: list[str]) -> list[dict[str, Any]]:
    """Loads benchmark result JSON files from the given directories."""
    results = []

    for results_dir in results_dirs:
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
