# Rollback and Bail-Out Features

## ⚠️ **EXPERIMENTAL FEATURE WARNING** ⚠️

**Rollback features are UNTESTED and may FAIL when you need them most.**

- Snapshots may be corrupted
- Rollback may not restore your system
- May cause additional data loss
- May leave system unbootable

**NEVER rely on these rollback features as your only safety net.**

**ALWAYS maintain external backups** before attempting any upgrade.

See [README.md](README.md) and [WARNING.md](WARNING.md) for full warnings.

---

## Overview

The Linux Upgrade Advisor includes comprehensive rollback capabilities using **boom-boot** and **snapm** to provide a "bail-out" option if upgrades fail or cause issues.

**NOTE**: These rollback features are experimental and untested. Do not rely on them.

## Why Rollback Matters

OS upgrades can fail for many reasons:
- Incompatible hardware drivers
- Package conflicts
- Configuration issues
- Power failures during upgrade
- User error

**Having a rollback plan is critical** for production systems. This tool automatically creates rollback points before upgrades, giving you a safety net.

## Rollback Technologies

### 1. snapm (Recommended)

**What it is**: Advanced snapshot manager for LVM and Btrfs filesystems

**Advantages**:
- Atomic snapshots using Copy-on-Write (CoW)
- Minimal disk space initially
- Fast rollback (seconds to minutes)
- Manages both LVM and Btrfs
- Automatic cleanup of old snapshots

**How it works**:
```bash
# snapm automatically detects your filesystem type
snapm create --name pre-upgrade-20260529
snapm list
snapm rollback pre-upgrade-20260529
```

**Installation**:
```bash
# RHEL/Fedora
dnf install snapm
```

### 2. boom-boot

**What it is**: Boot entry manager for creating bootable snapshots

**Advantages**:
- Works with any filesystem
- Creates GRUB boot entries
- Allows booting previous kernel/initrd
- Lightweight (metadata only)
- Good for kernel-related issues

**How it works**:
```bash
# Creates a new boot entry with current state
boom create --title "Pre-upgrade backup"
boom list
# Reboot and select the boom entry from GRUB
```

**Installation**:
```bash
# RHEL/Fedora
dnf install boom-boot
```

## Using Rollback in Upgrade Advisor

### Automatic Rollback (Default)

The tool **automatically creates rollback points** before upgrades:

```bash
# Upgrade with automatic rollback point
./upgrade-advisor.py upgrade

# Output shows:
# ⚡ Creating pre-upgrade rollback point...
# ✓ Rollback point created: pre-upgrade-20260529-143022 (snapm)
```

### Manual Snapshot Creation

Create a snapshot anytime without performing an upgrade:

```bash
# Auto-detect best method
./upgrade-advisor.py create-snapshot

# Specify method
./upgrade-advisor.py create-snapshot --method snapm
./upgrade-advisor.py create-snapshot --method boom
```

### List Rollback Points

View all available rollback points:

```bash
./upgrade-advisor.py list-rollbacks
```

### Execute Rollback

Restore your system to a previous snapshot:

```bash
./upgrade-advisor.py rollback <ID>

# Example:
./upgrade-advisor.py rollback pre-upgrade-20260529-143022
```

**Important**: You'll be prompted for confirmation. The system may need to reboot to complete the rollback.

## AI Assistant Integration

The AI assistant understands your rollback capabilities:

**Example conversation:**

```
You: What happens if the upgrade fails?