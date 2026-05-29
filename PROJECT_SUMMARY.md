# Linux Upgrade Advisor - Project Summary

## ⚠️ **EXPERIMENTAL SOFTWARE - NOT FOR PRODUCTION USE** ⚠️

This is untested prototype software that may cause complete data loss.
See [README.md](README.md) for full warnings before proceeding.

---

## Overview

A Python CLI tool that helps Linux system administrators safely upgrade Fedora and RHEL systems, featuring an **AI-powered assistant** that provides conversational guidance through the upgrade process.

## Key Features

### 1. **System Detection & Analysis**
- Auto-detects OS version, architecture, kernel
- Identifies package manager (DNF/YUM)
- Checks prerequisites (root access, internet, required tools)

### 2. **Upgrade Path Intelligence**
- **Fedora**: Upgrades via DNF system-upgrade plugin (automated with Ansible)
- **RHEL/CentOS**: In-place upgrades via Leapp utility
- Automatic tool selection based on detected OS
- Risk assessment (low/medium/high) for each path

### 3. **Compatibility Checking**
- Disk space validation
- Package update status
- SELinux configuration
- Third-party repository detection
- Custom kernel identification
- RHEL subscription verification
- Running services inventory

### 4. **Backup Recommendations**
- Priority-based backup suggestions (critical/recommended/optional)
- Automated backup script generation
- LVM snapshot guidance
- Database dump recommendations
- Configuration file archival

### 5. **Upgrade Execution**
- Dry-run mode for safety
- Leapp pre-upgrade assessment integration
- Ansible playbook generation for Fedora
- Confirmation prompts before destructive actions
- Detailed logging and error reporting

### 6. **🤖 AI Assistant (Claude Integration)**
The standout feature that sets this tool apart:

#### What It Does:
- **Contextual Awareness**: Automatically loads your system information, detected issues, and upgrade paths
- **Natural Language Interaction**: Ask questions like "What could go wrong?" instead of memorizing CLI flags
- **Step-by-Step Guidance**: Walks you through the entire process in order
- **Risk Explanation**: Translates technical jargon into clear, understandable advice
- **Troubleshooting Help**: Assists when things don't go as planned
- **Best Practices**: Shares real-world upgrade wisdom and safety tips

#### How It Works:
```python
# Loads system context once at startup
system_context = {
    'system': {os_info, architecture, kernel},
    'prerequisites': {has_root, has_leapp, has_ansible, has_internet},
    'upgrade_path': {from, to, method, risk_level, notes},
    'compatibility': {critical_issues, warnings, remediations},
    'backups': {critical_count, recommended_count}
}

# Uses Claude Sonnet 4 with this context
# Maintains conversation history for follow-up questions
# Employs prompt caching for efficient responses
```

#### Example Use Cases:
- "I'm nervous about this upgrade. What are the real risks?"
- "How long will downtime be?"
- "What should I backup first?"
- "My system has third-party repos. Is that a problem?"
- "Walk me through the entire process step-by-step"

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    upgrade-advisor.py                    │
│                    (Click CLI Interface)                 │
└────────┬──────────────────────────────────────┬─────────┘
         │                                       │
         ├─── System Detection ─────────────────┤
         │    (system_detector.py)               │
         │                                       │
         ├─── Upgrade Path Logic ───────────────┤
         │    (upgrade_paths.py)                 │
         │                                       │
         ├─── Compatibility Checks ─────────────┤
         │    (compatibility_checker.py)         │
         │                                       │
         ├─── Backup Recommendations ───────────┤
         │    (backup_advisor.py)                │
         │                                       │
         ├─── Upgrade Execution ────────────────┤
         │    (upgrade_executor.py)              │
         │    ├─> Leapp (RHEL/CentOS)            │
         │    └─> Ansible + DNF (Fedora)         │
         │                                       │
         └─── AI Assistant ─────────────────────┘
              (ai_assistant.py)
              └─> Claude Sonnet 4 API
                  (with prompt caching)
```

## Technology Stack

- **Language**: Python 3.8+
- **CLI Framework**: Click
- **UI**: Rich (terminal formatting)
- **AI**: Anthropic Claude API (Sonnet 4)
- **Automation**: Ansible Core
- **Upgrade Tools**: Leapp (RHEL), DNF system-upgrade (Fedora)
- **System Info**: distro, platform
- **Config**: python-dotenv

## Supported Systems

| Distribution | Versions | Upgrade Method |
|--------------|----------|----------------|
| Fedora | 38, 39, 40, 41 | DNF + Ansible |
| RHEL | 7→8, 8→9 | Leapp |
| CentOS | 7→8, 8→Stream | Leapp |
| Rocky Linux | 8, 9 | Leapp |
| AlmaLinux | 8, 9 | Leapp |

## Commands

```bash
upgrade-advisor.py check              # System analysis + upgrade recommendations
upgrade-advisor.py preflight          # Pre-upgrade compatibility checks
upgrade-advisor.py backup             # View backup recommendations
upgrade-advisor.py generate-backup-script  # Create backup script
upgrade-advisor.py upgrade            # Execute upgrade (with confirmation)
upgrade-advisor.py upgrade --dry-run  # Preview without executing
upgrade-advisor.py assistant          # 🤖 Start AI-guided session
upgrade-advisor.py assistant --export <file>  # Save conversation
```

## Design Decisions Made

### 1. **Advise AND Execute** (not just advise)
- Provides both analysis and action capabilities
- Dry-run mode for safety
- Clear warnings before destructive operations

### 2. **Automatic Tool Selection**
- Leapp for RHEL-based (Red Hat's official in-place upgrade tool)
- Ansible for Fedora (more flexible, handles DNF system-upgrade)
- Users don't need to understand the difference

### 3. **Target Audience: System Administrators**
- Technical but clear output
- Detailed logs and error messages
- Assumes basic Linux knowledge but explains complex concepts

### 4. **AI Integration via Anthropic Claude**
- Uses latest Claude Sonnet 4 for best reasoning
- Prompt caching reduces latency and cost
- Context-aware prompts with live system data
- Conversational over command-line for complex guidance

## Git History

```
ffdbc0f Add quick start guide for new users
b078e0d Add AI-powered assistant mode with Claude integration
9030061 Initial commit: Linux Upgrade Advisor prototype
```

## Files Structure

```
upgrade-advisor/
├── upgrade-advisor.py          # Main CLI (302 lines)
├── system_detector.py          # OS detection (95 lines)
├── upgrade_paths.py            # Upgrade logic (160 lines)
├── compatibility_checker.py    # Pre-flight checks (267 lines)
├── backup_advisor.py           # Backup guidance (151 lines)
├── upgrade_executor.py         # Leapp/Ansible execution (164 lines)
├── ai_assistant.py            # Claude AI integration (156 lines)
├── requirements.txt            # Dependencies
├── .env.example               # API key template
├── .gitignore                 # Git exclusions
├── README.md                  # Full documentation
├── QUICKSTART.md              # Getting started guide
├── DEMO.md                    # AI assistant examples
└── PROJECT_SUMMARY.md         # This file
```

## Next Steps / Future Enhancements

1. **Enhanced AI Capabilities**
   - Log file analysis and interpretation
   - Post-upgrade validation and anomaly detection
   - Predictive compatibility checking for installed packages

2. **Additional Features**
   - Rollback automation via LVM snapshots
   - Post-upgrade validation suite
   - Integration with monitoring tools (Prometheus, Grafana)
   - Email notifications for long-running upgrades

3. **Broader Support**
   - Ubuntu/Debian support (via do-release-upgrade)
   - openSUSE support (via zypper migration)
   - Container-based testing environments

4. **AI Assistant Enhancements**
   - Multi-language support
   - Voice mode for hands-free guidance
   - Integration with ticketing systems
   - Team collaboration features (shared upgrade sessions)

## Why This Approach Works

**Traditional upgrade tools** give you commands and checklists:
- "Run leapp preupgrade"
- "Check the report in /var/log/leapp/"
- "Fix inhibitors"
- "Run leapp upgrade"

**Problem**: Sysadmins still need to:
- Interpret cryptic error messages
- Understand what "inhibitors" mean for their specific setup
- Decide what to backup
- Know when it's safe to proceed

**This tool + AI assistant** provides:
- ✅ All the automation of traditional tools
- ✅ Plus conversational guidance through each step
- ✅ Risk explanation in plain language
- ✅ Personalized advice based on detected system state
- ✅ Answers to "what if" questions before you make mistakes

## Cost Considerations

**AI Assistant Usage**:
- Uses Claude Sonnet 4 (~$15 per million input tokens)
- System context: ~1-2K tokens (cached after first message)
- Typical upgrade session: 10-20 messages = ~$0.10-0.30
- Prompt caching reduces cost by ~90% for subsequent messages
- **Cost per upgrade session: < $0.50** (vs. hours of admin time)

## License

MIT License (see LICENSE file)

---

**Built with**: Python, Click, Rich, Anthropic Claude, Ansible, Leapp
**Version**: 0.1.0 (Prototype)
**Created**: May 2026
