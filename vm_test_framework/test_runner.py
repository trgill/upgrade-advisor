#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0

"""Test runner and orchestrator for VM-based upgrade tests."""

import sys
import os
import time
import json
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vm_test_framework.vm_manager import VMManager, VMInstance
from vm_test_framework.test_matrix import TestMatrix, TestCase, ValidationCheck
from upgrade_executor import UpgradeExecutor
from system_detector import SystemInfo, SystemDetector


@dataclass
class TestResult:
    """Result of a single test case."""
    test_id: str
    test_name: str
    status: str  # 'pass', 'fail', 'error', 'timeout', 'skipped'
    start_time: str
    end_time: str
    duration_seconds: float
    vm_name: str
    source_version: str
    target_version: str
    error_message: Optional[str] = None
    validation_results: List[Dict] = None
    logs_path: Optional[str] = None

    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)


class TestRunner:
    """Orchestrates VM-based upgrade tests."""

    def __init__(self, results_dir: str = "vm_test_framework/results"):
        """Initialize test runner."""
        self.vm_manager = VMManager()
        self.results_dir = Path(results_dir)
        self.current_run_dir = None
        self.results = []

    def run_test_suite(self, test_cases: List[TestCase], parallel_jobs: int = 1,
                       dry_run: bool = False) -> List[TestResult]:
        """
        Run a suite of test cases.

        Args:
            test_cases: List of test cases to run
            parallel_jobs: Number of tests to run in parallel
            dry_run: If True, print what would be done without executing

        Returns:
            List of test results
        """
        # Create results directory for this run
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_run_dir = self.results_dir / timestamp
        self.current_run_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"Starting test suite: {len(test_cases)} tests")
        print(f"Parallel jobs: {parallel_jobs}")
        print(f"Results directory: {self.current_run_dir}")
        print(f"{'='*60}\n")

        if dry_run:
            print("DRY RUN MODE - No tests will actually execute\n")
            for tc in test_cases:
                print(f"  Would run: {tc.get_test_id()}")
                print(f"    {tc.source_os} {tc.source_version} → {tc.target_os} {tc.target_version}")
                print(f"    Profile: {tc.profile}, Packages: {tc.package_set.name}")
                print(f"    Storage: {tc.storage_layout.name}\n")
            return []

        # Run tests
        if parallel_jobs == 1:
            # Sequential execution
            for i, test_case in enumerate(test_cases, 1):
                print(f"\n[{i}/{len(test_cases)}] Running test: {test_case.name}")
                result = self._run_single_test(test_case)
                self.results.append(result)
                self._save_result(result)
        else:
            # Parallel execution
            with ThreadPoolExecutor(max_workers=parallel_jobs) as executor:
                future_to_test = {
                    executor.submit(self._run_single_test, tc): tc
                    for tc in test_cases
                }

                for future in as_completed(future_to_test):
                    test_case = future_to_test[future]
                    try:
                        result = future.result()
                        self.results.append(result)
                        self._save_result(result)
                    except Exception as exc:
                        print(f"⚠ Test {test_case.name} generated an exception: {exc}")

        # Generate summary report
        self._generate_summary_report()

        return self.results

    def _run_single_test(self, test_case: TestCase) -> TestResult:
        """
        Run a single test case.

        Workflow:
        1. Clone VM from template
        2. Start VM
        3. Configure system (install packages, etc.)
        4. Take pre-upgrade snapshot
        5. Execute upgrade
        6. Validate results
        7. Collect logs
        8. Cleanup
        """
        test_id = test_case.get_test_id()
        vm_name = f"test-{test_id}-{int(time.time())}"

        start_time = datetime.now()
        status = "unknown"
        error_message = None
        validation_results = []
        logs_path = None

        try:
            print(f"\n{'='*60}")
            print(f"Test: {test_case.name} ({test_id})")
            print(f"VM: {vm_name}")
            print(f"{'='*60}")

            # Step 1: Create VM
            print(f"\n[1/7] Creating VM from template...")
            template_name = f"{test_case.source_os}-{test_case.source_version}-{test_case.profile}"

            # Check if template exists
            templates = self.vm_manager.list_templates()
            template_exists = any(t.name == template_name for t in templates)

            if not template_exists:
                error_message = f"Template not found: {template_name}. Run 'python vm_manager.py create-template' first."
                print(f"⚠ {error_message}")
                status = "skipped"
                return self._create_result(test_case, vm_name, start_time, status, error_message)

            vm_instance = self.vm_manager.clone_vm(template_name, vm_name)
            print(f"✓ VM created: {vm_name}")

            # Step 2: Start VM
            print(f"\n[2/7] Starting VM...")
            self.vm_manager.start_vm(vm_name, wait_for_boot=True)
            print(f"✓ VM started")

            # Get VM IP for SSH
            vm_info = self.vm_manager.get_vm_info(vm_name)
            if not vm_info or not vm_info.ip_address:
                print("⚠ Waiting for VM to get IP address...")
                time.sleep(10)
                vm_info = self.vm_manager.get_vm_info(vm_name)

            # Step 3: Configure system
            print(f"\n[3/7] Configuring system...")
            if test_case.package_set.packages or test_case.package_set.pre_install_commands:
                self._configure_vm(vm_name, test_case)
            print(f"✓ System configured")

            # Step 4: Take pre-upgrade snapshot
            print(f"\n[4/7] Creating pre-upgrade snapshot...")
            snapshot_name = "pre-upgrade"
            self.vm_manager.snapshot_vm(vm_name, snapshot_name, "Pre-upgrade state")
            print(f"✓ Snapshot created: {snapshot_name}")

            # Step 5: Execute upgrade
            print(f"\n[5/7] Executing upgrade...")
            upgrade_success, upgrade_output = self._execute_upgrade(
                vm_name, test_case, test_case.timeout_minutes
            )

            if not upgrade_success:
                error_message = f"Upgrade failed: {upgrade_output}"
                status = "fail"
            else:
                print(f"✓ Upgrade completed")

                # Step 6: Validate
                print(f"\n[6/7] Running validations...")
                validation_results = self._run_validations(vm_name, test_case.validations)

                # Determine status based on validations
                critical_failures = [v for v in validation_results if not v['passed'] and v['critical']]
                if critical_failures:
                    status = "fail"
                    error_message = f"Failed {len(critical_failures)} critical validations"
                else:
                    status = "pass"

                print(f"✓ Validations complete: {sum(v['passed'] for v in validation_results)}/{len(validation_results)} passed")

            # Step 7: Collect logs
            print(f"\n[7/7] Collecting logs...")
            logs_path = self._collect_logs(vm_name, test_case)
            print(f"✓ Logs collected: {logs_path}")

        except subprocess.TimeoutExpired:
            status = "timeout"
            error_message = f"Test timed out after {test_case.timeout_minutes} minutes"
            print(f"⚠ {error_message}")

        except Exception as e:
            status = "error"
            error_message = str(e)
            print(f"⚠ Error: {error_message}")

        finally:
            # Cleanup
            print(f"\n[Cleanup] Destroying VM...")
            try:
                self.vm_manager.destroy_vm(vm_name, delete_disk=True)
                print(f"✓ VM destroyed")
            except Exception as e:
                print(f"⚠ Warning: Could not destroy VM: {e}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = TestResult(
            test_id=test_id,
            test_name=test_case.name,
            status=status,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            vm_name=vm_name,
            source_version=f"{test_case.source_os} {test_case.source_version}",
            target_version=f"{test_case.target_os} {test_case.target_version}",
            error_message=error_message,
            validation_results=validation_results,
            logs_path=logs_path
        )

        # Print result summary
        symbol = "✓" if status == "pass" else "✗"
        print(f"\n{symbol} Test {status.upper()}: {test_case.name}")
        print(f"  Duration: {duration:.1f}s")
        if error_message:
            print(f"  Error: {error_message}")

        return result

    def _create_result(self, test_case: TestCase, vm_name: str, start_time: datetime,
                      status: str, error_message: Optional[str]) -> TestResult:
        """Create a test result for early termination."""
        end_time = datetime.now()
        return TestResult(
            test_id=test_case.get_test_id(),
            test_name=test_case.name,
            status=status,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=(end_time - start_time).total_seconds(),
            vm_name=vm_name,
            source_version=f"{test_case.source_os} {test_case.source_version}",
            target_version=f"{test_case.target_os} {test_case.target_version}",
            error_message=error_message,
            validation_results=[]
        )

    def _configure_vm(self, vm_name: str, test_case: TestCase):
        """Configure VM with packages and settings."""
        # Install packages
        if test_case.package_set.packages:
            packages = ' '.join(test_case.package_set.packages)
            cmd = f"dnf install -y {packages}"
            self._exec_in_vm(vm_name, cmd, timeout=600)

        # Run pre-install commands
        for cmd in test_case.package_set.pre_install_commands:
            self._exec_in_vm(vm_name, cmd, timeout=300)

    def _execute_upgrade(self, vm_name: str, test_case: TestCase,
                        timeout_minutes: int) -> Tuple[bool, str]:
        """Execute the upgrade inside the VM."""
        # Copy upgrade-advisor into VM
        # For now, we'll execute upgrade commands directly

        if test_case.source_os == 'rhel':
            # RHEL upgrade via Leapp
            commands = [
                'dnf install -y leapp-upgrade',
                'leapp preupgrade',
                'leapp upgrade --reboot'
            ]
        elif test_case.source_os == 'fedora':
            # Fedora upgrade via DNF
            commands = [
                'dnf install -y dnf-plugin-system-upgrade',
                f'dnf system-upgrade download --releasever={test_case.target_version} -y',
                'dnf system-upgrade reboot'
            ]
        else:
            return False, f"Unsupported OS: {test_case.source_os}"

        try:
            for cmd in commands:
                print(f"  Running: {cmd}")
                output = self._exec_in_vm(vm_name, cmd, timeout=timeout_minutes*60)

            # Wait for reboot and upgrade to complete
            print(f"  Waiting for upgrade to complete (timeout: {timeout_minutes}m)...")
            time.sleep(60)  # Initial wait for reboot

            # Poll for VM to come back up
            max_wait = timeout_minutes * 60
            waited = 0
            while waited < max_wait:
                try:
                    state = self.vm_manager.get_vm_state(vm_name)
                    if state.value == 'running':
                        # Try to SSH to verify it's actually up
                        self._exec_in_vm(vm_name, 'uptime', timeout=10)
                        return True, "Upgrade completed successfully"
                except Exception:
                    pass

                time.sleep(30)
                waited += 30

            return False, f"VM did not come back up after {timeout_minutes} minutes"

        except Exception as e:
            return False, str(e)

    def _run_validations(self, vm_name: str, validations: List[ValidationCheck]) -> List[Dict]:
        """Run post-upgrade validation checks."""
        results = []

        for validation in validations:
            result = {
                'name': validation.name,
                'type': validation.type,
                'critical': validation.critical,
                'passed': False,
                'output': '',
                'error': None
            }

            try:
                if validation.type == 'command':
                    output = self._exec_in_vm(vm_name, validation.target, timeout=60)
                    result['output'] = output
                    result['passed'] = validation.expected == 'success' or validation.expected in output

                elif validation.type == 'service':
                    output = self._exec_in_vm(
                        vm_name,
                        f'systemctl is-active {validation.target}',
                        timeout=30
                    )
                    result['output'] = output.strip()
                    result['passed'] = validation.expected in output

                elif validation.type == 'package':
                    output = self._exec_in_vm(
                        vm_name,
                        f'rpm -q {validation.target}',
                        timeout=30
                    )
                    result['output'] = output
                    result['passed'] = validation.target in output

                elif validation.type == 'file':
                    output = self._exec_in_vm(
                        vm_name,
                        f'test -f {validation.target} && echo "exists"',
                        timeout=30
                    )
                    result['passed'] = 'exists' in output

            except Exception as e:
                result['error'] = str(e)
                result['passed'] = False

            results.append(result)

            # Print result
            symbol = "✓" if result['passed'] else "✗"
            critical = " [CRITICAL]" if validation.critical else ""
            print(f"    {symbol} {validation.name}{critical}")

        return results

    def _exec_in_vm(self, vm_name: str, command: str, timeout: int = 300) -> str:
        """Execute a command inside VM via SSH (placeholder)."""
        # In real implementation, this would use SSH
        # For now, using virsh console or virt-exec

        # Get VM IP
        vm_info = self.vm_manager.get_vm_info(vm_name)

        # For prototype, we'll use virsh console
        # In production, use paramiko for SSH
        print(f"    [SSH] {command[:80]}...")

        # Placeholder - in real implementation, use SSH
        # result = subprocess.run(
        #     ['ssh', f'root@{vm_info.ip_address}', command],
        #     capture_output=True, text=True, timeout=timeout
        # )

        # For now, return success
        return "command output"

    def _collect_logs(self, vm_name: str, test_case: TestCase) -> str:
        """Collect logs from VM."""
        logs_dir = self.current_run_dir / 'logs' / test_case.get_test_id()
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Collect various logs
        log_files = {
            'leapp-report.txt': '/var/log/leapp/leapp-report.txt',
            'leapp-upgrade.log': '/var/log/leapp/leapp-upgrade.log',
            'dnf.log': '/var/log/dnf.log',
            'messages': '/var/log/messages'
        }

        # In real implementation, use SCP to download logs
        # For now, create placeholder
        for local_name, remote_path in log_files.items():
            log_file = logs_dir / local_name
            log_file.write_text(f"Log from {remote_path}\n")

        return str(logs_dir)

    def _save_result(self, result: TestResult):
        """Save individual test result to JSON."""
        result_file = self.current_run_dir / f"{result.test_id}.json"
        with open(result_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

    def _generate_summary_report(self):
        """Generate summary report of all test results."""
        summary_file = self.current_run_dir / 'summary.json'

        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.results),
            'passed': len([r for r in self.results if r.status == 'pass']),
            'failed': len([r for r in self.results if r.status == 'fail']),
            'errors': len([r for r in self.results if r.status == 'error']),
            'timeouts': len([r for r in self.results if r.status == 'timeout']),
            'skipped': len([r for r in self.results if r.status == 'skipped']),
            'total_duration_seconds': sum(r.duration_seconds for r in self.results),
            'results': [r.to_dict() for r in self.results]
        }

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        # Print summary
        print(f"\n{'='*60}")
        print(f"TEST SUITE SUMMARY")
        print(f"{'='*60}")
        print(f"Total tests:  {summary['total_tests']}")
        print(f"✓ Passed:     {summary['passed']}")
        print(f"✗ Failed:     {summary['failed']}")
        print(f"⚠ Errors:     {summary['errors']}")
        print(f"⏱ Timeouts:   {summary['timeouts']}")
        print(f"⊘ Skipped:    {summary['skipped']}")
        print(f"Duration:     {summary['total_duration_seconds']:.1f}s")
        print(f"\nResults: {summary_file}")
        print(f"{'='*60}\n")

        return summary


def main():
    """CLI interface for test runner."""
    import argparse

    parser = argparse.ArgumentParser(description='VM Test Framework - Test Runner')
    parser.add_argument('--config', help='Path to test matrix YAML config')
    parser.add_argument('--parallel', type=int, default=1, help='Number of parallel jobs')
    parser.add_argument('--dry-run', action='store_true', help='Print what would be done')
    parser.add_argument('--filter-tags', nargs='+', help='Filter tests by tags')
    parser.add_argument('--filter-profile', help='Filter tests by profile')

    args = parser.parse_args()

    if not args.config:
        print("Error: --config required")
        print("\nExample:")
        print("  python test_runner.py --config test_configs/rhel9-to-10.yaml")
        sys.exit(1)

    # Load test matrix
    print(f"Loading test matrix from: {args.config}")
    test_cases = TestMatrix.from_yaml(args.config)

    # Apply filters
    if args.filter_tags:
        test_cases = TestMatrix.filter_tests(test_cases, tags=args.filter_tags)
        print(f"Filtered by tags {args.filter_tags}: {len(test_cases)} tests")

    if args.filter_profile:
        test_cases = TestMatrix.filter_tests(test_cases, profile=args.filter_profile)
        print(f"Filtered by profile '{args.filter_profile}': {len(test_cases)} tests")

    if not test_cases:
        print("No tests to run after filtering")
        sys.exit(0)

    # Run tests
    runner = TestRunner()
    results = runner.run_test_suite(
        test_cases,
        parallel_jobs=args.parallel,
        dry_run=args.dry_run
    )

    # Exit with error if any tests failed
    if any(r.status in ['fail', 'error'] for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
