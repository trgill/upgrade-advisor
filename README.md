# Linux Upgrade Advisor

A CLI tool for Linux system administrators to analyze and execute OS upgrades for Fedora and RHEL systems, with an AI-powered assistant to guide you through the process.

## Features

- **System Detection**: Automatically detects current OS version and configuration
- **Upgrade Path Recommendations**: Suggests available upgrade paths
- **Compatibility Checks**: Identifies potential blockers and issues
- **Backup Recommendations**: Advises on pre-upgrade backup strategies
- **Automatic Tool Selection**: Uses Leapp for RHEL/CentOS, Ansible for Fedora
- **⚡ Automatic Rollback**: Creates snapshots with boom-boot/snapm for safe bailout
- **🤖 AI Assistant**: Interactive AI guide powered by Claude that helps you through upgrades

## Installation

```bash
pip install -r requirements.txt

# Optional but HIGHLY RECOMMENDED for rollback capability
dnf install boom-boot snapm
```

### AI Assistant Setup (Optional)

To use the AI-powered assistant feature:

1. Get an API key from [Anthropic Console](https://console.anthropic.com/)
2. Copy `.env.example` to `.env`
3. Add your API key to `.env`:
   ```
   ANTHROPIC_API_KEY=your_key_here
   ```

## Usage

### Standard Commands

```bash
# Check current system and get upgrade recommendations
python upgrade-advisor.py check

# Perform compatibility checks
python upgrade-advisor.py preflight

# Get backup recommendations
python upgrade-advisor.py backup

# Generate backup script
python upgrade-advisor.py generate-backup-script

# Execute upgrade (with confirmation)
python upgrade-advisor.py upgrade --dry-run  # Preview first
python upgrade-advisor.py upgrade            # Actual upgrade (auto-creates rollback point)

# Rollback management
python upgrade-advisor.py create-snapshot    # Manual snapshot creation
python upgrade-advisor.py list-rollbacks     # Show available rollback points
python upgrade-advisor.py rollback <ID>      # Restore to snapshot
```

### AI Assistant Mode

Get personalized, conversational guidance through the upgrade process:

```bash
# Start interactive AI assistant
python upgrade-advisor.py assistant

# Save conversation for later reference
python upgrade-advisor.py assistant --export conversation.json
```

The AI assistant will:
- Analyze your specific system configuration
- Answer questions in natural language
- Guide you step-by-step through the upgrade
- Explain technical concepts clearly
- Help troubleshoot issues
- Recommend best practices for your situation

**Example interaction:**
```
You: I'm worried about upgrading my RHEL 8 server. What could go wrong?

Assistant: I understand your concern—RHEL 8 to 9 is a significant upgrade. Let me walk you through the main risks...
```

## Supported Systems

- Fedora 38, 39, 40, 41
- RHEL 7, 8, 9
- CentOS 7, 8 (Stream)
- Rocky Linux, AlmaLinux

## How It Works

### Upgrade Methods

**For RHEL/CentOS (Leapp)**:
- In-place upgrade utility maintained by Red Hat
- Performs pre-upgrade analysis
- Automatic rollback point creation
- Handles RHEL 7→8 and 8→9 transitions

**For Fedora (Ansible + DNF)**:
- Uses DNF system-upgrade plugin
- Automated via Ansible playbooks
- Automatic rollback point creation
- Downloads new version packages
- Upgrades on reboot

**Rollback & Safety (boom-boot / snapm)**:
- **boom-boot**: Creates bootable rollback points in GRUB
- **snapm**: Atomic filesystem snapshots for instant rollback
- **Automatic**: Snapshot created before every upgrade
- **One-command rollback**: `./upgrade-advisor.py rollback <ID>`
- Works with LVM and Btrfs filesystems

### AI Assistant Architecture

The AI assistant uses Claude (Anthropic's AI) with:
- **System Context**: Auto-detects your OS, installed packages, and configuration
- **Compatibility Analysis**: Understands your specific blockers and risks
- **Conversational Guidance**: Explains steps in plain language
- **Prompt Caching**: Efficient context management for responsive interactions

## Project Structure

```
upgrade-advisor/
├── upgrade-advisor.py          # Main CLI entry point
├── system_detector.py          # OS and hardware detection
├── upgrade_paths.py            # Upgrade path logic
├── compatibility_checker.py    # Pre-flight checks
├── backup_advisor.py           # Backup recommendations
├── upgrade_executor.py         # Leapp/Ansible execution  
├── rollback_manager.py         # Boom/snapm rollback integration
├── ai_assistant.py            # AI-powered guide (Claude integration)
├── requirements.txt            # Python dependencies
├── .env.example               # Configuration template
└── ROLLBACK.md                # Rollback documentation
```

## Development

```bash
# Clone and setup
git clone <repo-url>
cd upgrade-advisor
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests (when available)
pytest

# Check your system
./upgrade-advisor.py check
```

## Safety Features

- ✅ **Automatic Rollback Points**: boom-boot/snapm snapshots before upgrades
- ✅ **One-Command Bailout**: Instant rollback if upgrade fails
- ✅ Dry-run mode for all operations
- ✅ Pre-upgrade compatibility checks
- ✅ Backup script generation
- ✅ Confirmation prompts for destructive actions
- ✅ Detailed logging and error messages
- ✅ AI assistant explains risks and rollback options

## Limitations

- Requires root/sudo for actual upgrades
- Third-party repos may cause conflicts
- Custom kernels not supported
- Limited to Fedora and RHEL-based distros

## Contributing

Contributions welcome! Areas for improvement:
- Additional distro support (Debian, Ubuntu)
- Enhanced AI reasoning for edge cases
- Post-upgrade validation
- Rollback automation
- Integration with monitoring tools

## License

MIT License - see LICENSE file for details
