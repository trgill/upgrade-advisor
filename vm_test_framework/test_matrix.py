#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0

"""Test matrix configuration and generation."""

import yaml
import itertools
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path


@dataclass
class PackageSet:
    """Package configuration for testing."""
    name: str
    packages: List[str]
    services: List[str] = field(default_factory=list)
    repos: List[str] = field(default_factory=list)
    pre_install_commands: List[str] = field(default_factory=list)


@dataclass
class StorageLayout:
    """Storage/partition layout configuration."""
    name: str
    type: str  # 'standard', 'lvm', 'lvm_thin', 'btrfs'
    description: str
    kickstart_snippet: Optional[str] = None


@dataclass
class ValidationCheck:
    """Post-upgrade validation check."""
    name: str
    type: str  # 'service', 'package', 'file', 'command', 'custom'
    target: str
    expected: Any
    critical: bool = True  # If False, failure is a warning


@dataclass
class TestCase:
    """Individual test case configuration."""
    name: str
    source_os: str
    source_version: str
    target_os: str
    target_version: str
    profile: str  # minimal, server, workstation
    package_set: PackageSet
    storage_layout: StorageLayout
    validations: List[ValidationCheck] = field(default_factory=list)
    timeout_minutes: int = 60
    tags: List[str] = field(default_factory=list)

    def get_test_id(self) -> str:
        """Generate unique test ID."""
        return f"{self.source_os}{self.source_version}-{self.target_os}{self.target_version}-{self.profile}-{self.package_set.name}-{self.storage_layout.name}".replace('.', '_')


class TestMatrix:
    """Generates and manages test matrices."""

    # Predefined package sets
    PACKAGE_SETS = {
        'minimal': PackageSet(
            name='minimal',
            packages=[],
            services=[]
        ),
        'web_server': PackageSet(
            name='web_server',
            packages=['httpd', 'mod_ssl', 'php'],
            services=['httpd'],
            pre_install_commands=[
                'systemctl enable httpd',
                'echo "Test Page" > /var/www/html/index.html'
            ]
        ),
        'database': PackageSet(
            name='database',
            packages=['postgresql-server', 'postgresql-contrib'],
            services=['postgresql'],
            pre_install_commands=[
                'postgresql-setup --initdb',
                'systemctl enable postgresql'
            ]
        ),
        'development': PackageSet(
            name='development',
            packages=['gcc', 'make', 'git', 'python3-devel', 'nodejs'],
            services=[]
        ),
        'container_host': PackageSet(
            name='container_host',
            packages=['podman', 'buildah', 'skopeo'],
            services=['podman'],
            pre_install_commands=[
                'podman pull registry.access.redhat.com/ubi9/ubi:latest'
            ]
        ),
        'third_party': PackageSet(
            name='third_party',
            packages=['epel-release', 'htop', 'tmux'],
            repos=['epel'],
            pre_install_commands=[
                'dnf install -y epel-release',
                'dnf install -y htop tmux'
            ]
        )
    }

    # Predefined storage layouts
    STORAGE_LAYOUTS = {
        'standard': StorageLayout(
            name='standard',
            type='standard',
            description='Standard partitions without LVM'
        ),
        'lvm_default': StorageLayout(
            name='lvm_default',
            type='lvm',
            description='Default LVM layout (/, /boot, swap)'
        ),
        'lvm_separate_home': StorageLayout(
            name='lvm_separate_home',
            type='lvm',
            description='LVM with separate /home partition'
        ),
        'lvm_thin': StorageLayout(
            name='lvm_thin',
            type='lvm_thin',
            description='LVM thin provisioning'
        ),
        'btrfs': StorageLayout(
            name='btrfs',
            type='btrfs',
            description='Btrfs filesystem with snapshots'
        )
    }

    # Predefined validation checks
    COMMON_VALIDATIONS = {
        'boot': ValidationCheck(
            name='system_boots',
            type='command',
            target='uptime',
            expected='success',
            critical=True
        ),
        'network': ValidationCheck(
            name='network_active',
            type='command',
            target='ping -c 1 8.8.8.8',
            expected='success',
            critical=True
        ),
        'selinux': ValidationCheck(
            name='selinux_enforcing',
            type='command',
            target='getenforce',
            expected='Enforcing',
            critical=False
        ),
        'disk_space': ValidationCheck(
            name='sufficient_disk_space',
            type='command',
            target='df -h / | tail -1 | awk \'{print $5}\'',
            expected='< 90%',
            critical=False
        )
    }

    def __init__(self):
        """Initialize test matrix generator."""
        pass

    @staticmethod
    def from_yaml(config_path: str) -> List[TestCase]:
        """Load test matrix from YAML configuration."""
        with open(config_path) as f:
            config = yaml.safe_load(f)

        test_cases = []
        base_config = config.get('base', {})

        for variant in config.get('variants', []):
            # Get package set
            package_set_name = variant.get('package_set', 'minimal')
            if package_set_name in TestMatrix.PACKAGE_SETS:
                package_set = TestMatrix.PACKAGE_SETS[package_set_name]
            else:
                # Custom package set
                package_set = PackageSet(
                    name=variant.get('name', 'custom'),
                    packages=variant.get('packages', []),
                    services=variant.get('services', []),
                    repos=variant.get('repos', []),
                    pre_install_commands=variant.get('pre_install_commands', [])
                )

            # Get storage layouts
            storage_layouts = variant.get('storage_layouts', ['lvm_default'])
            for layout_name in storage_layouts:
                layout = TestMatrix.STORAGE_LAYOUTS.get(layout_name, TestMatrix.STORAGE_LAYOUTS['lvm_default'])

                # Build validations
                validations = [TestMatrix.COMMON_VALIDATIONS['boot']]

                # Add service checks
                for service in package_set.services:
                    validations.append(ValidationCheck(
                        name=f'service_{service}',
                        type='service',
                        target=service,
                        expected='active',
                        critical=True
                    ))

                # Add custom validations from variant
                for val_config in variant.get('validations', []):
                    validations.append(ValidationCheck(
                        name=val_config.get('name', 'custom'),
                        type=val_config.get('type', 'command'),
                        target=val_config.get('target', ''),
                        expected=val_config.get('expected', 'success'),
                        critical=val_config.get('critical', True)
                    ))

                # Create test case
                test_case = TestCase(
                    name=variant.get('name', package_set.name),
                    source_os=base_config.get('source_os', 'rhel'),
                    source_version=base_config.get('source_version', '9'),
                    target_os=base_config.get('target_os', 'rhel'),
                    target_version=base_config.get('target_version', '10'),
                    profile=variant.get('profile', 'minimal'),
                    package_set=package_set,
                    storage_layout=layout,
                    validations=validations,
                    timeout_minutes=variant.get('timeout_minutes', 60),
                    tags=variant.get('tags', [])
                )

                test_cases.append(test_case)

        return test_cases

    @staticmethod
    def generate_full_matrix(source_versions: List[str], target_versions: List[str],
                            profiles: List[str] = None, package_sets: List[str] = None,
                            storage_layouts: List[str] = None) -> List[TestCase]:
        """
        Generate a full combinatorial test matrix.

        Warning: This can generate a LOT of tests!
        """
        if profiles is None:
            profiles = ['minimal', 'server']
        if package_sets is None:
            package_sets = ['minimal', 'web_server']
        if storage_layouts is None:
            storage_layouts = ['lvm_default']

        test_cases = []

        for (src_ver, tgt_ver, profile, pkg_set_name, layout_name) in itertools.product(
            source_versions, target_versions, profiles, package_sets, storage_layouts
        ):
            package_set = TestMatrix.PACKAGE_SETS.get(pkg_set_name)
            layout = TestMatrix.STORAGE_LAYOUTS.get(layout_name)

            if not package_set or not layout:
                continue

            # Build validations
            validations = [TestMatrix.COMMON_VALIDATIONS['boot']]
            for service in package_set.services:
                validations.append(ValidationCheck(
                    name=f'service_{service}',
                    type='service',
                    target=service,
                    expected='active',
                    critical=True
                ))

            test_case = TestCase(
                name=f"{pkg_set_name}_{layout_name}",
                source_os='rhel',
                source_version=src_ver,
                target_os='rhel',
                target_version=tgt_ver,
                profile=profile,
                package_set=package_set,
                storage_layout=layout,
                validations=validations,
                tags=['auto-generated']
            )

            test_cases.append(test_case)

        return test_cases

    @staticmethod
    def save_matrix_to_yaml(test_cases: List[TestCase], output_path: str):
        """Save test matrix to YAML file."""
        matrix_config = {
            'matrix_name': 'Generated Test Matrix',
            'base': {
                'source_os': test_cases[0].source_os if test_cases else 'rhel',
                'target_os': test_cases[0].target_os if test_cases else 'rhel',
            },
            'variants': []
        }

        for tc in test_cases:
            variant = {
                'name': tc.name,
                'profile': tc.profile,
                'package_set': tc.package_set.name,
                'packages': tc.package_set.packages,
                'services': tc.package_set.services,
                'storage_layouts': [tc.storage_layout.name],
                'timeout_minutes': tc.timeout_minutes,
                'tags': tc.tags,
                'validations': [
                    {
                        'name': v.name,
                        'type': v.type,
                        'target': v.target,
                        'expected': v.expected,
                        'critical': v.critical
                    }
                    for v in tc.validations
                ]
            }
            matrix_config['variants'].append(variant)

        with open(output_path, 'w') as f:
            yaml.dump(matrix_config, f, default_flow_style=False, sort_keys=False)

    @staticmethod
    def filter_tests(test_cases: List[TestCase], tags: List[str] = None,
                    profile: str = None, source_version: str = None) -> List[TestCase]:
        """Filter test cases based on criteria."""
        filtered = test_cases

        if tags:
            filtered = [tc for tc in filtered if any(tag in tc.tags for tag in tags)]

        if profile:
            filtered = [tc for tc in filtered if tc.profile == profile]

        if source_version:
            filtered = [tc for tc in filtered if tc.source_version == source_version]

        return filtered

    @staticmethod
    def print_matrix_summary(test_cases: List[TestCase]):
        """Print a summary of the test matrix."""
        print(f"\n=== Test Matrix Summary ===")
        print(f"Total test cases: {len(test_cases)}\n")

        # Group by upgrade path
        upgrade_paths = {}
        for tc in test_cases:
            path = f"{tc.source_os} {tc.source_version} → {tc.target_os} {tc.target_version}"
            if path not in upgrade_paths:
                upgrade_paths[path] = []
            upgrade_paths[path].append(tc)

        for path, cases in upgrade_paths.items():
            print(f"  {path}: {len(cases)} tests")
            profiles = {}
            for tc in cases:
                if tc.profile not in profiles:
                    profiles[tc.profile] = 0
                profiles[tc.profile] += 1

            for profile, count in profiles.items():
                print(f"    - {profile}: {count}")

        print(f"\n=== Package Sets ===")
        pkg_sets = set(tc.package_set.name for tc in test_cases)
        for pkg_set in sorted(pkg_sets):
            count = len([tc for tc in test_cases if tc.package_set.name == pkg_set])
            print(f"  - {pkg_set}: {count} tests")

        print(f"\n=== Storage Layouts ===")
        layouts = set(tc.storage_layout.name for tc in test_cases)
        for layout in sorted(layouts):
            count = len([tc for tc in test_cases if tc.storage_layout.name == layout])
            print(f"  - {layout}: {count} tests")


def main():
    """CLI for test matrix generation."""
    import argparse

    parser = argparse.ArgumentParser(description='VM Test Framework - Test Matrix Generator')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # from-yaml command
    yaml_parser = subparsers.add_parser('from-yaml', help='Load test matrix from YAML')
    yaml_parser.add_argument('config', help='Path to YAML config file')
    yaml_parser.add_argument('--save', help='Save to output file')

    # generate command
    gen_parser = subparsers.add_parser('generate', help='Generate full test matrix')
    gen_parser.add_argument('--source-versions', nargs='+', default=['9.3'],
                           help='Source versions (e.g., 9.3 8.9)')
    gen_parser.add_argument('--target-versions', nargs='+', default=['10.0'],
                           help='Target versions (e.g., 10.0)')
    gen_parser.add_argument('--profiles', nargs='+', default=['minimal', 'server'],
                           help='Installation profiles')
    gen_parser.add_argument('--package-sets', nargs='+',
                           default=['minimal', 'web_server', 'database'],
                           help='Package sets to test')
    gen_parser.add_argument('--storage-layouts', nargs='+',
                           default=['lvm_default'],
                           help='Storage layouts to test')
    gen_parser.add_argument('--save', help='Save to output file')

    # example command
    subparsers.add_parser('example', help='Generate example YAML configuration')

    args = parser.parse_args()

    if args.command == 'from-yaml':
        test_cases = TestMatrix.from_yaml(args.config)
        TestMatrix.print_matrix_summary(test_cases)

        if args.save:
            TestMatrix.save_matrix_to_yaml(test_cases, args.save)
            print(f"\n✓ Matrix saved to: {args.save}")

    elif args.command == 'generate':
        test_cases = TestMatrix.generate_full_matrix(
            source_versions=args.source_versions,
            target_versions=args.target_versions,
            profiles=args.profiles,
            package_sets=args.package_sets,
            storage_layouts=args.storage_layouts
        )

        TestMatrix.print_matrix_summary(test_cases)

        if args.save:
            TestMatrix.save_matrix_to_yaml(test_cases, args.save)
            print(f"\n✓ Matrix saved to: {args.save}")

    elif args.command == 'example':
        example_config = """# Example Test Matrix Configuration
name: "RHEL 9 to RHEL 10 Upgrade Suite"

base:
  source_os: rhel
  source_version: "9.3"
  target_os: rhel
  target_version: "10.0"

variants:
  - name: minimal-install
    profile: minimal
    package_set: minimal
    storage_layouts:
      - lvm_default
    timeout_minutes: 60
    tags:
      - smoke
      - minimal

  - name: web-server
    profile: server
    package_set: web_server
    storage_layouts:
      - lvm_default
      - lvm_separate_home
    validations:
      - name: http_response
        type: command
        target: curl -s http://localhost
        expected: "Test Page"
        critical: true
    tags:
      - server
      - web

  - name: database-server
    profile: server
    package_set: database
    storage_layouts:
      - lvm_default
    timeout_minutes: 90
    tags:
      - server
      - database

  - name: development-workstation
    profile: workstation
    package_set: development
    storage_layouts:
      - lvm_default
    validations:
      - name: gcc_installed
        type: command
        target: gcc --version
        expected: success
        critical: true
    tags:
      - workstation
      - development
"""
        print(example_config)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
