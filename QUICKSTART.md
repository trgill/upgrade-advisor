# Quick Start Guide

## Installation

```bash
# 1. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# venv\Scripts\activate    # On Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify installation
./upgrade-advisor.py --help
```

## Basic Usage (No AI)

```bash
# Check your system and see upgrade options
./upgrade-advisor.py check

# Run pre-flight compatibility checks
./upgrade-advisor.py preflight

# Get backup recommendations
./upgrade-advisor.py backup

# Generate a backup script
./upgrade-advisor.py generate-backup-script --priority critical

# Preview upgrade (dry run - safe to test)
./upgrade-advisor.py upgrade --dry-run
```

## AI Assistant Setup

```bash
# 1. Get API key from https://console.anthropic.com/
# 2. Create .env file
cp .env.example .env

# 3. Edit .env and add your key:
#    ANTHROPIC_API_KEY=sk-ant-xxxxx

# 4. Start interactive assistant
./upgrade-advisor.py assistant

# 5. Save conversation for reference
./upgrade-advisor.py assistant --export my-upgrade-plan.json
```

## Example Workflows

### Workflow 1: First-time RHEL upgrade

```bash
# Step 1: Check current system
./upgrade-advisor.py check

# Step 2: Run compatibility checks
./upgrade-advisor.py preflight

# Step 3: Get AI guidance
./upgrade-advisor.py assistant
# Ask: "What are the risks of upgrading RHEL 8 to 9?"
# Ask: "Walk me through the backup process"
# Ask: "What should I test after the upgrade?"

# Step 4: Create backups
./upgrade-advisor.py generate-backup-script
sudo bash /tmp/pre-upgrade-backup.sh

# Step 5: Preview upgrade
./upgrade-advisor.py upgrade --dry-run

# Step 6: Execute (when ready)
sudo ./upgrade-advisor.py upgrade
```

### Workflow 2: Fedora version upgrade

```bash
# Check upgrade path
./upgrade-advisor.py check

# Use AI to understand process
./upgrade-advisor.py assistant
# Ask: "I'm upgrading Fedora 40 to 41. What's different from RHEL upgrades?"

# Run preflight
./upgrade-advisor.py preflight

# Backup and upgrade
./upgrade-advisor.py backup
sudo ./upgrade-advisor.py upgrade
```

## Testing Without Root

Most commands work without root privileges:
- ✅ `check` - System detection
- ✅ `preflight` - Compatibility checks (limited without root)
- ✅ `backup` - View recommendations
- ✅ `assistant` - AI guidance
- ❌ `upgrade` - Requires root/sudo
- ❌ `generate-backup-script` execution - Requires root/sudo

## Troubleshooting

### "ModuleNotFoundError: No module named 'rich'"
```bash
pip install -r requirements.txt
```

### "ANTHROPIC_API_KEY not found"
```bash
# Create .env file with your API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

### "Permission denied" errors
```bash
# Most diagnostic commands work without root
# Only actual upgrades need sudo
sudo ./upgrade-advisor.py upgrade
```

## What to Expect

### Without AI Assistant
The tool provides:
- Structured analysis of your system
- Clear upgrade path recommendations
- Checklist-style compatibility reports
- Backup script generation
- Automated upgrade execution

### With AI Assistant
Additionally provides:
- Natural language Q&A about upgrades
- Personalized guidance based on your system
- Explanations of technical concepts
- Risk assessment and mitigation advice
- Step-by-step walkthrough
- Troubleshooting help

## Next Steps

1. **Read the docs**: Check [README.md](README.md) for full feature list
2. **Try the demo**: See [DEMO.md](DEMO.md) for example conversations
3. **Run a check**: Start with `./upgrade-advisor.py check`
4. **Ask the AI**: Use `./upgrade-advisor.py assistant` for guidance
