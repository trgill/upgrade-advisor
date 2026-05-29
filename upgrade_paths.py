# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0

"""Upgrade path logic and recommendations."""

from dataclasses import dataclass
from typing import Optional
from system_detector import SystemInfo


@dataclass
class UpgradePath:
    """Represents an available upgrade path."""
    from_version: str
    to_version: str
    method: str  # 'leapp' or 'ansible'
    supported: bool
    notes: list[str]
    risk_level: str  # 'low', 'medium', 'high'


class UpgradePathFinder:
    """Determines available upgrade paths for a system."""

    FEDORA_PATHS = {
        '38': {'to': '39', 'risk': 'low'},
        '39': {'to': '40', 'risk': 'low'},
        '40': {'to': '41', 'risk': 'low'},
        '41': {'to': '42', 'risk': 'medium'},  # Future version
    }

    RHEL_LEAPP_PATHS = {
        '7': {'to': ['8'], 'risk': 'high'},
        '8': {'to': ['9'], 'risk': 'medium'},
    }

    @staticmethod
    def find_paths(system: SystemInfo) -> list[UpgradePath]:
        """Find available upgrade paths for the given system."""
        paths = []

        if system.is_fedora:
            paths.extend(UpgradePathFinder._fedora_paths(system))
        elif system.is_rhel_based:
            paths.extend(UpgradePathFinder._rhel_paths(system))

        return paths

    @staticmethod
    def _fedora_paths(system: SystemInfo) -> list[UpgradePath]:
        """Generate Fedora upgrade paths."""
        paths = []
        current_version = system.os_version.split('.')[0]

        if current_version in UpgradePathFinder.FEDORA_PATHS:
            upgrade_info = UpgradePathFinder.FEDORA_PATHS[current_version]
            target = upgrade_info['to']

            notes = [
                "Fedora upgrades use DNF system-upgrade plugin",
                "Ensure all packages are updated before upgrading",
                "Reboot required after upgrade",
            ]

            if upgrade_info['risk'] == 'medium':
                notes.append("Target version not yet released - prepare for testing")

            paths.append(UpgradePath(
                from_version=current_version,
                to_version=target,
                method='ansible',
                supported=True,
                notes=notes,
                risk_level=upgrade_info['risk']
            ))
        else:
            paths.append(UpgradePath(
                from_version=current_version,
                to_version='unknown',
                method='ansible',
                supported=False,
                notes=[f"Fedora {current_version} is EOL or unsupported"],
                risk_level='high'
            ))

        return paths

    @staticmethod
    def _rhel_paths(system: SystemInfo) -> list[UpgradePath]:
        """Generate RHEL/CentOS upgrade paths using Leapp."""
        paths = []
        major_version = system.os_version.split('.')[0]

        if major_version in UpgradePathFinder.RHEL_LEAPP_PATHS:
            upgrade_info = UpgradePathFinder.RHEL_LEAPP_PATHS[major_version]

            for target in upgrade_info['to']:
                notes = [
                    "RHEL in-place upgrades use Leapp utility",
                    "Requires active RHEL subscription (or CentOS repos)",
                    "Review Leapp pre-upgrade report carefully",
                    "Full system backup strongly recommended",
                ]

                if major_version == '7':
                    notes.append("RHEL 7 → 8 is a major upgrade with significant changes")
                    notes.append("Python 2 → Python 3 migration required")

                paths.append(UpgradePath(
                    from_version=major_version,
                    to_version=target,
                    method='leapp',
                    supported=True,
                    notes=notes,
                    risk_level=upgrade_info['risk']
                ))
        else:
            if major_version == '9':
                notes = ["RHEL 9 is the latest major version", "Apply updates regularly"]
                risk = 'low'
                supported = True
            else:
                notes = [f"RHEL {major_version} upgrade path not defined or EOL"]
                risk = 'high'
                supported = False

            paths.append(UpgradePath(
                from_version=major_version,
                to_version='N/A' if major_version == '9' else 'unknown',
                method='leapp',
                supported=supported,
                notes=notes,
                risk_level=risk
            ))

        return paths

    @staticmethod
    def recommend_best_path(paths: list[UpgradePath]) -> Optional[UpgradePath]:
        """Recommend the best upgrade path from available options."""
        if not paths:
            return None

        supported_paths = [p for p in paths if p.supported]
        if not supported_paths:
            return None

        risk_priority = {'low': 0, 'medium': 1, 'high': 2}
        return min(supported_paths, key=lambda p: risk_priority.get(p.risk_level, 999))
