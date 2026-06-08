#!/bin/bash
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0

# VM Test Framework - Easy Runner Script
# Simplifies running VM-based upgrade tests

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    cat <<EOF
VM Test Framework - Easy Runner

Usage: $0 <command> [options]

Commands:
    setup           - Initial setup (create directories, config)
    check           - Verify permissions and prerequisites
    create-template - Create a VM template
    smoke           - Run smoke tests (quick validation)
    full            - Run full test suite
    parallel        - Run tests in parallel (3 jobs)
    report          - Show latest test results
    html            - Generate HTML report
    clean           - Clean up old test results
    help            - Show this help

Examples:
    # Initial setup
    $0 setup

    # Create RHEL 9 template
    $0 create-template rhel 9.3 /path/to/rhel-9.3-x86_64-dvd.iso

    # Run smoke test
    $0 smoke

    # Run full suite in parallel
    $0 parallel

    # View results
    $0 report
    $0 html

EOF
    exit 0
}

check_permissions() {
    local needs_setup=0

    # Check if user is in libvirt group
    if ! groups | grep -q libvirt; then
        echo -e "${YELLOW}⚠ You are not in the 'libvirt' group${NC}"
        echo "  This is required to manage VMs without sudo"
        needs_setup=1
    fi

    # Check if we can access libvirt without sudo
    if ! virsh -c qemu:///system list >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Cannot access libvirt daemon${NC}"
        echo "  You may need to log out and back in after group changes"
        needs_setup=1
    fi

    return $needs_setup
}

fix_permissions() {
    echo -e "${GREEN}Fixing permissions...${NC}"

    # Add user to libvirt group
    if ! groups | grep -q libvirt; then
        echo "Adding $USER to libvirt group..."
        sudo usermod -a -G libvirt $USER
        echo -e "${YELLOW}⚠ Group added. You must log out and back in (or run 'newgrp libvirt') for this to take effect${NC}"
        echo ""
        echo "After logging back in, run this setup again."
        exit 1
    fi

    # Fix storage directory permissions
    if [ -d /var/lib/libvirt/images/upgrade-test ]; then
        echo "Fixing storage directory permissions..."
        sudo chown -R $USER:libvirt /var/lib/libvirt/images/upgrade-test
        sudo chmod -R 775 /var/lib/libvirt/images/upgrade-test
    fi

    echo -e "${GREEN}✓ Permissions configured${NC}"
}

setup() {
    echo -e "${GREEN}Setting up VM Test Framework...${NC}"
    echo ""

    # Check permissions first
    if ! check_permissions; then
        echo ""
        read -p "Would you like to fix permissions now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            fix_permissions
        else
            echo -e "${RED}Cannot continue without proper permissions${NC}"
            exit 1
        fi
    fi

    # Create directories
    echo "Creating directories..."
    sudo mkdir -p /var/lib/libvirt/images/upgrade-test/{templates,instances}
    sudo mkdir -p /var/lib/libvirt/images/isos
    sudo chown -R $USER:libvirt /var/lib/libvirt/images/upgrade-test 2>/dev/null || true
    sudo chmod -R 775 /var/lib/libvirt/images/upgrade-test 2>/dev/null || true

    mkdir -p vm_test_framework/results
    mkdir -p vm_test_framework/logs
    mkdir -p vm_test_framework/kickstart_templates

    # Create config if doesn't exist
    if [ ! -f vm_test_framework/config.yaml ]; then
        echo "Creating config.yaml..."
        cp vm_test_framework/config.example.yaml vm_test_framework/config.yaml
        echo -e "${YELLOW}⚠ Edit vm_test_framework/config.yaml to add your RHEL subscription details${NC}"
    fi

    # Install Python dependencies
    echo "Installing Python dependencies..."
    pip install -r vm_test_framework/requirements.txt --quiet

    # Check libvirt
    if ! systemctl is-active --quiet libvirtd; then
        echo -e "${YELLOW}⚠ libvirtd is not running. Starting...${NC}"
        sudo systemctl start libvirtd
        sudo systemctl enable libvirtd
    fi

    # Check default network
    if ! virsh net-list --all 2>/dev/null | grep -q default; then
        echo -e "${YELLOW}⚠ Creating default libvirt network...${NC}"
        virsh net-define /usr/share/libvirt/networks/default.xml
        virsh net-start default
        virsh net-autostart default
    fi

    echo -e "${GREEN}✓ Setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Download RHEL ISO to /var/lib/libvirt/images/isos/"
    echo "  2. Edit vm_test_framework/config.yaml with your subscription"
    echo "  3. Run: $0 create-template rhel 9.3 /path/to/rhel.iso"
}

preflight_check() {
    # Quick check before running any VM operations
    if ! check_permissions; then
        echo -e "${RED}✗ Permission problem detected${NC}"
        echo ""
        echo "Please run: $0 setup"
        echo "Or manually fix with:"
        echo "  sudo usermod -a -G libvirt $USER"
        echo "  newgrp libvirt  # or log out and back in"
        exit 1
    fi

    # Check libvirt is running
    if ! systemctl is-active --quiet libvirtd; then
        echo -e "${RED}✗ libvirtd is not running${NC}"
        echo "Start with: sudo systemctl start libvirtd"
        echo "Or run: $0 setup"
        exit 1
    fi

    # Verify we can actually connect
    if ! virsh -c qemu:///system list >/dev/null 2>&1; then
        echo -e "${RED}✗ Cannot connect to libvirt${NC}"
        echo "You may need to log out and back in after being added to libvirt group"
        exit 1
    fi
}

create_template() {
    preflight_check

    local os=$1
    local version=$2
    local iso=$3

    if [ -z "$os" ] || [ -z "$version" ] || [ -z "$iso" ]; then
        echo "Usage: $0 create-template <os> <version> <iso-path>"
        echo "Example: $0 create-template rhel 9.3 /var/lib/libvirt/images/isos/rhel-9.3-x86_64-dvd.iso"
        exit 1
    fi

    if [ ! -f "$iso" ]; then
        echo -e "${RED}✗ ISO file not found: $iso${NC}"
        exit 1
    fi

    echo -e "${GREEN}Creating template: $os-$version${NC}"
    python vm_test_framework/vm_manager.py create-template \
        --os "$os" \
        --version "$version" \
        --profile minimal \
        --iso "$iso"

    echo -e "${GREEN}✓ Template created successfully${NC}"
}

run_smoke() {
    preflight_check
    echo -e "${GREEN}Running smoke tests...${NC}"
    python vm_test_framework/test_runner.py \
        --config vm_test_framework/test_configs/rhel9-to-10.yaml \
        --filter-tags smoke
}

run_full() {
    preflight_check
    echo -e "${GREEN}Running full test suite...${NC}"
    python vm_test_framework/test_runner.py \
        --config vm_test_framework/test_configs/rhel9-to-10.yaml
}

run_parallel() {
    preflight_check
    echo -e "${GREEN}Running tests in parallel (3 jobs)...${NC}"
    python vm_test_framework/test_runner.py \
        --config vm_test_framework/test_configs/rhel9-to-10.yaml \
        --parallel 3
}

show_report() {
    python vm_test_framework/reporting.py --show-latest
}

generate_html() {
    python vm_test_framework/reporting.py --html
    latest=$(ls -t vm_test_framework/results | head -1)
    echo ""
    echo -e "${GREEN}HTML report: vm_test_framework/results/$latest/report.html${NC}"
    echo "Open with: firefox vm_test_framework/results/$latest/report.html"
}

clean_results() {
    echo -e "${YELLOW}Cleaning up old test results...${NC}"
    find vm_test_framework/results -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

run_check() {
    echo -e "${GREEN}Checking VM test framework prerequisites...${NC}"
    echo ""

    local all_good=1

    # Check user groups
    echo -n "Checking libvirt group membership... "
    if groups | grep -q libvirt; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo "  Run: sudo usermod -a -G libvirt $USER"
        echo "  Then log out and back in"
        all_good=0
    fi

    # Check libvirt daemon
    echo -n "Checking libvirtd service... "
    if systemctl is-active --quiet libvirtd; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo "  Run: sudo systemctl start libvirtd"
        all_good=0
    fi

    # Check libvirt connection
    echo -n "Checking libvirt connection... "
    if virsh -c qemu:///system list >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo "  Cannot connect to libvirt"
        echo "  May need to log out/in after group change"
        all_good=0
    fi

    # Check storage directories
    echo -n "Checking storage directories... "
    if [ -d /var/lib/libvirt/images/upgrade-test ]; then
        if [ -w /var/lib/libvirt/images/upgrade-test ]; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${YELLOW}⚠${NC} (exists but not writable)"
            echo "  Run: sudo chown -R $USER:libvirt /var/lib/libvirt/images/upgrade-test"
            all_good=0
        fi
    else
        echo -e "${YELLOW}⚠${NC} (not created yet)"
        echo "  Run: $0 setup"
    fi

    # Check Python dependencies
    echo -n "Checking Python dependencies... "
    if python3 -c "import yaml, libvirt" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo "  Run: pip install -r vm_test_framework/requirements.txt"
        all_good=0
    fi

    # Check config file
    echo -n "Checking configuration... "
    if [ -f vm_test_framework/config.yaml ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠${NC} (not created yet)"
        echo "  Run: $0 setup"
    fi

    echo ""
    if [ $all_good -eq 1 ]; then
        echo -e "${GREEN}✓ All checks passed! Ready to run tests.${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Some issues detected. Run '$0 setup' to fix.${NC}"
        return 1
    fi
}

# Main
case "$1" in
    setup)
        setup
        ;;
    check)
        run_check
        ;;
    create-template)
        shift
        create_template "$@"
        ;;
    smoke)
        run_smoke
        ;;
    full)
        run_full
        ;;
    parallel)
        run_parallel
        ;;
    report)
        show_report
        ;;
    html)
        generate_html
        ;;
    clean)
        clean_results
        ;;
    help|--help|-h|"")
        usage
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        usage
        ;;
esac
