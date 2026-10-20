#!/usr/bin/env python3

"""Lists and removes development (PR/CI build) results stored under dev_results/."""

# ruff: noqa: T201 `print` found
# ruff: noqa: S310 Audit URL open for permitted schemes

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dev_results")
_KEY_RE = re.compile(r"^(pr|run)-(\d+)$")


@dataclass
class DevResultsEntry:
    key: str
    path: str
    metadata: dict[str, Any]
    num_files: int

    @property
    def pr_number(self) -> int | None:
        match = _KEY_RE.match(self.key)
        if match and match.group(1) == "pr":
            return int(match.group(2))
        return None

    @property
    def last_updated(self) -> datetime.datetime | None:
        value = self.metadata.get("last_updated")
        if not value:
            return None
        try:
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            return None


def load_entries(root: str) -> list[DevResultsEntry]:
    if not os.path.isdir(root):
        return []

    ret = []
    for key in sorted(os.listdir(root)):
        path = os.path.join(root, key)
        if not os.path.isdir(path) or not _KEY_RE.match(key):
            continue

        metadata: dict[str, Any] = {}
        metadata_file = os.path.join(path, "pr.json")
        if os.path.isfile(metadata_file):
            with open(metadata_file) as infile:
                metadata = json.load(infile)

        num_files = sum(
            1 for _dirpath, _dirs, files in os.walk(path) for name in files if name.endswith(("-GL.json", "-VK.json"))
        )
        ret.append(DevResultsEntry(key=key, path=path, metadata=metadata, num_files=num_files))
    return ret


def _fetch_pr_state(repo: str, pr_number: int, token: str | None) -> tuple[str, datetime.datetime | None]:
    """Returns the (state, closed_at) of the given PR."""
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        info = json.load(response)

    closed_at = info.get("closed_at")
    return info.get("state", "unknown"), datetime.datetime.fromisoformat(closed_at) if closed_at else None


def _remove(entry: DevResultsEntry, *, dry_run: bool, reason: str = "") -> None:
    suffix = f" ({reason})" if reason else ""
    if dry_run:
        print(f"Would remove {entry.key}{suffix}")
        return
    shutil.rmtree(entry.path)
    print(f"Removed {entry.key}{suffix}")


def cmd_list(entries: list[DevResultsEntry], args) -> int:
    if not entries:
        print("No development results.")
        return 0

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    for entry in entries:
        state = ""
        if args.check_state and entry.pr_number:
            try:
                state, _closed_at = _fetch_pr_state(
                    entry.metadata.get("repo", args.default_repo), entry.pr_number, token
                )
            except urllib.error.URLError as err:
                state = f"error: {err}"
        title = entry.metadata.get("pr_title", "")
        updated = entry.metadata.get("last_updated", "unknown")
        state_str = f" [{state}]" if state else ""
        print(f"{entry.key}{state_str}: {entry.num_files} result files, last updated {updated}  {title}")
    return 0


def cmd_remove(entries: list[DevResultsEntry], args) -> int:
    requested = set()
    for raw_value in args.keys:
        value = raw_value.strip().lstrip("#")
        requested.add(f"pr-{value}" if value.isdigit() else value)

    by_key = {entry.key: entry for entry in entries}
    missing = sorted(requested - set(by_key))
    for key in missing:
        logger.error("No development results for '%s'", key)

    for key in sorted(requested & set(by_key)):
        _remove(by_key[key], dry_run=args.dry_run)

    return 1 if missing else 0


def cmd_prune(entries: list[DevResultsEntry], args) -> int:
    now = datetime.datetime.now(datetime.UTC)
    cutoff = now - datetime.timedelta(days=args.closed_older_than)
    run_cutoff = now - datetime.timedelta(days=args.runs_older_than)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    failures = 0
    for entry in entries:
        if not entry.pr_number:
            last_updated = entry.last_updated
            if last_updated and last_updated < run_cutoff:
                _remove(entry, dry_run=args.dry_run, reason=f"CI run results last updated {last_updated.date()}")
            continue

        repo = entry.metadata.get("repo", args.default_repo)
        try:
            state, closed_at = _fetch_pr_state(repo, entry.pr_number, token)
        except urllib.error.HTTPError as err:
            if err.code == 404:  # noqa: PLR2004 Magic value used in comparison
                _remove(entry, dry_run=args.dry_run, reason=f"{repo}#{entry.pr_number} no longer exists")
                continue
            logger.exception("Failed to fetch state of %s#%d", repo, entry.pr_number)
            failures += 1
            continue
        except urllib.error.URLError:
            logger.exception("Failed to fetch state of %s#%d", repo, entry.pr_number)
            failures += 1
            continue

        if state == "closed" and closed_at and closed_at < cutoff:
            _remove(entry, dry_run=args.dry_run, reason=f"{repo}#{entry.pr_number} closed {closed_at.date()}")
        else:
            logger.info("Keeping %s (%s)", entry.key, state)

    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=_DEFAULT_ROOT, help="Path to the dev_results directory.")
    parser.add_argument("--default-repo", default="xemu-project/xemu", help="Repo used if pr.json has no repo.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enables verbose logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List development results.")
    list_parser.add_argument("--check-state", action="store_true", help="Query GitHub for each PR's state.")
    list_parser.set_defaults(func=cmd_list)

    remove_parser = subparsers.add_parser("remove", help="Remove results for the given PRs/runs.")
    remove_parser.add_argument("keys", nargs="+", help="PR numbers (e.g. 3088) or keys (e.g. pr-3088, run-1234).")
    remove_parser.add_argument("--dry-run", action="store_true", help="Print what would be removed.")
    remove_parser.set_defaults(func=cmd_remove)

    prune_parser = subparsers.add_parser("prune", help="Remove results for PRs that were closed a while ago.")
    prune_parser.add_argument(
        "--closed-older-than", type=int, default=14, metavar="DAYS", help="Remove PRs closed more than DAYS ago."
    )
    prune_parser.add_argument(
        "--runs-older-than",
        type=int,
        default=30,
        metavar="DAYS",
        help="Remove results for CI runs not associated with a PR that were last updated more than DAYS ago.",
    )
    prune_parser.add_argument("--dry-run", action="store_true", help="Print what would be removed.")
    prune_parser.set_defaults(func=cmd_prune)

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    return args.func(load_entries(os.path.abspath(args.root)), args)


if __name__ == "__main__":
    sys.exit(main())
