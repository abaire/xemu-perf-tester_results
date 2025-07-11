from __future__ import annotations

# ruff: noqa: PLR2004 Magic value used in comparison
import glob
import json
import os
import re
from enum import StrEnum
from typing import Any

_XEMU_VERSION_CAPTURE = r"(\d+)\.(\d+)\.(\d+)"
# xemu-0.8.92-master-<githash>
# xemu-0.8.53-master-5685a6290cfbf7b022ec5e58a8ffb09f664c04e8
_XEMU_RELEASE_VERSION_RE = re.compile(r"xemu-" + _XEMU_VERSION_CAPTURE + r"-master-(.*)")

# xemu-0.8.92-6-gdf22bfacd8- -df22bfacd83f6256f0fe52adfc3eb3cb7e3a4f54
# xemu-0.8.92-<build>-g<shorthash>-<branch_name>-<githash>
# xemu-0.8.53-4-g90cfbf-fix_something-90cfbf022ec5e58a8ffb09f664
_XEMU_DEV_OR_PR_VERSION_RE = re.compile(r"xemu-" + _XEMU_VERSION_CAPTURE + r"-(\d+)-g[^-]+-([^-]+)-(.*)")

# xemu-0.0.0- -0c24cf3a07ee3962c8d099dc281043eefc8dcf65
_XEMU_FORK_PR_RE = re.compile(r"xemu-" + _XEMU_VERSION_CAPTURE + r"-\s+-(.*)")


class XemuVersionType(StrEnum):
    RELEASE = "release"
    DEV_OR_PR = "dev_pr"
    FORK = "fork"


_XEMU_RELEASE_SPECIAL_CASES = {
    "xemu-0.8.0- -b6d6a4709d7563a0cc03a06cd80f7107b54a52e2": (
        0,
        8,
        0,
        None,
        None,
        "b6d6a4709d7563a0cc03a06cd80f7107b54a52e2",
        XemuVersionType.RELEASE,
    ),
}


class XemuVersion:
    """Parses xemu version strings into semantic versions."""

    def __init__(self, version_string: str):
        self.major: int
        self.minor: int
        self.patch: int
        self.build: int | None
        self.branch: str | None
        self.git_hash: str
        self.type: XemuVersionType

        self._parse_version(version_string)

        self.short_name: str
        self.compare_name: str

        self._build_special_names()

    def to_object(self) -> dict[str, Any]:
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "build": self.build,
            "branch": self.branch,
            "hash": self.git_hash,
            "type": str(self.type),
            "short": self.short_name,
            "compare": self.compare_name,
        }

    def _build_special_names(self):
        if self.type == XemuVersionType.RELEASE:
            self.short_name = f"{self.major}.{self.minor}.{self.patch}"
            self.compare_name = f"{self.major:06d}.{self.minor:06d}.{self.patch:06d}"
            return

        if self.type == XemuVersionType.DEV_OR_PR:
            self.short_name = f"{self.major}.{self.minor}.{self.patch}-{self.build}-{self.branch}"
            self.compare_name = f"{self.major:06d}.{self.minor:06d}.{self.patch:06d}.{self.build:06d}-{self.branch}"
            return

        if self.type == XemuVersionType.FORK:
            self.short_name = f"fork-{self.git_hash}"
            self.compare_name = self.short_name
            return

        msg = f"No special name converter for version type f{self.type}"
        raise NotImplementedError(msg)

    def _parse_version(self, version_string: str):
        special_case = _XEMU_RELEASE_SPECIAL_CASES.get(version_string)
        if special_case:
            self.major, self.minor, self.patch, self.build, self.branch, self.git_hash, self.type = special_case
            return

        match = _XEMU_RELEASE_VERSION_RE.match(version_string)
        if match:
            self.major = int(match.group(1))
            self.minor = int(match.group(2))
            self.patch = int(match.group(3))
            self.build = None
            self.branch = None
            self.git_hash = match.group(4)
            self.type = XemuVersionType.RELEASE
            return

        match = _XEMU_DEV_OR_PR_VERSION_RE.match(version_string)
        if match:
            self.major = int(match.group(1))
            self.minor = int(match.group(2))
            self.patch = int(match.group(3))
            self.build = int(match.group(4))
            self.branch = match.group(5)
            self.git_hash = match.group(6)
            self.type = XemuVersionType.DEV_OR_PR
            return

        match = _XEMU_FORK_PR_RE.match(version_string)
        if match:
            self.major = int(match.group(1))
            self.minor = int(match.group(2))
            self.patch = int(match.group(3))
            self.build = 0
            self.branch = "Unofficial"
            self.git_hash = match.group(4)
            self.type = XemuVersionType.FORK
            return

        msg = f"Failed to parse xemu version string '{version_string}'"
        raise ValueError(msg)


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
                min_us = test_result["min_us"]
                total_us = test_result["total_us"]
                average_us = test_result["average_us"]

                average_excluding_max = (total_us - max_us) / (iterations - 1) if iterations > 1 else average_us
                error_plus_us = max_us - average_us
                error_minus_us = average_us - min_us

                xemu_tag: str = result.get("xemu_tag", "")
                if xemu_tag:
                    xemu_tag = xemu_tag.removeprefix("https://github.com/")

                version = result["xemu_version"]
                xemu_version_obj = XemuVersion(version)

                flattened = {
                    "suite": test_result["name"].split("::")[0] if "::" in test_result["name"] else "N/A",
                    "test_name": test_result["name"],
                    "average_us": average_us,
                    "total_us": total_us,
                    "max_us": max_us,
                    "min_us": min_us,
                    "error_plus_us": error_plus_us,
                    "error_minus_us": error_minus_us,
                    "average_us_exmax": average_excluding_max,
                    "iterations": iterations,
                    "xemu_version": version,
                    "xemu_version_obj": xemu_version_obj.to_object(),
                    "xemu_tag": xemu_tag,
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
                    inner_max_us = raw_results[-2]
                    inner_min_us = raw_results[1]
                    average_excluding_outliers = (total_us - max_us - min_us) / (iterations - 2)

                    flattened["inner_max_us"] = inner_max_us
                    flattened["inner_min_us"] = inner_min_us
                    flattened["inner_average_us"] = average_excluding_outliers

                    flattened["error_plus_inner_us"] = inner_max_us - average_excluding_outliers
                    flattened["error_minus_inner_us"] = average_excluding_outliers - inner_min_us

                    flattened["error_plus_us_exmax"] = inner_max_us - average_excluding_max

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
