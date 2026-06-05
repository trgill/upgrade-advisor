#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0

"""VM lifecycle management for upgrade testing."""

import subprocess
import json
import os
import time
import yaml
import hashlib
from dataclasses import dataclass
from typing import Optional, List, Dict
from pathlib import Path
from enum import Enum


class VMState(Enum):
    """VM states."""
    RUNNING = "running"
    SHUT_OFF = "shut off"
    PAUSED = "paused"
    CRASHED = "crashed"
    UNKNOWN = "unknown"


@dataclass
class VMTemplate:
    """VM template information."""
    name: str
    os_variant: str
    os_version: str
    profile: str  # minimal, server, workstation
    disk_path: str
    memory_mb: int
    vcpus: int
    created_at: str
    iso_checksum: Optional[str] = None


@dataclass
class VMInstance:
    """Running VM instance."""
    name: str
    template: str
    disk_path: str
    state: VMState
    ip_address: Optional[str] = None
    ssh_port: int = 22


class VMManager:
    """Manages QEMU/KVM virtual machines for testing."""

    def __init__(self, config_path: str = "vm_test_framework/config.yaml"):
        """Initialize VM manager with configuration."""
        self.config = self._load_config(config_path)
        self.storage_pool = Path(self.config.get('storage_pool', '/var/lib/libvirt/images/upgrade-test'))
        self.templates_dir = self.storage_pool / 'templates'
        self.instances_dir = self.storage_pool / 'instances'
        self.iso_cache = Path(self.config.get('iso_cache', '/var/lib/libvirt/images/isos'))

        # Ensure directories exist
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.instances_dir.mkdir(parents=True, exist_ok=True)
        self.iso_cache.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        if os.path.exists(config_path):
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}

    def create_template(self, os_name: str, os_version: str, profile: str = "minimal",
                       iso_path: Optional[str] = None, kickstart_path: Optional[str] = None) -> VMTemplate:
        """
        Create a new VM template from ISO using kickstart.

        Args:
            os_name: OS name (rhel, fedora)
            os_version: Version (8.9, 9.3, 40, etc.)
            profile: Installation profile (minimal, server, workstation)
            iso_path: Path to installation ISO
            kickstart_path: Path to kickstart file (auto-generated if not provided)

        Returns:
            VMTemplate object
        """
        template_name = f"{os_name}-{os_version}-{profile}"
        disk_path = self.templates_dir / f"{template_name}.qcow2"

        print(f"Creating template: {template_name}")

        # Generate kickstart if not provided
        if not kickstart_path:
            kickstart_path = self._generate_kickstart(os_name, os_version, profile)

        # Determine OS variant for virt-install
        os_variant = self._get_os_variant(os_name, os_version)

        # Create disk image
        subprocess.run([
            'qemu-img', 'create', '-f', 'qcow2',
            str(disk_path), '20G'
        ], check=True)

        # Build virt-install command
        virt_install_cmd = [
            'virt-install',
            '--name', template_name,
            '--memory', '2048',
            '--vcpus', '2',
            '--disk', f'path={disk_path},format=qcow2',
            '--os-variant', os_variant,
            '--network', 'network=default',
            '--graphics', 'none',
            '--console', 'pty,target_type=serial',
            '--location', iso_path,
            '--initrd-inject', kickstart_path,
            '--extra-args', f'inst.ks=file:/{os.path.basename(kickstart_path)} console=ttyS0',
            '--wait', '-1',  # Wait for installation to complete
            '--noreboot'
        ]

        print(f"Running virt-install (this may take 10-20 minutes)...")
        print(f"Command: {' '.join(virt_install_cmd)}")

        try:
            result = subprocess.run(virt_install_cmd, capture_output=True, text=True, timeout=3600)
            if result.returncode != 0:
                raise RuntimeError(f"virt-install failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("⚠ Installation timed out after 60 minutes")
            self._destroy_vm(template_name, force=True)
            raise

        # Undefine the VM but keep the disk
        print("Installation complete, cleaning up VM definition...")
        subprocess.run(['virsh', 'undefine', template_name], check=False)

        # Create template metadata
        template = VMTemplate(
            name=template_name,
            os_variant=os_variant,
            os_version=os_version,
            profile=profile,
            disk_path=str(disk_path),
            memory_mb=2048,
            vcpus=2,
            created_at=time.strftime('%Y-%m-%d %H:%M:%S'),
            iso_checksum=self._get_file_checksum(iso_path) if iso_path else None
        )

        # Save template metadata
        self._save_template_metadata(template)

        print(f"✓ Template created: {template_name}")
        return template

    def clone_vm(self, template_name: str, instance_name: str,
                 memory_mb: Optional[int] = None, vcpus: Optional[int] = None) -> VMInstance:
        """
        Clone a template to create a new test VM instance.

        Uses copy-on-write (qcow2 backing file) for fast cloning.
        """
        template = self._load_template_metadata(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        instance_disk = self.instances_dir / f"{instance_name}.qcow2"

        print(f"Cloning template {template_name} -> {instance_name}")

        # Create copy-on-write disk based on template
        subprocess.run([
            'qemu-img', 'create', '-f', 'qcow2',
            '-F', 'qcow2',
            '-b', template.disk_path,
            str(instance_disk)
        ], check=True)

        # Create VM definition
        memory = memory_mb or template.memory_mb
        cpus = vcpus or template.vcpus

        virt_install_cmd = [
            'virt-install',
            '--name', instance_name,
            '--memory', str(memory),
            '--vcpus', str(cpus),
            '--disk', f'path={instance_disk},format=qcow2',
            '--os-variant', template.os_variant,
            '--network', 'network=default',
            '--graphics', 'none',
            '--console', 'pty,target_type=serial',
            '--import',
            '--noautoconsole'
        ]

        subprocess.run(virt_install_cmd, check=True)

        instance = VMInstance(
            name=instance_name,
            template=template_name,
            disk_path=str(instance_disk),
            state=VMState.SHUT_OFF
        )

        print(f"✓ VM cloned: {instance_name}")
        return instance

    def start_vm(self, vm_name: str, wait_for_boot: bool = True) -> VMInstance:
        """Start a VM and optionally wait for it to boot."""
        print(f"Starting VM: {vm_name}")
        subprocess.run(['virsh', 'start', vm_name], check=True)

        if wait_for_boot:
            print("Waiting for VM to boot...")
            time.sleep(30)  # Basic wait, could be improved with SSH polling

        return self.get_vm_info(vm_name)

    def stop_vm(self, vm_name: str, force: bool = False):
        """Stop a VM (graceful shutdown or force)."""
        if force:
            print(f"Force stopping VM: {vm_name}")
            subprocess.run(['virsh', 'destroy', vm_name], check=False)
        else:
            print(f"Shutting down VM: {vm_name}")
            subprocess.run(['virsh', 'shutdown', vm_name], check=True)

            # Wait for shutdown
            for _ in range(60):
                state = self.get_vm_state(vm_name)
                if state == VMState.SHUT_OFF:
                    break
                time.sleep(1)

    def destroy_vm(self, vm_name: str, delete_disk: bool = True):
        """Destroy a VM and optionally delete its disk."""
        print(f"Destroying VM: {vm_name}")

        # Stop VM if running
        state = self.get_vm_state(vm_name)
        if state != VMState.SHUT_OFF:
            self.stop_vm(vm_name, force=True)

        # Get disk path before undefining
        disk_path = None
        if delete_disk:
            try:
                result = subprocess.run(
                    ['virsh', 'domblklist', vm_name, '--details'],
                    capture_output=True, text=True, check=True
                )
                for line in result.stdout.split('\n'):
                    if 'disk' in line and 'file' in line:
                        parts = line.split()
                        disk_path = parts[-1]
                        break
            except Exception as e:
                print(f"⚠ Could not get disk path: {e}")

        # Undefine VM
        self._destroy_vm(vm_name, force=True)

        # Delete disk
        if delete_disk and disk_path and os.path.exists(disk_path):
            print(f"Deleting disk: {disk_path}")
            os.remove(disk_path)

        print(f"✓ VM destroyed: {vm_name}")

    def _destroy_vm(self, vm_name: str, force: bool = False):
        """Internal method to undefine VM."""
        cmd = ['virsh', 'undefine', vm_name]
        if force:
            cmd.append('--nvram')  # Also remove NVRAM if it exists
        subprocess.run(cmd, check=False)

    def snapshot_vm(self, vm_name: str, snapshot_name: str, description: str = "") -> str:
        """Create a snapshot of a VM."""
        print(f"Creating snapshot: {snapshot_name} for VM {vm_name}")

        cmd = [
            'virsh', 'snapshot-create-as', vm_name,
            snapshot_name,
            '--description', description or f"Snapshot {snapshot_name}",
            '--atomic'
        ]

        subprocess.run(cmd, check=True)
        print(f"✓ Snapshot created: {snapshot_name}")
        return snapshot_name

    def restore_snapshot(self, vm_name: str, snapshot_name: str):
        """Restore a VM to a snapshot."""
        print(f"Restoring VM {vm_name} to snapshot {snapshot_name}")

        # Stop VM if running
        state = self.get_vm_state(vm_name)
        if state == VMState.RUNNING:
            self.stop_vm(vm_name, force=True)

        subprocess.run([
            'virsh', 'snapshot-revert', vm_name, snapshot_name
        ], check=True)

        print(f"✓ Snapshot restored: {snapshot_name}")

    def list_snapshots(self, vm_name: str) -> List[str]:
        """List all snapshots for a VM."""
        result = subprocess.run(
            ['virsh', 'snapshot-list', vm_name, '--name'],
            capture_output=True, text=True, check=True
        )
        return [s.strip() for s in result.stdout.split('\n') if s.strip()]

    def get_vm_state(self, vm_name: str) -> VMState:
        """Get current state of a VM."""
        try:
            result = subprocess.run(
                ['virsh', 'domstate', vm_name],
                capture_output=True, text=True, check=True
            )
            state_str = result.stdout.strip()

            state_map = {
                'running': VMState.RUNNING,
                'shut off': VMState.SHUT_OFF,
                'paused': VMState.PAUSED,
                'crashed': VMState.CRASHED
            }
            return state_map.get(state_str, VMState.UNKNOWN)
        except subprocess.CalledProcessError:
            return VMState.UNKNOWN

    def get_vm_info(self, vm_name: str) -> Optional[VMInstance]:
        """Get detailed information about a VM."""
        try:
            result = subprocess.run(
                ['virsh', 'dominfo', vm_name],
                capture_output=True, text=True, check=True
            )

            # Parse output (simplified)
            state = self.get_vm_state(vm_name)

            # Try to get IP address
            ip_address = self._get_vm_ip(vm_name)

            return VMInstance(
                name=vm_name,
                template="unknown",  # Would need to track this in metadata
                disk_path="unknown",
                state=state,
                ip_address=ip_address
            )
        except subprocess.CalledProcessError:
            return None

    def _get_vm_ip(self, vm_name: str) -> Optional[str]:
        """Try to get VM's IP address via DHCP lease."""
        try:
            result = subprocess.run(
                ['virsh', 'domifaddr', vm_name],
                capture_output=True, text=True, check=True
            )

            for line in result.stdout.split('\n'):
                if 'ipv4' in line.lower():
                    parts = line.split()
                    for part in parts:
                        if '/' in part:  # IP with CIDR
                            return part.split('/')[0]
            return None
        except Exception:
            return None

    def list_templates(self) -> List[VMTemplate]:
        """List all available templates."""
        templates = []
        metadata_dir = self.templates_dir / 'metadata'

        if metadata_dir.exists():
            for meta_file in metadata_dir.glob('*.json'):
                template = self._load_template_metadata(meta_file.stem)
                if template:
                    templates.append(template)

        return templates

    def list_instances(self) -> List[str]:
        """List all VM instances (running or stopped)."""
        result = subprocess.run(
            ['virsh', 'list', '--all', '--name'],
            capture_output=True, text=True, check=True
        )
        return [vm.strip() for vm in result.stdout.split('\n') if vm.strip()]

    def _save_template_metadata(self, template: VMTemplate):
        """Save template metadata to JSON."""
        metadata_dir = self.templates_dir / 'metadata'
        metadata_dir.mkdir(exist_ok=True)

        metadata_file = metadata_dir / f"{template.name}.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                'name': template.name,
                'os_variant': template.os_variant,
                'os_version': template.os_version,
                'profile': template.profile,
                'disk_path': template.disk_path,
                'memory_mb': template.memory_mb,
                'vcpus': template.vcpus,
                'created_at': template.created_at,
                'iso_checksum': template.iso_checksum
            }, f, indent=2)

    def _load_template_metadata(self, template_name: str) -> Optional[VMTemplate]:
        """Load template metadata from JSON."""
        metadata_file = self.templates_dir / 'metadata' / f"{template_name}.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file) as f:
            data = json.load(f)
            return VMTemplate(**data)

    def _generate_kickstart(self, os_name: str, os_version: str, profile: str) -> str:
        """Generate a kickstart file for automated installation."""
        kickstart_dir = Path('vm_test_framework/kickstart_templates')
        kickstart_dir.mkdir(parents=True, exist_ok=True)

        kickstart_file = kickstart_dir / f"{os_name}-{os_version}-{profile}.ks"

        # Basic kickstart template
        kickstart_content = f"""# Kickstart for {os_name} {os_version} - {profile}
# Auto-generated by VM Test Framework

# System authorization
auth --enableshadow --passalgo=sha512

# Use text install
text

# Disable Setup Agent on first boot
firstboot --disable

# Keyboard and language
keyboard --vckeymap=us --xlayouts='us'
lang en_US.UTF-8

# Network configuration
network --bootproto=dhcp --device=eth0 --onboot=on --ipv6=auto --activate
network --hostname=test-vm.local

# Root password (change in production!)
rootpw --plaintext testpassword

# System timezone
timezone America/New_York --utc

# Disk partitioning
clearpart --all --initlabel
autopart --type=lvm

# Bootloader
bootloader --location=mbr --boot-drive=vda

# Package selection
%packages --ignoremissing
@core
@base
"""

        if profile == 'server':
            kickstart_content += """@server-product-environment
httpd
"""
        elif profile == 'workstation':
            kickstart_content += """@workstation-product-environment
"""

        kickstart_content += """
# Minimal packages for testing
python3
openssh-server
vim
%end

# Post-installation script
%post --log=/root/ks-post.log
# Enable SSH
systemctl enable sshd

# Create test user
useradd -m testuser
echo "testuser:testpassword" | chpasswd

# Allow root SSH (for testing only!)
sed -i 's/#PermitRootLogin yes/PermitRootLogin yes/' /etc/ssh/sshd_config
%end

# Reboot after installation
reboot
"""

        with open(kickstart_file, 'w') as f:
            f.write(kickstart_content)

        print(f"Generated kickstart: {kickstart_file}")
        return str(kickstart_file)

    def _get_os_variant(self, os_name: str, os_version: str) -> str:
        """Map OS name and version to virt-install os-variant."""
        if os_name == 'rhel':
            major = os_version.split('.')[0]
            return f'rhel{major}.0'
        elif os_name == 'fedora':
            return f'fedora{os_version}'
        else:
            return 'linux2020'  # Generic fallback

    def _get_file_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


def main():
    """CLI interface for VM manager."""
    import argparse

    parser = argparse.ArgumentParser(description='VM Test Framework - VM Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # create-template command
    create_parser = subparsers.add_parser('create-template', help='Create a new VM template')
    create_parser.add_argument('--os', required=True, help='OS name (rhel, fedora)')
    create_parser.add_argument('--version', required=True, help='OS version (9.3, 40, etc.)')
    create_parser.add_argument('--profile', default='minimal', help='Profile (minimal, server, workstation)')
    create_parser.add_argument('--iso', required=True, help='Path to installation ISO')
    create_parser.add_argument('--kickstart', help='Path to kickstart file (optional)')

    # list-templates command
    subparsers.add_parser('list-templates', help='List all templates')

    # clone command
    clone_parser = subparsers.add_parser('clone', help='Clone a template')
    clone_parser.add_argument('--template', required=True, help='Template name')
    clone_parser.add_argument('--name', required=True, help='Instance name')

    # list command
    subparsers.add_parser('list', help='List all VMs')

    # destroy command
    destroy_parser = subparsers.add_parser('destroy', help='Destroy a VM')
    destroy_parser.add_argument('--vm', required=True, help='VM name')
    destroy_parser.add_argument('--keep-disk', action='store_true', help='Keep disk image')

    args = parser.parse_args()

    manager = VMManager()

    if args.command == 'create-template':
        template = manager.create_template(
            args.os, args.version, args.profile,
            iso_path=args.iso, kickstart_path=args.kickstart
        )
        print(f"\n✓ Template created: {template.name}")
        print(f"  Disk: {template.disk_path}")

    elif args.command == 'list-templates':
        templates = manager.list_templates()
        print(f"\nAvailable templates ({len(templates)}):")
        for t in templates:
            print(f"  - {t.name} ({t.os_version}, {t.profile})")
            print(f"    Created: {t.created_at}")
            print(f"    Disk: {t.disk_path}")

    elif args.command == 'clone':
        instance = manager.clone_vm(args.template, args.name)
        print(f"\n✓ VM cloned: {instance.name}")

    elif args.command == 'list':
        instances = manager.list_instances()
        print(f"\nVM Instances ({len(instances)}):")
        for vm_name in instances:
            state = manager.get_vm_state(vm_name)
            print(f"  - {vm_name}: {state.value}")

    elif args.command == 'destroy':
        manager.destroy_vm(args.vm, delete_disk=not args.keep_disk)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
