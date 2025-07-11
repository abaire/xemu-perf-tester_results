#!/usr/bin/env python3

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)

_STRIP_TESTS_REGEXES = {re.compile(r"High vertex count::MixedVtxCount-.*")}


class ActionType(Enum):
    NONE = auto()
    DELETE = auto()
    UPDATE = auto()


@dataclass
class Action:
    action: ActionType = ActionType.NONE
    content: dict[str, Any] | None = None


def _clean_data(content: dict[str, Any]) -> Action:
    results_to_strip = []

    all_results = content.get("results", [])
    for index, result in enumerate(all_results):
        if any(regex.match(result["name"]) for regex in _STRIP_TESTS_REGEXES):
            results_to_strip.append(index)
            continue

    if not results_to_strip:
        return Action()

    for index in reversed(results_to_strip):
        all_results.pop(index)

    content["results"] = all_results

    return Action(action=ActionType.UPDATE, content=content)


def entrypoint():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "results",
        nargs="+",
        help="Path to the root of the results to process.",
    )

    args = parser.parse_args()
    result_paths = [os.path.abspath(os.path.expanduser(p)) for p in args.results]
    for results_dir in result_paths:
        if not os.path.isdir(results_dir):
            logger.error("Results directory '%s' does not exist", results_dir)
            return 1

        for result_file in glob.glob("**/*.json", root_dir=results_dir, recursive=True):
            full_path = os.path.join(results_dir, result_file)
            with open(full_path, "rb") as infile:
                result = json.load(infile)

            action = _clean_data(result)
            if action.action == ActionType.NONE:
                continue

            if action.action == ActionType.UPDATE:
                with open(full_path, "w", encoding="utf-8") as outfile:
                    json.dump(action.content, outfile, indent=2)
                continue

            if action.action == ActionType.DELETE:
                raise NotImplementedError

            msg = f"Unsupported action {action}"
            raise NotImplementedError(msg)

    return 0


if __name__ == "__main__":
    sys.exit(entrypoint())
