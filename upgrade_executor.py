# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0

"""Execution module for performing upgrades via Leapp or Ansible."""

import subprocess
import os
from typing import Optional
from system_detector import SystemInfo, SystemDetector
from upgrade_paths import UpgradePath
from rollback_manager import RollbackManager


class UpgradeExecutor:
    """Executes upgrades using Leapp or Ansible."""

    def __init__(self, system: SystemInfo, upgrade_path: UpgradePath, create_rollback: bool = True):
        self.system = system
        self.upgrade_path = upgrade_path
        self.create_rollback = create_rollback
        self.rollback_point = None

    def prepare_upgrade(self) -> dict:
        """Prepare the system for upgrade."""
        results = {
            'method': self.upgrade_path.method,
            'ready': False,
            'actions_needed': []
        }

        if self.upgrade_path.method == 'leapp':
            results.update(self._prepare_leapp())
        elif self.upgrade_path.method == 'ansible':
            results.update(self._prepare_ansible())

        return results

    def _prepare_leapp(self) -> dict:
        """Prepare for Leapp upgrade."""
        actions = []

        if not os.path.exists('/usr/bin/leapp'):
            actions.append('Install leapp: dnf install -y leapp-upgrade')

        if self.system.os_id == 'rhel':
            actions.append('Ensure active RHEL subscription: subscription-manager status')

        actions.append('Run pre-upgrade check: leapp preupgrade')

        return {
            'ready': len(actions) == 0,
            'actions_needed': actions
        }

    def _prepare_ansible(self) -> dict:
        """Prepare for Ansible-based upgrade."""
        actions = []

        if not os.path.exists('/usr/bin/ansible-playbook'):
            actions.append('Install Ansible: dnf install -y ansible-core')

        if not os.path.exists('/usr/bin/dnf'):
            actions.append('DNF package manager required')

        return {
            'ready': len(actions) == 0,
            'actions_needed': actions
        }

    def execute_leapp_upgrade(self, auto_reboot: bool = False) -> dict:
        """Execute RHEL upgrade via Leapp."""
        try:
            if self.create_rollback:
                print("\n⚡ Creating pre-upgrade rollback point...")
                try:
                    rollback_caps = SystemDetector.check_rollback_capabilities()
                    if rollback_caps['boom_available'] or rollback_caps['snapm_available']:
                        self.rollback_point = RollbackManager.create_pre_upgrade_snapshot(
                            description=f"Pre-upgrade snapshot before {self.system.os_name} {self.upgrade_path.from_version} → {self.upgrade_path.to_version}"
                        )
                        print(f"✓ Rollback point created: {self.rollback_point.identifier} ({self.rollback_point.method})")
                    else:
                        print("⚠ No automatic rollback tools available (boom/snapm)")
                        print("  Consider creating manual LVM snapshot if needed")
                except Exception as e:
                    print(f"⚠ Warning: Could not create rollback point: {e}")
                    print("  Continuing without automatic rollback capability")

            print("\nRunning Leapp pre-upgrade assessment...")
            preupgrade_result = subprocess.run(
                ['leapp', 'preupgrade'],
                capture_output=True,
                text=True
            )

            if preupgrade_result.returncode != 0:
                return {
                    'success': False,
                    'phase': 'preupgrade',
                    'message': 'Pre-upgrade check failed',
                    'output': preupgrade_result.stdout + preupgrade_result.stderr,
                    'rollback_point': self.rollback_point.identifier if self.rollback_point else None
                }

            print("Pre-upgrade check passed. Review /var/log/leapp/leapp-report.txt")
            print("\nStarting upgrade process...")

            cmd = ['leapp', 'upgrade']
            if auto_reboot:
                cmd.append('--reboot')

            upgrade_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            return {
                'success': upgrade_result.returncode == 0,
                'phase': 'upgrade',
                'message': 'Upgrade initiated - system will reboot',
                'output': upgrade_result.stdout,
                'rollback_point': self.rollback_point.identifier if self.rollback_point else None
            }

        except FileNotFoundError:
            return {
                'success': False,
                'phase': 'execution',
                'message': 'Leapp not found - install leapp-upgrade package'
            }
        except Exception as e:
            return {
                'success': False,
                'phase': 'execution',
                'message': f'Error executing Leapp: {str(e)}'
            }

    def execute_ansible_upgrade(self) -> dict:
        """Execute Fedora upgrade via Ansible playbook."""
        if self.create_rollback:
            print("\n⚡ Creating pre-upgrade rollback point...")
            try:
                rollback_caps = SystemDetector.check_rollback_capabilities()
                if rollback_caps['boom_available'] or rollback_caps['snapm_available']:
                    self.rollback_point = RollbackManager.create_pre_upgrade_snapshot(
                        description=f"Pre-upgrade snapshot before Fedora {self.upgrade_path.from_version} → {self.upgrade_path.to_version}"
                    )
                    print(f"✓ Rollback point created: {self.rollback_point.identifier} ({self.rollback_point.method})")
                else:
                    print("⚠ No automatic rollback tools available (boom/snapm)")
            except Exception as e:
                print(f"⚠ Warning: Could not create rollback point: {e}")

        playbook_path = self._generate_fedora_playbook()

        try:
            print(f"\nGenerated Ansible playbook: {playbook_path}")
            print("Executing upgrade playbook...")

            result = subprocess.run(
                ['ansible-playbook', '-i', 'localhost,', '-c', 'local', playbook_path],
                capture_output=True,
                text=True
            )

            return {
                'success': result.returncode == 0,
                'phase': 'upgrade',
                'message': 'Ansible playbook executed',
                'output': result.stdout,
                'playbook': playbook_path,
                'rollback_point': self.rollback_point.identifier if self.rollback_point else None
            }

        except FileNotFoundError:
            return {
                'success': False,
                'phase': 'execution',
                'message': 'Ansible not found - install ansible-core package'
            }
        except Exception as e:
            return {
                'success': False,
                'phase': 'execution',
                'message': f'Error executing Ansible: {str(e)}'
            }

    def _generate_fedora_playbook(self) -> str:
        """Generate Ansible playbook for Fedora upgrade."""
        playbook_content = f"""---
- name: Fedora System Upgrade
  hosts: localhost
  become: yes
  tasks:
    - name: Update all packages
      dnf:
        name: "*"
        state: latest

    - name: Install dnf-plugin-system-upgrade
      dnf:
        name: dnf-plugin-system-upgrade
        state: present

    - name: Download Fedora {self.upgrade_path.to_version} packages
      command: dnf system-upgrade download --releasever={self.upgrade_path.to_version} --assumeyes
      register: download_result
      changed_when: download_result.rc == 0

    - name: Display download results
      debug:
        var: download_result.stdout_lines

    - name: Reboot and upgrade
      command: dnf system-upgrade reboot
      when: download_result.rc == 0
      async: 1
      poll: 0
      ignore_errors: yes
"""

        playbook_path = '/tmp/fedora-upgrade-playbook.yml'
        with open(playbook_path, 'w') as f:
            f.write(playbook_content)

        return playbook_path
