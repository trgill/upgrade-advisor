"""System detection module for identifying OS version and configuration."""

import os
import platform
import subprocess
from dataclasses import dataclass
from typing import Optional
import distro


@dataclass
class SystemInfo:
    """Container for system information."""
    os_id: str
    os_version: str
    os_name: str
    os_codename: str
    kernel: str
    architecture: str
    is_rhel_based: bool
    is_fedora: bool
    package_manager: str

    def __str__(self):
        return f"{self.os_name} {self.os_version} ({self.os_codename})"


class SystemDetector:
    """Detects current Linux system information."""

    @staticmethod
    def detect() -> SystemInfo:
        """Detect and return current system information."""
        info = distro.info()

        os_id = info.get('id', '').lower()
        os_version = info.get('version', '')
        os_name = info.get('name', '')
        os_codename = info.get('codename', '')

        is_rhel_based = os_id in ['rhel', 'centos', 'rocky', 'almalinux', 'ol']
        is_fedora = os_id == 'fedora'

        package_manager = SystemDetector._detect_package_manager(is_rhel_based, is_fedora)

        return SystemInfo(
            os_id=os_id,
            os_version=os_version,
            os_name=os_name,
            os_codename=os_codename,
            kernel=platform.release(),
            architecture=platform.machine(),
            is_rhel_based=is_rhel_based,
            is_fedora=is_fedora,
            package_manager=package_manager
        )

    @staticmethod
    def _detect_package_manager(is_rhel_based: bool, is_fedora: bool) -> str:
        """Detect which package manager is in use."""
        if is_fedora:
            if os.path.exists('/usr/bin/dnf'):
                return 'dnf'
            elif os.path.exists('/usr/bin/yum'):
                return 'yum'

        if is_rhel_based:
            if os.path.exists('/usr/bin/dnf'):
                return 'dnf'
            elif os.path.exists('/usr/bin/yum'):
                return 'yum'

        return 'unknown'

    @staticmethod
    def check_prerequisites() -> dict[str, bool]:
        """Check if required tools are available."""
        checks = {}

        checks['has_root'] = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
        checks['has_leapp'] = os.path.exists('/usr/bin/leapp')
        checks['has_ansible'] = os.path.exists('/usr/bin/ansible') or \
                                os.path.exists('/usr/local/bin/ansible')
        checks['has_internet'] = SystemDetector._check_internet()

        return checks

    @staticmethod
    def _check_internet() -> bool:
        """Check for internet connectivity."""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', '8.8.8.8'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
