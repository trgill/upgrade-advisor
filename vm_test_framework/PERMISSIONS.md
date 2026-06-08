# VM Test Framework - Permissions Guide

## TL;DR - You Don't Need Root

✅ **Tests run as your regular user** (after one-time setup)  
✅ **Setup script handles everything automatically**  
✅ **Just run: `./run-vm-tests.sh setup`**

## How It Works

The VM test framework uses **libvirt group membership** instead of root access.

### One-Time Setup

```bash
# Automated setup (recommended)
./run-vm-tests.sh setup

# The script will:
# 1. Add you to libvirt group
# 2. Create directories with correct ownership
# 3. Enable libvirtd service
# 4. Set up default network
```

After setup, **log out and back in** (or run `newgrp libvirt`) for group changes to take effect.

### What Gets Configured

1. **User Group**: Added to `libvirt` group
   ```bash
   # What the script does:
   sudo usermod -a -G libvirt $USER
   ```

2. **Storage Directories**: Owned by your user
   ```bash
   # Permissions set to:
   drwxrwxr-x. user libvirt /var/lib/libvirt/images/upgrade-test/
   ```

3. **Libvirt Service**: Enabled and running
   ```bash
   # Ensures daemon is available:
   sudo systemctl enable --now libvirtd
   ```

## Verify Your Setup

```bash
# Check everything is configured correctly
./run-vm-tests.sh check
```

Expected output:
```
Checking VM test framework prerequisites...

Checking libvirt group membership... ✓
Checking libvirtd service... ✓
Checking libvirt connection... ✓
Checking storage directories... ✓
Checking Python dependencies... ✓
Checking configuration... ✓

✓ All checks passed! Ready to run tests.
```

## Manual Setup (if needed)

If you prefer to set up manually:

```bash
# 1. Add yourself to libvirt group
sudo usermod -a -G libvirt $USER

# 2. Log out and back in (or use newgrp)
newgrp libvirt

# 3. Create storage directories
sudo mkdir -p /var/lib/libvirt/images/upgrade-test/{templates,instances}
sudo chown -R $USER:libvirt /var/lib/libvirt/images/upgrade-test
sudo chmod -R 775 /var/lib/libvirt/images/upgrade-test

# 4. Start libvirt
sudo systemctl enable --now libvirtd

# 5. Verify
virsh -c qemu:///system list  # Should work without sudo
```

## Running Tests (No Sudo Required)

Once set up, all test operations run as your user:

```bash
# All of these run without sudo:
./run-vm-tests.sh create-template rhel 9.3 /path/to/iso
./run-vm-tests.sh smoke
./run-vm-tests.sh parallel
python vm_test_framework/test_runner.py --config test_configs/rhel9-to-10.yaml
virsh list --all
```

## What About Root Inside VMs?

The **upgrade inside the VM runs as root**, but that's controlled by:
- The VM's kickstart configuration (sets root password)
- SSH access to the VM (as root)

Your **host user never needs to be root** to orchestrate the tests.

## Common Issues

### "Permission denied" errors

**Problem**: Can't access libvirt daemon

**Solution**:
```bash
# Verify you're in the group
groups | grep libvirt

# If not present, re-run setup
./run-vm-tests.sh setup

# Then log out and back in
```

### "Cannot access libvirt" after adding to group

**Problem**: Group membership not active in current session

**Solution**:
```bash
# Quick fix (without logout):
newgrp libvirt

# Or log out and back in for permanent effect
```

### Storage directory permission errors

**Problem**: Can't write to `/var/lib/libvirt/images/upgrade-test/`

**Solution**:
```bash
# Fix ownership
sudo chown -R $USER:libvirt /var/lib/libvirt/images/upgrade-test
sudo chmod -R 775 /var/lib/libvirt/images/upgrade-test

# Verify
ls -la /var/lib/libvirt/images/ | grep upgrade-test
# Should show: drwxrwxr-x. user libvirt ...
```

### "virsh: command not found"

**Problem**: Virtualization packages not installed

**Solution**:
```bash
# On RHEL/Fedora:
sudo dnf install -y qemu-kvm libvirt virt-install

# Start service:
sudo systemctl enable --now libvirtd
```

### libvirtd not running

**Problem**: Service stopped or not enabled

**Solution**:
```bash
# Start and enable:
sudo systemctl enable --now libvirtd

# Verify:
systemctl status libvirtd
```

## Why This Approach?

### Security Benefits
- **Least Privilege**: Don't need full root access
- **Audit Trail**: User actions tracked separately from root
- **Safer**: Mistakes won't affect system-wide files

### Convenience Benefits
- **No sudo prompts**: Commands run smoothly in scripts
- **CI/CD Friendly**: Easy to automate without privilege escalation
- **Team Collaboration**: Each user has their own isolated storage

### Standard Practice
- **Libvirt Design**: This is how libvirt is meant to be used
- **Follows Best Practices**: Same approach as Docker, KVM, etc.
- **Upstream Standard**: Matches Red Hat/Fedora documentation

## Advanced: PolicyKit Rules

If you want even finer-grained control, you can use PolicyKit rules instead of group membership.

Create `/etc/polkit-1/rules.d/80-libvirt.rules`:
```javascript
polkit.addRule(function(action, subject) {
    if (action.id == "org.libvirt.unix.manage" &&
        subject.user == "yourusername") {
        return polkit.Result.YES;
    }
});
```

This gives your specific user libvirt access without group membership.

## Security Considerations

### What You Can Do
- Create/destroy VMs in your storage pool
- Manage networks (user-mode or existing networks)
- Take snapshots and clone VMs
- Access VM consoles

### What You Cannot Do
- Modify system-wide libvirt settings (without sudo)
- Access other users' VMs (unless explicitly shared)
- Change libvirt daemon configuration
- Install system packages (inside host)

### Inside Test VMs
- VMs are **isolated** from your host
- VMs run on **NAT network** by default (isolated from external network)
- Template VMs have **hardcoded test passwords** (testpassword)
- For production use, change passwords and use SSH keys

## Quick Reference

| Task | Requires Sudo? | When |
|------|----------------|------|
| Initial setup | Yes | One-time only |
| Add user to group | Yes | One-time only |
| Create templates | No | After setup |
| Run tests | No | After setup |
| View results | No | Always |
| Manage VMs | No | After setup |
| Install packages (host) | Yes | When needed |
| Upgrade inside VM | No* | During tests |

*Upgrade runs as root inside the VM, but your host user doesn't need sudo to orchestrate it.

## Getting Help

If you're stuck with permissions:

1. **Run the diagnostic**: `./run-vm-tests.sh check`
2. **Check the output**: It will tell you exactly what's wrong
3. **Follow the suggestions**: Each check provides fix commands
4. **Re-run setup if needed**: `./run-vm-tests.sh setup`

Still having issues? Check:
- You logged out and back in after being added to libvirt group
- libvirtd service is running: `systemctl status libvirtd`
- You can run virsh: `virsh -c qemu:///system list`
- Directory permissions: `ls -la /var/lib/libvirt/images/`

## Summary

✅ One-time setup with sudo (automated)  
✅ All tests run as regular user  
✅ Secure, convenient, and standard practice  
✅ Built-in diagnostics help troubleshoot  
✅ No root access needed for day-to-day testing
