from __future__ import annotations

import json
import logging
from typing import Any, NamedTuple

logger = logging.getLogger(__name__)


class TestSuiteDescriptor(NamedTuple):
    """Describes one of the nxdk_pgraph_tests test suites."""

    suite_name: str
    class_name: str
    description: list[str]
    source_file: str
    source_file_line: int
    test_descriptions: dict[str, str]

    @classmethod
    def from_obj(cls, obj: dict[str, Any]) -> TestSuiteDescriptor:
        return cls(
            suite_name=obj.get("suite", "").replace(" ", "_"),
            class_name=obj.get("class", ""),
            description=obj.get("description", []),
            source_file=obj.get("source_file", ""),
            source_file_line=obj.get("source_file_line", -1),
            test_descriptions=obj.get("test_descriptions", {}),
        )


def _fuzzy_lookup_suite_descriptor(
    descriptors: dict[str, TestSuiteDescriptor], suite_name: str
) -> TestSuiteDescriptor | None:
    """Attempts a permissive lookup of the given suite_name in the given set of `TestSuiteDescriptor`s"""

    # Check for a perfect match.
    ret = descriptors.get(suite_name)
    if ret:
        return ret

    # Descriptor keys are generally of the form TestSuiteTests whereas the suite names tend to be "Test_suite".
    camel_cased = "".join(element.title() for element in suite_name.split("_"))
    ret = descriptors.get(camel_cased)
    if ret:
        return ret

    return descriptors.get(f"{camel_cased}Tests")


class TestSuiteDescriptorLoader:
    """Loads test suite descriptors from the xemu-perf-tests project."""

    def __init__(self, registry_url: str):
        self.registry_url = registry_url

    def _load_registry(self) -> dict[str, Any] | None:
        import requests

        try:
            response = requests.get(self.registry_url, timeout=30)
            response.raise_for_status()
            return json.loads(response.content)
        except requests.exceptions.RequestException:
            logger.exception("Failed to load descriptor from '%s'", self.registry_url)
            return None

    def process(self) -> dict[str, TestSuiteDescriptor]:
        """Loads the test suite descriptors from the registry URL."""

        registry = self._load_registry()
        if not registry:
            return {}

        return {
            descriptor.suite_name: descriptor
            for descriptor in [TestSuiteDescriptor.from_obj(item) for item in registry.get("test_suites", [])]
        }
