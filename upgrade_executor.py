"""Execution module for performing upgrades via Leapp or Ansible."""

import subprocess
import os
from typing import Optional
from system_detector import SystemInfo
from upgrade_paths import UpgradePath


class UpgradeExecutor:
    """Executes upgrades using Leapp or Ansible."""

    def __init__(self, system: SystemInfo, upgrade_path: UpgradePath):
        self.system = system
        self.upgrade_path = upgrade_path

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
            print("Running Leapp pre-upgrade assessment...")
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
                    'output': preupgrade_result.stdout + preupgrade_result.stderr
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
                'output': upgrade_result.stdout
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
        playbook_path = self._generate_fedora_playbook()

        try:
            print(f"Generated Ansible playbook: {playbook_path}")
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
                'playbook': playbook_path
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
