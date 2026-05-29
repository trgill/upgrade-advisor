# Linux Upgrade Advisor

A CLI tool for Linux system administrators to analyze and execute OS upgrades for Fedora and RHEL systems.

## Features

- **System Detection**: Automatically detects current OS version and configuration
- **Upgrade Path Recommendations**: Suggests available upgrade paths
- **Compatibility Checks**: Identifies potential blockers and issues
- **Backup Recommendations**: Advises on pre-upgrade backup strategies
- **Automatic Tool Selection**: Uses Leapp for RHEL/CentOS, Ansible for Fedora

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Check current system and get upgrade recommendations
python upgrade-advisor.py check

# Perform compatibility checks
python upgrade-advisor.py preflight

# Execute upgrade (with confirmation)
python upgrade-advisor.py upgrade
```

## Supported Systems

- Fedora 38, 39, 40, 41
- RHEL 7, 8, 9
- CentOS 7, 8 (Stream)
