# VM-Based Upgrade Test Framework

Automated testing framework for validating OS upgrades across different configurations using QEMU/KVM virtual machines.

## Architecture Overview

```
vm_test_framework/
├── vm_manager.py           # VM lifecycle management (create, clone, snapshot, destroy)
├── test_matrix.py          # Test configuration and matrix generation
├── test_runner.py          # Orchestrates test execution
├── validators.py           # Post-upgrade validation checks
├── reporting.py            # Test results and reports
├── kickstart_templates/    # Automated installation configs
│   ├── rhel8-minimal.ks
│   ├── rhel9-minimal.ks
│   ├── rhel9-server.ks
│   └── fedora-workstation.ks
├── test_configs/           # Test scenario definitions
│   ├── rhel8-to-9.yaml
│   ├── rhel9-to-10.yaml
│   └── fedora-upgrade.yaml
└── results/                # Test output and logs
    └── <timestamp>/
        ├── summary.json
        ├── detailed_report.html
        └── vm_logs/
```

## Features

### 1. VM Template Management
- Base image creation with kickstart automation
- Clone-on-write snapshots for fast test startup
- Template versioning and caching
- Automatic ISO download (with RHEL subscription support)

### 2. Test Matrix Support
- Multiple source OS versions (RHEL 8.x, 9.x, Fedora 40-44)
- Different installation profiles (minimal, server, workstation)
- Package set variations (web server, database, development)
- Storage configurations (standard partitions, LVM, custom layouts)
- Third-party repo testing

### 3. Automated Testing
- Parallel test execution
- Pre-upgrade system snapshots
- Upgrade execution with timeout handling
- Post-upgrade validation
- Automatic log collection
- Rollback testing

### 4. Validation Framework
- System boots successfully
- All expected services running
- Package integrity verification
- Configuration file preservation
- Network connectivity
- Custom application testing
- Performance benchmarks

### 5. Integration with upgrade-advisor
- Uses your existing upgrade_executor.py
- Tests your tool's recommendations
- Validates rollback functionality
- AI assistant testing scenarios

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure (point to your RHEL ISOs, set storage pool)
cp config.example.yaml config.yaml
vim config.yaml

# Create base templates (one-time setup)
python vm_test_framework/vm_manager.py create-templates

# Run a single test
python vm_test_framework/test_runner.py --config test_configs/rhel9-to-10.yaml

# Run full test matrix
python vm_test_framework/test_runner.py --matrix rhel-upgrade-matrix

# View results
python vm_test_framework/reporting.py --show-latest
```

## Test Configuration Example

```yaml
# test_configs/rhel9-to-10.yaml
name: "RHEL 9 to RHEL 10 Upgrade Suite"
source_version: "rhel-9.3"
target_version: "rhel-10.0"

variants:
  - name: "minimal-install"
    profile: minimal
    packages: []
    
  - name: "web-server"
    profile: server
    packages:
      - httpd
      - mod_ssl
      - php
    services:
      - httpd
    validation:
      - check_service: httpd
      - check_http_response: "http://localhost"
      
  - name: "database-server"
    profile: server
    packages:
      - postgresql-server
      - postgresql-contrib
    pre_upgrade_setup:
      - "postgresql-setup --initdb"
      - "systemctl enable postgresql"
    validation:
      - check_service: postgresql
      - check_database_integrity: true

storage_layouts:
  - standard_partitions
  - lvm_default
  - lvm_with_separate_home

parallel_jobs: 3
timeout_minutes: 60
```

## How It Works

### Phase 1: Template Preparation
1. Download RHEL/Fedora ISOs (via subscription or Red Hat employee access)
2. Create base VMs using kickstart for unattended installation
3. Snapshot base VMs as templates
4. Cache templates for reuse

### Phase 2: Test Execution
1. Clone template VM for test instance
2. Boot VM and apply test-specific configuration
3. Take pre-upgrade snapshot
4. Execute upgrade using upgrade-advisor
5. Monitor upgrade process (with timeout)
6. Reboot and verify boot success

### Phase 3: Validation
1. System health checks (boot, login, services)
2. Package verification
3. Configuration preservation checks
4. Application-specific tests
5. Performance benchmarks (optional)

### Phase 4: Reporting
1. Collect all logs (leapp, dnf, system logs)
2. Generate pass/fail status
3. Create detailed HTML report
4. Update test matrix dashboard
5. Archive results

## VM Management Commands

```bash
# Create a new base template
python vm_manager.py create-template --os rhel9 --iso /path/to/rhel.iso

# List all templates
python vm_manager.py list-templates

# Clone a template for testing
python vm_manager.py clone --template rhel9-minimal --name test-vm-001

# Snapshot management
python vm_manager.py snapshot --vm test-vm-001 --name pre-upgrade
python vm_manager.py restore --vm test-vm-001 --snapshot pre-upgrade

# Cleanup
python vm_manager.py destroy --vm test-vm-001
python vm_manager.py cleanup-old --days 7
```

## Red Hat Subscription Handling

For RHEL VMs, the framework supports:

1. **Activation Keys**: Pre-configured subscription activation
2. **Temporary Subscriptions**: Auto-register and unregister
3. **Employee Developer Subscriptions**: Use your Red Hat employee account
4. **Offline Testing**: Pre-cache repos for air-gapped testing

```yaml
# config.yaml
rhel_subscription:
  method: "activation_key"  # or "username_password" or "cached_repos"
  activation_key: "your-key"
  org_id: "your-org"
```

## Integration Points

### With upgrade-advisor
```python
# The test framework calls your existing tool
from upgrade_executor import UpgradeExecutor
from system_detector import SystemDetector

# Inside VM (via SSH)
system = SystemDetector.detect()
upgrade_path = UpgradePath.get_recommended_path(system)
executor = UpgradeExecutor(system, upgrade_path, create_rollback=True)
result = executor.execute_leapp_upgrade()
```

### With CI/CD
```bash
# Run in GitLab/GitHub Actions
- name: Test RHEL Upgrades
  run: |
    python vm_test_framework/test_runner.py --matrix rhel-matrix --junit results.xml
```

## Resource Requirements

### Per Test VM
- CPU: 2 cores
- RAM: 2-4 GB
- Disk: 20 GB (thin provisioned)

### Parallel Execution
- 3 parallel jobs: ~12 cores, 12 GB RAM, 60 GB disk
- Adjust based on your host system

### Storage Pool
- Templates: ~40 GB (all RHEL/Fedora versions)
- Active tests: ~60 GB (with 3 parallel)
- Results archive: ~10 GB/month

## Safety Features

- All VMs are isolated (NAT network by default)
- Automatic cleanup of failed tests
- Resource limits prevent runaway VMs
- Timeout protection on all operations
- Pre-flight checks before destructive operations

## Roadmap

- [ ] Support for Debian/Ubuntu upgrades
- [ ] Cloud VM support (AWS, Azure, GCP)
- [ ] Integration with upgrade-advisor AI assistant
- [ ] Performance regression testing
- [ ] Visual diff of config files
- [ ] Automatic bug report generation
- [ ] Test result trending dashboard
