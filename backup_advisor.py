# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0

"""Backup recommendations for pre-upgrade safety."""

from dataclasses import dataclass
from typing import List
import os
from system_detector import SystemInfo, SystemDetector


@dataclass
class BackupRecommendation:
    """A specific backup recommendation."""
    priority: str  # 'critical', 'recommended', 'optional'
    target: str
    method: str
    reason: str
    estimated_size: str = 'Unknown'


class BackupAdvisor:
    """Provides backup recommendations before upgrade."""

    CRITICAL_PATHS = [
        '/etc',
        '/home',
        '/root',
        '/var/lib/mysql',
        '/var/lib/pgsql',
        '/var/www',
    ]

    OPTIONAL_PATHS = [
        '/opt',
        '/srv',
        '/usr/local',
    ]

    @staticmethod
    def get_recommendations(system: SystemInfo) -> List[BackupRecommendation]:
        """Generate backup recommendations for the system."""
        recommendations = []

        rollback_caps = SystemDetector.check_rollback_capabilities()

        if rollback_caps['snapm_available']:
            recommendations.append(BackupRecommendation(
                priority='critical',
                target='System snapshot (snapm)',
                method='snapm create --name pre-upgrade',
                reason='Atomic filesystem snapshot for instant rollback - RECOMMENDED',
                estimated_size='Uses CoW - minimal initial space'
            ))
        elif rollback_caps['boom_available']:
            recommendations.append(BackupRecommendation(
                priority='critical',
                target='Boot entry (boom-boot)',
                method='boom create --title "Pre-upgrade"',
                reason='Creates bootable rollback point - allows booting previous kernel/config',
                estimated_size='< 1 MB (metadata only)'
            ))

        recommendations.append(BackupRecommendation(
            priority='critical',
            target='Package list',
            method=f'{system.package_manager} list installed > /root/packages-backup.txt',
            reason='Allows reinstallation of packages if upgrade fails',
            estimated_size='< 1 MB'
        ))

        recommendations.append(BackupRecommendation(
            priority='critical',
            target='/etc directory',
            method='tar -czf /root/etc-backup.tar.gz /etc',
            reason='Contains all system configuration files',
            estimated_size='50-200 MB'
        ))

        recommendations.append(BackupRecommendation(
            priority='critical',
            target='/home directory',
            method='tar -czf /backup/home-backup.tar.gz /home',
            reason='User data and configurations',
            estimated_size='Varies (use du -sh /home)'
        ))

        recommendations.append(BackupRecommendation(
            priority='recommended',
            target='/var/log',
            method='tar -czf /root/logs-backup.tar.gz /var/log',
            reason='System logs for troubleshooting',
            estimated_size='100 MB - 1 GB'
        ))

        if system.is_rhel_based and not rollback_caps['snapm_available']:
            if rollback_caps['lvm_snapshots']:
                recommendations.append(BackupRecommendation(
                    priority='recommended',
                    target='System snapshot (LVM - manual)',
                    method='lvcreate -L 10G -s -n root_snapshot /dev/mapper/rhel-root',
                    reason='LVM snapshot for rollback (consider using snapm for easier management)',
                    estimated_size='10 GB (grows with changes)'
                ))
            if rollback_caps['btrfs_snapshots']:
                recommendations.append(BackupRecommendation(
                    priority='recommended',
                    target='System snapshot (Btrfs)',
                    method='btrfs subvolume snapshot / /.snapshots/pre-upgrade',
                    reason='Btrfs snapshot for rollback',
                    estimated_size='CoW - minimal initial space'
                ))

        recommendations.append(BackupRecommendation(
            priority='recommended',
            target='Database dumps',
            method='mysqldump --all-databases > /root/mysql-backup.sql',
            reason='If running databases, backup data before upgrade',
            estimated_size='Varies'
        ))

        recommendations.append(BackupRecommendation(
            priority='optional',
            target='/opt directory',
            method='tar -czf /root/opt-backup.tar.gz /opt',
            reason='Third-party applications',
            estimated_size='Varies'
        ))

        recommendations.append(BackupRecommendation(
            priority='critical',
            target='Boot configuration',
            method='cp -r /boot /root/boot-backup',
            reason='Allows recovery if bootloader is affected',
            estimated_size='200-500 MB'
        ))

        return recommendations

    @staticmethod
    def generate_backup_script(recommendations: List[BackupRecommendation],
                               priority_level: str = 'recommended') -> str:
        """Generate a shell script to perform backups."""
        priority_order = ['critical', 'recommended', 'optional']
        cutoff_index = priority_order.index(priority_level)
        included_priorities = priority_order[:cutoff_index + 1]

        script_lines = [
            "#!/bin/bash",
            "# Pre-upgrade backup script",
            "# Generated by Linux Upgrade Advisor",
            "",
            "set -e",
            "BACKUP_DIR=/root/upgrade-backups",
            "mkdir -p $BACKUP_DIR",
            "cd $BACKUP_DIR",
            "",
            "echo 'Starting pre-upgrade backups...'",
            "echo 'Backup location: '$BACKUP_DIR",
            "",
        ]

        for rec in recommendations:
            if rec.priority in included_priorities:
                script_lines.append(f"# {rec.priority.upper()}: {rec.target}")
                script_lines.append(f"echo 'Backing up {rec.target}...'")
                script_lines.append(rec.method)
                script_lines.append("")

        script_lines.extend([
            "echo 'Backup complete!'",
            "echo 'Backup size:'",
            "du -sh $BACKUP_DIR",
            "",
            "echo 'Backup files:'",
            "ls -lh $BACKUP_DIR",
        ])

        return '\n'.join(script_lines)
