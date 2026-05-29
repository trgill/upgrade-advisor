"""Rollback management using boom-boot and snapm for safe bailout."""

import subprocess
import os
import json
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class RollbackPoint:
    """Represents a rollback point created before upgrade."""
    timestamp: str
    method: str  # 'boom', 'snapm', 'lvm', 'btrfs'
    identifier: str
    description: str
    metadata: Dict


class RollbackManager:
    """Manages rollback points for safe upgrade bailout."""

    ROLLBACK_STATE_FILE = '/var/lib/upgrade-advisor/rollback-state.json'

    @staticmethod
    def create_pre_upgrade_snapshot(method: str = 'auto', description: str = None) -> Optional[RollbackPoint]:
        """Create a pre-upgrade snapshot using best available method."""
        if method == 'auto':
            method = RollbackManager._select_best_method()

        if not description:
            description = f"Pre-upgrade snapshot created {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        if method == 'snapm':
            return RollbackManager._create_snapm_snapshot(description)
        elif method == 'boom':
            return RollbackManager._create_boom_entry(description)
        elif method == 'lvm':
            return RollbackManager._create_lvm_snapshot(description)
        elif method == 'btrfs':
            return RollbackManager._create_btrfs_snapshot(description)
        else:
            raise ValueError(f"Unsupported rollback method: {method}")

    @staticmethod
    def _select_best_method() -> str:
        """Select the best available rollback method."""
        if os.path.exists('/usr/bin/snapm'):
            return 'snapm'
        elif os.path.exists('/usr/bin/boom'):
            return 'boom'
        elif RollbackManager._check_lvm_available():
            return 'lvm'
        elif RollbackManager._check_btrfs_available():
            return 'btrfs'
        else:
            raise RuntimeError("No rollback methods available on this system")

    @staticmethod
    def _create_snapm_snapshot(description: str) -> RollbackPoint:
        """Create snapshot using snapm."""
        try:
            snapshot_name = f"upgrade-advisor-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            result = subprocess.run(
                ['snapm', 'create', '--name', snapshot_name, '--description', description],
                capture_output=True,
                text=True,
                check=True
            )

            rollback_point = RollbackPoint(
                timestamp=datetime.now().isoformat(),
                method='snapm',
                identifier=snapshot_name,
                description=description,
                metadata={
                    'output': result.stdout,
                    'command': f'snapm create --name {snapshot_name}'
                }
            )

            RollbackManager._save_rollback_point(rollback_point)
            return rollback_point

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create snapm snapshot: {e.stderr}")

    @staticmethod
    def _create_boom_entry(description: str) -> RollbackPoint:
        """Create boot entry using boom-boot."""
        try:
            entry_title = f"Pre-upgrade-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            result = subprocess.run(
                ['boom', 'create', '--title', entry_title, '--description', description],
                capture_output=True,
                text=True,
                check=True
            )

            boom_id = RollbackManager._extract_boom_id(result.stdout)

            rollback_point = RollbackPoint(
                timestamp=datetime.now().isoformat(),
                method='boom',
                identifier=boom_id,
                description=description,
                metadata={
                    'title': entry_title,
                    'output': result.stdout,
                    'command': f'boom create --title {entry_title}'
                }
            )

            RollbackManager._save_rollback_point(rollback_point)
            return rollback_point

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create boom entry: {e.stderr}")

    @staticmethod
    def _create_lvm_snapshot(description: str) -> RollbackPoint:
        """Create LVM snapshot manually."""
        try:
            root_vg = RollbackManager._detect_root_lv()
            if not root_vg:
                raise RuntimeError("Could not detect root LVM volume")

            snapshot_name = f"root_pre_upgrade_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            snapshot_size = "10G"

            result = subprocess.run(
                ['lvcreate', '-L', snapshot_size, '-s', '-n', snapshot_name, root_vg],
                capture_output=True,
                text=True,
                check=True
            )

            rollback_point = RollbackPoint(
                timestamp=datetime.now().isoformat(),
                method='lvm',
                identifier=snapshot_name,
                description=description,
                metadata={
                    'volume_group': root_vg,
                    'size': snapshot_size,
                    'output': result.stdout
                }
            )

            RollbackManager._save_rollback_point(rollback_point)
            return rollback_point

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create LVM snapshot: {e.stderr}")

    @staticmethod
    def _create_btrfs_snapshot(description: str) -> RollbackPoint:
        """Create Btrfs snapshot."""
        try:
            root_subvol = '/'
            snapshot_path = f'/.snapshots/pre_upgrade_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

            os.makedirs('/.snapshots', exist_ok=True)

            result = subprocess.run(
                ['btrfs', 'subvolume', 'snapshot', root_subvol, snapshot_path],
                capture_output=True,
                text=True,
                check=True
            )

            rollback_point = RollbackPoint(
                timestamp=datetime.now().isoformat(),
                method='btrfs',
                identifier=snapshot_path,
                description=description,
                metadata={
                    'subvolume': root_subvol,
                    'output': result.stdout
                }
            )

            RollbackManager._save_rollback_point(rollback_point)
            return rollback_point

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create Btrfs snapshot: {e.stderr}")

    @staticmethod
    def list_rollback_points() -> List[RollbackPoint]:
        """List available rollback points."""
        if not os.path.exists(RollbackManager.ROLLBACK_STATE_FILE):
            return []

        try:
            with open(RollbackManager.ROLLBACK_STATE_FILE, 'r') as f:
                data = json.load(f)
                return [RollbackPoint(**point) for point in data.get('rollback_points', [])]
        except Exception:
            return []

    @staticmethod
    def execute_rollback(identifier: str) -> bool:
        """Execute rollback to a specific point."""
        rollback_points = RollbackManager.list_rollback_points()
        target_point = next((rp for rp in rollback_points if rp.identifier == identifier), None)

        if not target_point:
            raise ValueError(f"Rollback point {identifier} not found")

        if target_point.method == 'snapm':
            return RollbackManager._rollback_snapm(target_point)
        elif target_point.method == 'boom':
            return RollbackManager._rollback_boom(target_point)
        elif target_point.method == 'lvm':
            return RollbackManager._rollback_lvm(target_point)
        elif target_point.method == 'btrfs':
            return RollbackManager._rollback_btrfs(target_point)
        else:
            raise ValueError(f"Unknown rollback method: {target_point.method}")

    @staticmethod
    def _rollback_snapm(rollback_point: RollbackPoint) -> bool:
        """Rollback using snapm."""
        try:
            subprocess.run(
                ['snapm', 'rollback', rollback_point.identifier],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"Snapm rollback to {rollback_point.identifier} initiated.")
            print("System will reboot to complete rollback.")
            return True
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Snapm rollback failed: {e.stderr}")

    @staticmethod
    def _rollback_boom(rollback_point: RollbackPoint) -> bool:
        """Set boom entry as default boot."""
        try:
            subprocess.run(
                ['boom', 'entry', '--set-default', rollback_point.identifier],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"Boom boot entry {rollback_point.identifier} set as default.")
            print("Reboot to use the pre-upgrade boot configuration.")
            return True
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Boom rollback failed: {e.stderr}")

    @staticmethod
    def _rollback_lvm(rollback_point: RollbackPoint) -> bool:
        """Rollback LVM snapshot (merge)."""
        try:
            print(f"WARNING: LVM snapshot rollback requires careful manual intervention.")
            print(f"To rollback, you need to:")
            print(f"1. Boot from rescue media")
            print(f"2. Run: lvconvert --merge {rollback_point.metadata['volume_group']}/{rollback_point.identifier}")
            print(f"3. Reboot")
            return False  # Requires manual intervention
        except Exception as e:
            raise RuntimeError(f"LVM rollback setup failed: {e}")

    @staticmethod
    def _rollback_btrfs(rollback_point: RollbackPoint) -> bool:
        """Rollback Btrfs snapshot."""
        print(f"To rollback Btrfs snapshot:")
        print(f"1. Boot from rescue media or snapshot")
        print(f"2. Mount btrfs filesystem")
        print(f"3. Set {rollback_point.identifier} as default subvolume")
        print(f"4. Reboot")
        return False  # Requires manual intervention

    @staticmethod
    def _save_rollback_point(rollback_point: RollbackPoint):
        """Save rollback point to state file."""
        os.makedirs(os.path.dirname(RollbackManager.ROLLBACK_STATE_FILE), exist_ok=True)

        data = {'rollback_points': []}
        if os.path.exists(RollbackManager.ROLLBACK_STATE_FILE):
            with open(RollbackManager.ROLLBACK_STATE_FILE, 'r') as f:
                data = json.load(f)

        data['rollback_points'].append({
            'timestamp': rollback_point.timestamp,
            'method': rollback_point.method,
            'identifier': rollback_point.identifier,
            'description': rollback_point.description,
            'metadata': rollback_point.metadata
        })

        with open(RollbackManager.ROLLBACK_STATE_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _extract_boom_id(boom_output: str) -> str:
        """Extract boom ID from boom command output."""
        for line in boom_output.split('\n'):
            if 'Boot Entry' in line or 'ID:' in line:
                parts = line.split()
                if parts:
                    return parts[-1]
        return f"boom-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    @staticmethod
    def _detect_root_lv() -> Optional[str]:
        """Detect root logical volume."""
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == '/':
                        device = parts[0]
                        if '/dev/mapper/' in device or '/dev/' in device:
                            return device
            return None
        except Exception:
            return None

    @staticmethod
    def _check_lvm_available() -> bool:
        """Check if LVM is available."""
        try:
            result = subprocess.run(
                ['lvs', '--noheadings'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _check_btrfs_available() -> bool:
        """Check if Btrfs is available."""
        try:
            result = subprocess.run(
                ['btrfs', 'filesystem', 'show'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
