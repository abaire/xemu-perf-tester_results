"""Generates pages comparing development (PR/CI build) results against their base xemu release."""

from __future__ import annotations

import json
import logging
import math
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from xemu_perf_renderer.util.data import XemuVersion, XemuVersionType, load_results

if TYPE_CHECKING:
    from jinja2 import Environment

logger = logging.getLogger(__name__)

DEFAULT_CHANGE_THRESHOLD = 0.05

_IMPROVED = "improved"
_REGRESSED = "regressed"
_UNCHANGED = "unchanged"


def _version_tuple(version: XemuVersion) -> tuple[int, int, int]:
    return version.major, version.minor, version.patch


def _parse_base_version(base_version: str | None) -> tuple[int, int, int] | None:
    if not base_version:
        return None
    try:
        major, minor, patch = (int(part) for part in base_version.split("."))
    except ValueError:
        return None
    return major, minor, patch


def _test_metric(test_result: dict[str, Any]) -> float:
    """Returns the per-test metric used for comparisons (average excluding the max outlier, matching the site)."""
    iterations = test_result["iterations"]
    if iterations > 1:
        return (test_result["total_us"] - test_result["max_us"]) / (iterations - 1)
    return float(test_result["average_us"])


def _gpu_renderer(result: dict[str, Any]) -> str:
    return result.get("gpu_renderer") or result.get("machine_info", {}).get("cpu_manufacturer", "Unknown")


@dataclass
class TestComparison:
    name: str
    baseline_us: float | None
    dev_us: float | None
    change: float | None
    status: str


@dataclass
class MachineComparison:
    machine_id_with_renderer: str
    renderer: str
    os_system: str
    cpu: str
    gpu: str
    dev_version: str
    baseline_version: str | None
    baseline_note: str | None
    tests: list[TestComparison] = field(default_factory=list)

    @property
    def improved(self) -> int:
        return sum(1 for test in self.tests if test.status == _IMPROVED)

    @property
    def regressed(self) -> int:
        return sum(1 for test in self.tests if test.status == _REGRESSED)

    @property
    def geomean_change(self) -> float | None:
        ratios = [
            test.dev_us / test.baseline_us
            for test in self.tests
            if test.baseline_us and test.dev_us and test.baseline_us > 0 and test.dev_us > 0
        ]
        if not ratios:
            return None
        return math.exp(sum(math.log(ratio) for ratio in ratios) / len(ratios)) - 1.0


@dataclass
class DevBuildComparison:
    key: str
    metadata: dict[str, Any]
    xemu_version: str
    is_current_head: bool
    machines: list[MachineComparison] = field(default_factory=list)


@dataclass
class DevResultsSet:
    key: str
    metadata: dict[str, Any]
    builds: list[DevBuildComparison] = field(default_factory=list)

    @property
    def title(self) -> str:
        if self.metadata.get("pr_number"):
            title = f"PR #{self.metadata['pr_number']}"
            if self.metadata.get("pr_title"):
                title += f": {self.metadata['pr_title']}"
            return title
        return f"CI run {self.metadata.get('run_id', self.key)}"

    @property
    def machine_count(self) -> int:
        return len({machine.machine_id_with_renderer for build in self.builds for machine in build.machines})


def _compare_tests(baseline: dict[str, Any] | None, dev: dict[str, Any], threshold: float) -> list[TestComparison]:
    baseline_tests = {test["name"]: _test_metric(test) for test in (baseline or {}).get("results", [])}
    dev_tests = {test["name"]: _test_metric(test) for test in dev.get("results", [])}

    ret = []
    for name in sorted(set(baseline_tests) | set(dev_tests)):
        baseline_us = baseline_tests.get(name)
        dev_us = dev_tests.get(name)
        change = None
        status = _UNCHANGED
        if baseline_us and dev_us is not None:
            change = (dev_us - baseline_us) / baseline_us
            if change > threshold:
                status = _REGRESSED
            elif change < -threshold:
                status = _IMPROVED
        ret.append(TestComparison(name, baseline_us, dev_us, change, status))

    def sort_key(test: TestComparison):
        # Largest regressions first, tests missing from one side last.
        return (test.change is None, -(test.change or 0.0), test.name)

    ret.sort(key=sort_key)
    return ret


def _find_baseline(
    candidates: list[dict[str, Any]], base_version: tuple[int, int, int] | None
) -> tuple[dict[str, Any] | None, str | None]:
    """Returns the baseline release result and an optional note explaining a fallback choice."""
    if not candidates:
        return None, "No release results from this machine/renderer"

    def version_of(result):
        return _version_tuple(XemuVersion.parse(result["xemu_version"]))

    ordered = sorted(candidates, key=version_of, reverse=True)
    if base_version is None:
        return ordered[0], "Base version unknown; using newest release"

    for result in ordered:
        if version_of(result) == base_version:
            return result, None
    for result in ordered:
        if version_of(result) < base_version:
            return result, f"No results for {'.'.join(map(str, base_version))}; using nearest older release"
    return None, f"No release results at or before {'.'.join(map(str, base_version))}"


def build_comparisons(
    release_results: list[dict[str, Any]], dev_results_root: str, threshold: float = DEFAULT_CHANGE_THRESHOLD
) -> list[DevResultsSet]:
    releases_by_machine: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in release_results:
        if XemuVersion.parse(result["xemu_version"]).type == XemuVersionType.RELEASE:
            releases_by_machine[result["machine_id_with_renderer"]].append(result)

    ret = []
    for key in sorted(os.listdir(dev_results_root)):
        dev_dir = os.path.join(dev_results_root, key)
        if not os.path.isdir(dev_dir):
            continue

        metadata: dict[str, Any] = {}
        metadata_file = os.path.join(dev_dir, "pr.json")
        if os.path.isfile(metadata_file):
            with open(metadata_file) as infile:
                metadata = json.load(infile)

        by_version: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for result in load_results([dev_dir]):
            by_version[result["xemu_version"]].append(result)
        if not by_version:
            continue

        results_set = DevResultsSet(key=key, metadata=metadata)
        head_sha = metadata.get("head_sha", "")
        for xemu_version, results in by_version.items():
            build_metadata = results[0].get("dev_build", {})
            base_version = _parse_base_version(build_metadata.get("base_version"))
            if base_version is None:
                base_version = _version_tuple(XemuVersion.parse(xemu_version))

            build = DevBuildComparison(
                key=key,
                metadata=build_metadata,
                xemu_version=xemu_version,
                is_current_head=bool(head_sha) and build_metadata.get("head_sha") == head_sha,
            )
            for result in sorted(results, key=lambda r: r["machine_id_with_renderer"]):
                machine_key = result["machine_id_with_renderer"]
                baseline, note = _find_baseline(releases_by_machine.get(machine_key, []), base_version)
                build.machines.append(
                    MachineComparison(
                        machine_id_with_renderer=machine_key,
                        renderer=result["renderer"],
                        os_system=result["machine_info"].get("os_system", ""),
                        cpu=result["machine_info"].get("cpu_manufacturer", ""),
                        gpu=_gpu_renderer(result),
                        dev_version=xemu_version,
                        baseline_version=baseline["xemu_version"] if baseline else None,
                        baseline_note=note,
                        tests=_compare_tests(baseline, result, threshold),
                    )
                )
            results_set.builds.append(build)

        results_set.builds.sort(key=lambda build: (not build.is_current_head, build.xemu_version))
        ret.append(results_set)

    return ret


def render_comparisons(
    env: Environment, output_dir: str, comparisons: list[DevResultsSet], threshold: float = DEFAULT_CHANGE_THRESHOLD
) -> None:
    """Renders comparison pages into output_dir/pr/."""
    pr_root = os.path.join(output_dir, "pr")
    os.makedirs(pr_root, exist_ok=True)

    page_template = env.get_template("pr_compare.html.jinja2")
    for results_set in comparisons:
        page_dir = os.path.join(pr_root, results_set.key)
        os.makedirs(page_dir, exist_ok=True)
        with open(os.path.join(page_dir, "index.html"), "w", encoding="utf-8") as outfile:
            outfile.write(page_template.render(results_set=results_set, threshold=threshold))

    index_template = env.get_template("pr_index.html.jinja2")
    with open(os.path.join(pr_root, "index.html"), "w", encoding="utf-8") as outfile:
        outfile.write(index_template.render(comparisons=comparisons, threshold=threshold))

    logger.debug("Generated %d PR comparison pages into '%s'", len(comparisons), pr_root)
