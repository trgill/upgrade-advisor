# ⚠️ EXPERIMENTAL SOFTWARE - CRITICAL WARNINGS ⚠️

## DO NOT USE THIS SOFTWARE WITHOUT READING THIS FILE

This document contains critical safety information. **Failure to follow these warnings may result in complete data loss.**

---

## What This Software Is

**Linux Upgrade Advisor** is an **EXPERIMENTAL, UNTESTED PROTOTYPE**. It was created as a demonstration/proof-of-concept and has **NOT** been validated for production use.

## What Can Go Wrong

Using this software may result in:

### ❌ Complete Data Loss
- All files, databases, configurations may be permanently destroyed
- No recovery possible without external backups

### ❌ System Corruption
- Operating system may become corrupted
- File systems may be damaged
- Configuration files may be destroyed

### ❌ Unbootable System
- System may fail to boot after upgrade
- May require complete reinstallation
- Recovery media may not help

### ❌ Failed Upgrades
- Upgrade process may fail midway
- System may be left in inconsistent state
- Rollback features may also fail

### ❌ Business Impact
- Extended downtime (hours to days)
- Loss of critical business data
- Service interruption
- Financial losses

## Rollback Features Are Also Experimental

**DO NOT TRUST THE ROLLBACK FEATURES**

The boom-boot and snapm integration is:
- ❌ Untested
- ❌ May fail when needed
- ❌ May corrupt snapshots
- ❌ May make things worse
- ❌ NOT a reliable safety net

**External backups are mandatory.**

## What You MUST Do Before Using This Tool

### ✅ 1. BACKUP EVERYTHING TO EXTERNAL STORAGE

- Copy ALL data to external drives or remote servers
- Include:
  - User files (/home)
  - Databases
  - Configuration files (/etc)
  - Application data (/var, /opt)
  - Any custom modifications

### ✅ 2. VERIFY BACKUPS ARE RESTORABLE

- Test restore process on another machine
- Verify data integrity
- Ensure you know how to restore

### ✅ 3. HAVE RECOVERY PLAN READY

- Installation media for your OS
- Documentation for reinstallation
- Contact information for support
- Downtime window scheduled

### ✅ 4. TEST ON NON-PRODUCTION FIRST

- **NEVER** test on production systems first
- Use identical hardware if possible
- Test complete upgrade and rollback cycle
- Document any issues

### ✅ 5. HAVE EXTERNAL SUPPORT AVAILABLE

- System administrator on standby
- Vendor support contact information
- Escalation plan if recovery fails

## What You Must NOT Do

### ⛔ DO NOT use on production systems without extensive testing
### ⛔ DO NOT rely on rollback features as your only backup
### ⛔ DO NOT assume it will work correctly
### ⛔ DO NOT use on systems with data you cannot afford to lose
### ⛔ DO NOT use without verified external backups
### ⛔ DO NOT skip the warning prompts
### ⛔ DO NOT ignore error messages

## For Production Systems

**Use official vendor-supported tools:**

- **Red Hat Enterprise Linux**: Use official Leapp tool with Red Hat support
- **Fedora**: Use official dnf system-upgrade with Fedora documentation
- **CentOS/Rocky/Alma**: Use official upgrade paths and documentation

Follow proper change management procedures:
1. Change request approval
2. Maintenance window scheduling
3. Stakeholder notification
4. Tested rollback plan
5. Vendor support on standby

## Legal Disclaimer

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

THE AUTHORS AND CONTRIBUTORS:
- Provide **NO WARRANTY** of any kind
- Accept **NO LIABILITY** for any damage or data loss
- Make **NO GUARANTEES** about functionality
- Provide **NO SUPPORT** obligations

**YOU USE THIS SOFTWARE ENTIRELY AT YOUR OWN RISK.**

By using this software, you acknowledge that you have read, understood, and
accepted these terms.

## Questions to Ask Yourself Before Proceeding

1. ❓ Do I have verified, restorable external backups?
2. ❓ Can I afford complete data loss on this system?
3. ❓ Have I tested this on non-production systems first?
4. ❓ Do I have a recovery plan if everything fails?
5. ❓ Am I prepared for extended downtime?
6. ❓ Do I have vendor support available if needed?
7. ❓ Is there a business-critical reason I can't use official tools?

**If you answered "NO" to ANY question, DO NOT PROCEED.**

## Recommended Alternative

For production use, follow vendor-recommended procedures:

- RHEL: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/
- Fedora: https://docs.fedoraproject.org/en-US/quick-docs/upgrading/

## Still Want to Proceed?

If you have:
- ✅ Read and understood all warnings
- ✅ Made verified external backups
- ✅ Tested on non-production systems
- ✅ Accepted full responsibility for consequences
- ✅ Have recovery plan ready

Then you may proceed with extreme caution.

Remember: **The software will likely break. Be prepared.**

---

**Last Updated**: 2026-05-29
**Software Version**: 0.1.0-EXPERIMENTAL
