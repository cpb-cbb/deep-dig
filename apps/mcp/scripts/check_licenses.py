#!/usr/bin/env python3
from __future__ import annotations

import re
from importlib import metadata
from packaging.requirements import Requirement


ROOT_PACKAGE = "deep-dig-mcp"
FORBIDDEN_PACKAGES = {"pymupdf", "pymupdf4llm", "pymupdf-layout"}
FORBIDDEN_LICENSE_MARKERS = {"AGPL", "GPL-2", "GPL-3", "SSPL"}


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def production_distributions() -> dict[str, metadata.Distribution]:
    discovered: dict[str, metadata.Distribution] = {}
    pending = [ROOT_PACKAGE]
    while pending:
        name = normalize(pending.pop())
        if name in discovered:
            continue
        distribution = metadata.distribution(name)
        discovered[name] = distribution
        for raw_requirement in distribution.requires or []:
            requirement = Requirement(raw_requirement)
            if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
                continue
            pending.append(requirement.name)
    return discovered


def license_label(distribution: metadata.Distribution) -> str:
    expression = distribution.metadata.get("License-Expression")
    if expression:
        return expression
    value = distribution.metadata.get("License")
    if value and len(value) < 160:
        return " ".join(value.split())
    classifiers = distribution.metadata.get_all("Classifier") or []
    licenses = [item.rsplit("::", 1)[-1].strip() for item in classifiers if "License ::" in item]
    return ", ".join(licenses) or "UNKNOWN"


def main() -> None:
    distributions = production_distributions()
    violations: list[str] = []
    print("PACKAGE\tVERSION\tLICENSE")
    for name in sorted(distributions):
        distribution = distributions[name]
        license_name = license_label(distribution)
        print(f"{name}\t{distribution.version}\t{license_name}")
        upper_license = license_name.upper()
        if name in FORBIDDEN_PACKAGES:
            violations.append(f"forbidden dependency present: {name}")
        if any(marker in upper_license for marker in FORBIDDEN_LICENSE_MARKERS):
            violations.append(f"disallowed license for {name}: {license_name}")
    if violations:
        raise SystemExit("\n".join(violations))


if __name__ == "__main__":
    main()
