# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0

"""Compatibility and pre-flight checks for upgrades."""

import subprocess
import os
from dataclasses import dataclass
from typing import Optional
from system_detector import SystemInfo


@dataclass
class CheckResult:
    """Result of a compatibility check."""
    name: str
    passed: bool
    severity: str  # 'critical', 'warning', 'info'
    message: str
    remediation: Optional[str] = None


class CompatibilityChecker:
    """Performs pre-upgrade compatibility checks."""

    def __init__(self, system: SystemInfo):
        self.system = system

    def run_all_checks(self) -> list[CheckResult]:
        """Run all compatibility checks."""
        checks = [
            self._check_disk_space(),
            self._check_package_updates(),
            self._check_selinux(),
            self._check_third_party_repos(),
            self._check_custom_kernels(),
            self._check_running_services(),
        ]

        if self.system.is_rhel_based:
            checks.append(self._check_subscription())

        return checks

    def _check_disk_space(self) -> CheckResult:
        """Check available disk space."""
        try:
            stat = os.statvfs('/')
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            required_gb = 5.0

            if free_gb >= required_gb:
                return CheckResult(
                    name="Disk Space",
                    passed=True,
                    severity='info',
                    message=f"Sufficient disk space: {free_gb:.1f} GB available"
                )
            else:
                return CheckResult(
                    name="Disk Space",
                    passed=False,
                    severity='critical',
                    message=f"Insufficient disk space: {free_gb:.1f} GB available, {required_gb} GB required",
                    remediation="Free up disk space by removing unused packages or files"
                )
        except Exception as e:
            return CheckResult(
                name="Disk Space",
                passed=False,
                severity='warning',
                message=f"Could not check disk space: {e}"
            )

    def _check_package_updates(self) -> CheckResult:
        """Check if system has pending updates."""
        try:
            cmd = [self.system.package_manager, 'check-update']
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )

            if result.returncode == 0:
                return CheckResult(
                    name="Package Updates",
                    passed=True,
                    severity='info',
                    message="System is up to date"
                )
            elif result.returncode == 100:
                return CheckResult(
                    name="Package Updates",
                    passed=False,
                    severity='warning',
                    message="Pending updates available",
                    remediation=f"Run '{self.system.package_manager} update' before upgrading"
                )
            else:
                return CheckResult(
                    name="Package Updates",
                    passed=False,
                    severity='warning',
                    message="Could not check for updates"
                )
        except Exception as e:
            return CheckResult(
                name="Package Updates",
                passed=False,
                severity='warning',
                message=f"Update check failed: {e}"
            )

    def _check_selinux(self) -> CheckResult:
        """Check SELinux status."""
        try:
            if os.path.exists('/usr/sbin/getenforce'):
                result = subprocess.run(
                    ['/usr/sbin/getenforce'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                    text=True
                )
                status = result.stdout.strip()

                if status in ['Enforcing', 'Permissive']:
                    return CheckResult(
                        name="SELinux",
                        passed=True,
                        severity='info',
                        message=f"SELinux is {status}"
                    )
                else:
                    return CheckResult(
                        name="SELinux",
                        passed=True,
                        severity='warning',
                        message=f"SELinux is {status} - consider enabling for security"
                    )
            else:
                return CheckResult(
                    name="SELinux",
                    passed=True,
                    severity='info',
                    message="SELinux not installed"
                )
        except Exception as e:
            return CheckResult(
                name="SELinux",
                passed=True,
                severity='info',
                message="Could not check SELinux status"
            )

    def _check_third_party_repos(self) -> CheckResult:
        """Check for third-party repositories."""
        repo_dirs = ['/etc/yum.repos.d/', '/etc/dnf/repos.d/']
        third_party_repos = []

        for repo_dir in repo_dirs:
            if os.path.exists(repo_dir):
                for file in os.listdir(repo_dir):
                    if file.endswith('.repo'):
                        file_path = os.path.join(repo_dir, file)
                        if not any(official in file.lower() for official in
                                 ['fedora', 'rhel', 'centos', 'base', 'updates', 'extras']):
                            third_party_repos.append(file)

        if third_party_repos:
            return CheckResult(
                name="Third-party Repositories",
                passed=True,
                severity='warning',
                message=f"Found {len(third_party_repos)} third-party repos: {', '.join(third_party_repos[:3])}",
                remediation="Review and disable third-party repos before upgrade if they cause conflicts"
            )
        else:
            return CheckResult(
                name="Third-party Repositories",
                passed=True,
                severity='info',
                message="No third-party repositories detected"
            )

    def _check_custom_kernels(self) -> CheckResult:
        """Check for custom or third-party kernels."""
        try:
            result = subprocess.run(
                ['uname', '-r'],
                stdout=subprocess.PIPE,
                text=True,
                timeout=5
            )
            kernel = result.stdout.strip()

            if any(custom in kernel.lower() for custom in ['liquorix', 'xanmod', 'zen']):
                return CheckResult(
                    name="Kernel",
                    passed=False,
                    severity='warning',
                    message=f"Custom kernel detected: {kernel}",
                    remediation="Switch to stock kernel before upgrade"
                )
            else:
                return CheckResult(
                    name="Kernel",
                    passed=True,
                    severity='info',
                    message=f"Stock kernel: {kernel}"
                )
        except Exception:
            return CheckResult(
                name="Kernel",
                passed=True,
                severity='info',
                message="Could not determine kernel type"
            )

    def _check_subscription(self) -> CheckResult:
        """Check RHEL subscription status."""
        try:
            if os.path.exists('/usr/sbin/subscription-manager'):
                result = subprocess.run(
                    ['/usr/sbin/subscription-manager', 'status'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                    text=True
                )

                if 'Current' in result.stdout or 'Status: Current' in result.stdout:
                    return CheckResult(
                        name="RHEL Subscription",
                        passed=True,
                        severity='info',
                        message="Active RHEL subscription found"
                    )
                else:
                    return CheckResult(
                        name="RHEL Subscription",
                        passed=False,
                        severity='critical',
                        message="No active RHEL subscription",
                        remediation="Register with subscription-manager or configure CentOS repos"
                    )
            else:
                return CheckResult(
                    name="RHEL Subscription",
                    passed=True,
                    severity='info',
                    message="Not a subscription-managed system (CentOS/Rocky/Alma)"
                )
        except Exception as e:
            return CheckResult(
                name="RHEL Subscription",
                passed=True,
                severity='warning',
                message="Could not check subscription status"
            )

    def _check_running_services(self) -> CheckResult:
        """Check for critical running services."""
        try:
            result = subprocess.run(
                ['systemctl', 'list-units', '--type=service', '--state=running', '--no-pager'],
                stdout=subprocess.PIPE,
                text=True,
                timeout=10
            )

            service_count = len([line for line in result.stdout.split('\n')
                               if '.service' in line and 'running' in line])

            return CheckResult(
                name="Running Services",
                passed=True,
                severity='info',
                message=f"{service_count} services currently running - note for post-upgrade verification"
            )
        except Exception:
            return CheckResult(
                name="Running Services",
                passed=True,
                severity='info',
                message="Could not enumerate services"
            )
