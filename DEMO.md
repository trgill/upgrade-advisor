# AI Assistant Demo

## Quick Start

```bash
# 1. Set up your API key
cp .env.example .env
# Edit .env and add your Anthropic API key

# 2. Start the AI assistant
python upgrade-advisor.py assistant
```

## Example Conversation Flow

### Scenario: Nervous administrator upgrading RHEL 8 → 9

**You:** I need to upgrade from RHEL 8 to RHEL 9, but I've never done this before. Can you help me understand the process?

**Assistant:** Absolutely! I can see you're running RHEL 8, and upgrading to RHEL 9 is definitely doable. Think of it like renovating a house while you're still living in it—Leapp (the upgrade tool) does the heavy lifting while keeping your data and configurations intact.

Here's what will happen:
1. **Pre-upgrade check** - Leapp scans your system for potential issues
2. **Download phase** - New RHEL 9 packages are downloaded
3. **Upgrade phase** - System reboots into a special environment and upgrades
4. **Verification** - You check that everything works

The good news: I've detected your system is eligible for this upgrade. The main risk level is medium—this is a major version jump with changes to Python, package versions, and system libraries.

Would you like me to walk you through the pre-flight checks first?

---

**You:** Yes, let's do the checks. What should I be worried about?

**Assistant:** Great thinking—let's identify any potential blockers before we start. Based on my analysis of your system, here's what I found:

**Critical Issues:** None! 🎉

**Warnings (2):**
1. You have pending package updates - we should apply those first
2. I detected third-party repositories - these might need to be disabled during upgrade

Neither of these are showstoppers, just preparation steps. The most important thing before any major upgrade is backing up your data. 

I see you have critical paths like `/home`, `/etc`, and potentially databases. Have you thought about your backup strategy yet?

---

**You:** I haven't backed up anything yet. What do I need to do?

**Assistant:** Don't worry—let's make sure you're protected. Think of backups as your "undo button" if anything unexpected happens.

For RHEL 8→9, I recommend:
1. **Critical backups** (must-have):
   - `/etc` - all your configuration files
   - `/home` - user data
   - Package list - so we can rebuild if needed
   
2. **Recommended** (strongly advised):
   - Database dumps (if you're running MySQL/PostgreSQL)
   - `/var/log` - helps troubleshooting
   - LVM snapshot - gives you a quick rollback option

The tool can generate a backup script for you. Would you like me to explain how to create an LVM snapshot? It's like taking a "checkpoint" of your entire system that you can roll back to if needed.

---

**You:** How long will the upgrade take?

**Assistant:** Good question—you'll want to plan a maintenance window. For RHEL 8→9 with Leapp:

- **Download phase:** 20-45 minutes (downloading ~2-4 GB of packages)
- **Upgrade phase:** 30-60 minutes (system reboots, applies changes)
- **Verification:** 15-30 minutes (checking services, testing)

**Total: 1-2 hours of downtime**

The system will be unavailable during the upgrade reboot phase. If you're running production services, you'll want to:
1. Schedule this during a maintenance window
2. Notify users of the downtime
3. Have a rollback plan ready (that LVM snapshot!)

One more thing: after the upgrade completes, some services might need manual restart. I'll help you verify everything afterward.

Ready to proceed, or do you have more questions first?

---

### Commands During Session

- Type `context` to see your system information
- Type `reset` to start a fresh conversation
- Type `exit` to quit

## What Makes the AI Assistant Valuable

1. **Contextual Understanding**: Knows your specific OS version, detected issues, and upgrade path
2. **Plain Language**: Explains technical concepts without jargon
3. **Proactive Safety**: Emphasizes backups and risk mitigation
4. **Guided Process**: Walks you through each step in order
5. **Question Answering**: Handles "what if" scenarios and concerns
6. **Experience Sharing**: Provides best practices from real-world upgrades

## Technical Features

- Powered by Claude Sonnet 4 (latest Anthropic model)
- Includes prompt caching for efficient responses
- Auto-loads system context from compatibility checks
- Maintains conversation history across questions
- Can export full conversation for documentation
