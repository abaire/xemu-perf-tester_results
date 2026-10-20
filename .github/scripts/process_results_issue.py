#!/usr/bin/env python3

# ruff: noqa: BLE001 Do not catch blind exception

import base64
import datetime
import json
import logging
import os
import re
import sys
import zlib

logger = logging.getLogger(__name__)

_MACHINE_TOKEN_RE = re.compile(r"^[a-f0-9]{16,128}$")
_RENDERERS = {"GL", "VK"}
# Version strings come from xemu's build info, e.g.
#   xemu-0.8.134-fc9980d2962cbec656253106ea2e121fab1e68d4
#   xemu-0.8.92-4-gfe356d27a4- -fe356d27a428c676846d20bab7f6fd21a210bbb1
_XEMU_VERSION_RE = re.compile(r"^xemu-[\w.\- /]+$")
_HEAD_SHA_RE = re.compile(r"^[a-f0-9]{7,40}$")

DEV_RESULTS_ROOT = "dev_results"
RESULTS_ROOT = "results"


def _validate_path_component(value: str, description: str) -> str:
    if not value or value in {".", ".."} or "/" in value or "\\" in value or ".." in value:
        msg = f"Invalid {description}: {value!r}"
        raise ValueError(msg)
    return value


def _validate_xemu_version(xemu_version) -> str:
    if not isinstance(xemu_version, str) or not _XEMU_VERSION_RE.match(xemu_version):
        msg = f"Invalid xemu_version: {xemu_version!r}"
        raise ValueError(msg)
    # Some historical dev builds report branches containing "/", which would create nested directories.
    return _validate_path_component(xemu_version.replace("/", "_"), "xemu_version")


def _validate_positive_int(value, description: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        msg = f"Invalid {description}: {value!r}"
        raise ValueError(msg)
    return value


def dev_results_key(dev_build: dict) -> str:
    """Returns the directory name under dev_results/ for the given dev_build metadata."""
    pr_number = dev_build.get("pr_number")
    if pr_number is not None:
        return f"pr-{_validate_positive_int(pr_number, 'pr_number')}"
    return f"run-{_validate_positive_int(dev_build.get('run_id'), 'run_id')}"


def _build_dev_metadata(dev_build: dict, existing: dict | None) -> dict:
    head_sha = dev_build.get("head_sha", "")
    if head_sha and not _HEAD_SHA_RE.match(head_sha):
        msg = f"Invalid head_sha: {head_sha!r}"
        raise ValueError(msg)

    metadata = dict(existing or {})
    for key in ("repo", "pr_number", "pr_url", "pr_title", "head_ref", "head_sha", "run_id", "run_url", "base_version"):
        value = dev_build.get(key)
        if value is not None:
            metadata[key] = value
    metadata["last_updated"] = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    return metadata


def output_path_for_results(results: dict, root: str = ".") -> tuple[str, str | None]:
    """Returns (result_file_path, dev_metadata_path_or_None) for the given results payload."""
    xemu_version = _validate_xemu_version(results.get("xemu_version"))

    machine_token = results.get("machine_token")
    if not isinstance(machine_token, str) or not _MACHINE_TOKEN_RE.match(machine_token):
        msg = f"Invalid machine_token: {machine_token!r}"
        raise ValueError(msg)

    renderer = results.get("renderer")
    if renderer not in _RENDERERS:
        msg = f"Invalid renderer: {renderer!r}"
        raise ValueError(msg)

    filename = f"{machine_token}-{renderer}.json"
    dev_build = results.get("dev_build")
    if not dev_build:
        return os.path.join(root, RESULTS_ROOT, xemu_version, filename), None

    if not isinstance(dev_build, dict):
        msg = f"Invalid dev_build: {dev_build!r}"
        raise ValueError(msg)  # noqa: TRY004 Prefer `TypeError` exception for invalid type
    dev_dir = os.path.join(root, DEV_RESULTS_ROOT, dev_results_key(dev_build))
    return os.path.join(dev_dir, xemu_version, filename), os.path.join(dev_dir, "pr.json")


def ingest(results: dict, root: str = ".") -> str:
    """Writes the given results payload into the repository, returning the path of the written file."""
    filename, dev_metadata_path = output_path_for_results(results, root)

    if dev_metadata_path:
        existing = None
        if os.path.isfile(dev_metadata_path):
            with open(dev_metadata_path) as infile:
                existing = json.load(infile)
        metadata = _build_dev_metadata(results["dev_build"], existing)
        os.makedirs(os.path.dirname(dev_metadata_path), exist_ok=True)
        with open(dev_metadata_path, "w") as outfile:
            json.dump(metadata, outfile, indent=2)
            outfile.write("\n")

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        f.write(json.dumps(results, indent=2))

    return filename


def _set_output(name: str, value: str):
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        return
    with open(output_file, "a") as outfile:
        outfile.write(f"{name}={value}\n")


def main():
    logging.basicConfig(level=logging.INFO)
    body = os.environ.get("ISSUE_BODY", "")

    match = re.search(r"```\n(.*?)\n```", body, re.DOTALL)
    if not match:
        sys.exit("No payload block found.")

    b64_payload = match.group(1).strip()

    try:
        compressed_data = base64.b64decode(b64_payload)
        json_data = zlib.decompress(compressed_data).decode("utf-8")
        results = json.loads(json_data)
    except Exception as e:
        sys.exit(f"Failed to decode/decompress/parse: {e}")

    if not isinstance(results, dict):
        sys.exit("Payload is not a JSON object.")

    logger.info("Received JSON data:\n\n%s", json.dumps(results, indent=2))

    try:
        filename = ingest(results)
    except (ValueError, KeyError) as e:
        sys.exit(f"Invalid payload: {e}")

    logger.info("Wrote %s", filename)
    _set_output("is_dev_result", "true" if results.get("dev_build") else "false")


if __name__ == "__main__":
    main()
