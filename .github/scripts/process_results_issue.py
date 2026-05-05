#!/usr/bin/env python3

# ruff: noqa: BLE001 Do not catch blind exception

import base64
import json
import logging
import os
import re
import sys
import zlib

logger = logging.getLogger(__name__)


def main():
    body = os.environ.get("ISSUE_BODY", "")

    match = re.search(r"```\n(.*?)\n```", body, re.DOTALL)
    if not match:
        sys.exit("No payload block found.")

    b64_payload = match.group(1).strip()

    try:
        compressed_data = base64.b64decode(b64_payload)
        json_data = zlib.decompress(compressed_data).decode("utf-8")
        results = json.loads(json_data)
        json_data = json.dumps(results, indent=2)
    except Exception as e:
        sys.exit(f"Failed to decode/decompress/parse: {e}")

    xemu_version = results["xemu_version"]
    machine_token = results["machine_token"]
    renderer = results["renderer"]

    logger.info("Received JSON data:\n\n%s", json_data)

    output_dir = f"results/{xemu_version}"

    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{machine_token}-{renderer}.json")

    with open(filename, "w") as f:
        f.write(json_data)


if __name__ == "__main__":
    main()
