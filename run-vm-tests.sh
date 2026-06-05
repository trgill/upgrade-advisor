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

setup() {
    echo -e "${GREEN}Setting up VM Test Framework...${NC}"

    # Create directories
    echo "Creating directories..."
    sudo mkdir -p /var/lib/libvirt/images/upgrade-test/{templates,instances}
    sudo mkdir -p /var/lib/libvirt/images/isos
    sudo chown -R $USER:libvirt /var/lib/libvirt/images/upgrade-test 2>/dev/null || true

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
    fi

    # Check default network
    if ! virsh net-list --all | grep -q default; then
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

create_template() {
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
    echo -e "${GREEN}Running smoke tests...${NC}"
    python vm_test_framework/test_runner.py \
        --config vm_test_framework/test_configs/rhel9-to-10.yaml \
        --filter-tags smoke
}

run_full() {
    echo -e "${GREEN}Running full test suite...${NC}"
    python vm_test_framework/test_runner.py \
        --config vm_test_framework/test_configs/rhel9-to-10.yaml
}

run_parallel() {
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

# Main
case "$1" in
    setup)
        setup
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
