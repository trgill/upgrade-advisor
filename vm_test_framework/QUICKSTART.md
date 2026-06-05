# VM Test Framework - Quick Start Guide

Get started testing RHEL upgrades in VMs in under 30 minutes.

## Prerequisites

1. **System Requirements**
   - RHEL 9 or Fedora host system
   - qemu-kvm and libvirt installed
   - At least 100 GB free disk space
   - 16 GB RAM (for parallel testing)
   - CPU with virtualization support (Intel VT-x or AMD-V)

2. **Install Required Packages**
   ```bash
   # On RHEL/CentOS
   sudo dnf install -y qemu-kvm libvirt virt-install virt-manager \
       python3 python3-pip python3-libvirt python3-yaml

   # Start libvirt
   sudo systemctl enable --now libvirtd

   # Add your user to libvirt group
   sudo usermod -a -G libvirt $USER
   newgrp libvirt
   ```

3. **Python Dependencies**
   ```bash
   cd /home/tgill/workspace/upgrade-advisor
   pip install -r vm_test_framework/requirements.txt
   ```

## Step 1: Configuration

1. Copy the example config:
   ```bash
   cd vm_test_framework
   cp config.example.yaml config.yaml
   ```

2. Edit `config.yaml`:
   ```yaml
   # Set your storage pool location
   storage_pool: /var/lib/libvirt/images/upgrade-test
   
   # Configure RHEL subscription (for Red Hat employees)
   rhel_subscription:
     method: activation_key
     activation_key: "your-key-here"
     org_id: "your-org-id"
   ```

3. Create storage directories:
   ```bash
   sudo mkdir -p /var/lib/libvirt/images/upgrade-test/{templates,instances}
   sudo mkdir -p /var/lib/libvirt/images/isos
   sudo chown -R $USER:libvirt /var/lib/libvirt/images/upgrade-test
   ```

## Step 2: Get RHEL ISO

As a Red Hat employee, download RHEL ISOs from the Customer Portal:

1. Go to https://access.redhat.com/downloads
2. Download **RHEL 9.3 Binary DVD** (or latest 9.x)
3. Save to `/var/lib/libvirt/images/isos/`

```bash
# Example (replace with your actual download)
mv ~/Downloads/rhel-9.3-x86_64-dvd.iso /var/lib/libvirt/images/isos/
```

**Alternative for testing:** Use Red Hat Developer Subscription (free):
- https://developers.redhat.com/products/rhel/download

## Step 3: Create VM Template

Create a base RHEL 9 template (this takes 10-20 minutes):

```bash
cd /home/tgill/workspace/upgrade-advisor

python vm_test_framework/vm_manager.py create-template \
  --os rhel \
  --version 9.3 \
  --profile minimal \
  --iso /var/lib/libvirt/images/isos/rhel-9.3-x86_64-dvd.iso
```

This will:
- Create a VM with kickstart automation
- Install RHEL 9.3 unattended
- Save as template for fast cloning
- Template saved in `/var/lib/libvirt/images/upgrade-test/templates/`

**Verify template creation:**
```bash
python vm_test_framework/vm_manager.py list-templates
```

You should see: `rhel-9.3-minimal`

## Step 4: Run Your First Test

Run a smoke test to verify everything works:

```bash
# Dry run (see what would happen)
python vm_test_framework/test_runner.py \
  --config test_configs/rhel9-to-10.yaml \
  --filter-tags smoke \
  --dry-run

# Actual test run
python vm_test_framework/test_runner.py \
  --config test_configs/rhel9-to-10.yaml \
  --filter-tags smoke
```

This will:
1. Clone the template
2. Start a test VM
3. Run RHEL 9 → 10 upgrade
4. Validate the upgrade
5. Collect logs
6. Generate report

**Expected duration:** 15-30 minutes for smoke test

## Step 5: View Results

```bash
# Results are in:
ls vm_test_framework/results/

# View latest summary:
cat vm_test_framework/results/$(ls -t vm_test_framework/results | head -1)/summary.json | jq
```

## Step 6: Run Full Test Suite

Once the smoke test passes, run the full suite:

```bash
# Run all tests sequentially
python vm_test_framework/test_runner.py \
  --config test_configs/rhel9-to-10.yaml

# Run 3 tests in parallel (faster!)
python vm_test_framework/test_runner.py \
  --config test_configs/rhel9-to-10.yaml \
  --parallel 3
```

**Full suite duration:** 2-4 hours (sequential), 1-2 hours (parallel)

## Common Operations

### List all VMs
```bash
python vm_test_framework/vm_manager.py list
```

### Clone a template manually
```bash
python vm_test_framework/vm_manager.py clone \
  --template rhel-9.3-minimal \
  --name my-test-vm
```

### Destroy a VM
```bash
python vm_test_framework/vm_manager.py destroy --vm my-test-vm
```

### Create custom test matrix
```bash
# Generate example config
python vm_test_framework/test_matrix.py example > my-tests.yaml

# Edit my-tests.yaml, then run:
python vm_test_framework/test_runner.py --config my-tests.yaml
```

## Troubleshooting

### Template creation fails
```bash
# Check libvirt is running
sudo systemctl status libvirtd

# Check permissions
ls -la /var/lib/libvirt/images/upgrade-test/

# Check ISO is accessible
ls -la /var/lib/libvirt/images/isos/
```

### VM won't start
```bash
# Check libvirt network
virsh net-list --all
virsh net-start default

# Check VM logs
virsh domstate <vm-name>
tail -f /var/log/libvirt/qemu/<vm-name>.log
```

### Upgrade times out
```bash
# Increase timeout in test config
# Edit test_configs/rhel9-to-10.yaml
timeout_minutes: 120  # Increase from 60
```

### Can't SSH to VM
```bash
# Check VM IP
virsh domifaddr <vm-name>

# Check SSH service
virsh console <vm-name>
# (login, then check sshd)
systemctl status sshd
```

## Next Steps

1. **Create more templates:**
   ```bash
   # RHEL 8 template
   python vm_manager.py create-template \
     --os rhel --version 8.9 --profile minimal \
     --iso /var/lib/libvirt/images/isos/rhel-8.9-x86_64-dvd.iso
   
   # Server profile
   python vm_manager.py create-template \
     --os rhel --version 9.3 --profile server \
     --iso /var/lib/libvirt/images/isos/rhel-9.3-x86_64-dvd.iso
   ```

2. **Customize test scenarios:**
   - Edit `test_configs/rhel9-to-10.yaml`
   - Add your own package sets
   - Add custom validation checks

3. **Integrate with upgrade-advisor:**
   - Tests use your upgrade_executor.py
   - Validate rollback functionality
   - Test AI assistant recommendations

4. **Set up CI/CD:**
   - Run tests on every commit
   - Automated nightly test runs
   - Email reports on failures

## Resource Usage

**Per test:**
- Disk: ~2-3 GB (copy-on-write)
- RAM: 2 GB (configurable)
- CPU: 2 cores (configurable)

**Full parallel run (3 jobs):**
- Disk: ~10 GB
- RAM: 6 GB
- CPU: 6 cores

**Storage growth:**
- Templates: ~5 GB per OS version
- Results archive: ~500 MB per test run

## Tips

1. **Speed up testing:**
   - Use `--parallel 3` for 3x faster runs
   - Run smoke tests (`--filter-tags smoke`) first
   - Cache ISOs locally

2. **Save disk space:**
   - Templates use qcow2 (compressed)
   - Test VMs use copy-on-write (minimal space)
   - Auto-cleanup old results (config.yaml)

3. **Debug failed tests:**
   - Add `keep_failed: true` to config.yaml
   - Failed VMs won't be destroyed
   - Login with `virsh console <vm-name>`

4. **Customize templates:**
   - Edit kickstart files in `kickstart_templates/`
   - Add pre-installed packages
   - Configure networking

## Getting Help

- Check [README.md](README.md) for architecture details
- Review test configs in `test_configs/`
- Check logs in `vm_test_framework/results/`
- Ask in #upgrade-advisor (internal Slack)

## Example Workflow

```bash
# 1. One-time setup (30 min)
cp config.example.yaml config.yaml
vim config.yaml  # Add your RHEL subscription
python vm_manager.py create-template --os rhel --version 9.3 --profile minimal \
  --iso /var/lib/libvirt/images/isos/rhel-9.3-x86_64-dvd.iso

# 2. Quick smoke test (15 min)
python test_runner.py --config test_configs/rhel9-to-10.yaml \
  --filter-tags smoke

# 3. Full test suite (1-2 hours)
python test_runner.py --config test_configs/rhel9-to-10.yaml \
  --parallel 3

# 4. View results
cat results/$(ls -t results | head -1)/summary.json | jq
```

Congratulations! You're now running automated upgrade tests! 🎉
