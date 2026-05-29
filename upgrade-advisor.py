#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0

"""Linux Upgrade Advisor CLI - Main entry point."""

import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from system_detector import SystemDetector
from upgrade_paths import UpgradePathFinder
from compatibility_checker import CompatibilityChecker
from backup_advisor import BackupAdvisor
from upgrade_executor import UpgradeExecutor
from ai_assistant import UpgradeAssistant
from rollback_manager import RollbackManager

console = Console()


@click.group()
@click.version_option(version='0.1.0-EXPERIMENTAL')
def cli():
    """Linux Upgrade Advisor - Analyze and execute OS upgrades for Fedora and RHEL.

    ⚠️  EXPERIMENTAL SOFTWARE - USE AT YOUR OWN RISK ⚠️

    This is untested prototype software. May cause complete data loss.
    ALWAYS backup data before use. Test on non-production systems only.
    Authors provide NO WARRANTY. See README.md for full warnings.
    """
    pass


@cli.command()
def check():
    """Check current system and display upgrade recommendations."""
    console.print("[bold blue]Linux Upgrade Advisor[/bold blue]\n")

    with console.status("[bold green]Detecting system..."):
        system = SystemDetector.detect()
        prereqs = SystemDetector.check_prerequisites()

    console.print(Panel(f"[bold]{system}[/bold]\nArchitecture: {system.architecture}\nKernel: {system.kernel}",
                       title="System Information", border_style="blue"))

    table = Table(title="Prerequisites")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="magenta")

    for check, status in prereqs.items():
        status_str = "✓" if status else "✗"
        color = "green" if status else "red"
        table.add_row(check.replace('_', ' ').title(), f"[{color}]{status_str}[/{color}]")

    console.print(table)

    with console.status("[bold green]Finding upgrade paths..."):
        paths = UpgradePathFinder.find_paths(system)

    if paths:
        for path in paths:
            if path.supported:
                console.print(f"\n[bold green]Available Upgrade:[/bold green] {system.os_name} {path.from_version} → {path.to_version}")
                console.print(f"[bold]Method:[/bold] {path.method.upper()}")
                console.print(f"[bold]Risk Level:[/bold] {path.risk_level.upper()}")
                console.print("\n[bold]Notes:[/bold]")
                for note in path.notes:
                    console.print(f"  • {note}")
            else:
                console.print(f"\n[bold yellow]No supported upgrade path available[/bold yellow]")
                for note in path.notes:
                    console.print(f"  • {note}")
    else:
        console.print("\n[bold red]No upgrade paths found for this system[/bold red]")


@cli.command()
def preflight():
    """Run pre-upgrade compatibility checks."""
    console.print("[bold blue]Pre-flight Compatibility Checks[/bold blue]\n")

    system = SystemDetector.detect()
    console.print(f"System: {system}\n")

    checker = CompatibilityChecker(system)

    with console.status("[bold green]Running compatibility checks..."):
        results = checker.run_all_checks()

    critical_failures = []
    warnings = []

    for result in results:
        if result.severity == 'critical' and not result.passed:
            critical_failures.append(result)
            console.print(f"[bold red]✗ CRITICAL:[/bold red] {result.name}")
            console.print(f"  {result.message}")
            if result.remediation:
                console.print(f"  [italic]Fix: {result.remediation}[/italic]")
        elif result.severity == 'warning' and not result.passed:
            warnings.append(result)
            console.print(f"[bold yellow]⚠ WARNING:[/bold yellow] {result.name}")
            console.print(f"  {result.message}")
            if result.remediation:
                console.print(f"  [italic]Fix: {result.remediation}[/italic]")
        else:
            console.print(f"[green]✓[/green] {result.name}: {result.message}")

    console.print()
    if critical_failures:
        console.print(f"[bold red]{len(critical_failures)} critical issue(s) must be resolved before upgrade[/bold red]")
    elif warnings:
        console.print(f"[bold yellow]{len(warnings)} warning(s) detected - review before upgrading[/bold yellow]")
    else:
        console.print("[bold green]All checks passed! System is ready for upgrade.[/bold green]")


@cli.command()
@click.option('--generate-script', is_flag=True, help='Generate backup script')
def backup():
    """Display backup recommendations."""
    console.print("[bold blue]Backup Recommendations[/bold blue]\n")

    system = SystemDetector.detect()
    recommendations = BackupAdvisor.get_recommendations(system)

    for priority in ['critical', 'recommended', 'optional']:
        priority_recs = [r for r in recommendations if r.priority == priority]
        if priority_recs:
            console.print(f"\n[bold]{priority.upper()}[/bold]")
            for rec in priority_recs:
                console.print(f"\n  [cyan]Target:[/cyan] {rec.target}")
                console.print(f"  [cyan]Method:[/cyan] {rec.method}")
                console.print(f"  [cyan]Reason:[/cyan] {rec.reason}")
                console.print(f"  [cyan]Size:[/cyan] {rec.estimated_size}")


@cli.command()
@click.option('--priority', type=click.Choice(['critical', 'recommended', 'optional']),
              default='recommended', help='Backup priority level')
def generate_backup_script(priority):
    """Generate a backup script."""
    system = SystemDetector.detect()
    recommendations = BackupAdvisor.get_recommendations(system)
    script = BackupAdvisor.generate_backup_script(recommendations, priority)

    script_path = '/tmp/pre-upgrade-backup.sh'
    with open(script_path, 'w') as f:
        f.write(script)

    console.print(f"[bold green]Backup script generated:[/bold green] {script_path}")
    console.print(f"\nRun with: [cyan]sudo bash {script_path}[/cyan]")


@cli.command()
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--i-accept-the-risks', is_flag=True, help='Acknowledge experimental software risks')
def upgrade(dry_run, i_accept_the_risks):
    """Execute the system upgrade.

    ⚠️  EXPERIMENTAL - May cause complete data loss!
    """
    if not dry_run and not i_accept_the_risks:
        console.print("\n[bold red]⚠️  EXPERIMENTAL SOFTWARE WARNING ⚠️[/bold red]\n")
        console.print("[yellow]This is UNTESTED prototype software that may cause:[/yellow]")
        console.print("  • Complete data loss")
        console.print("  • System corruption")
        console.print("  • Unbootable system")
        console.print("  • Failed upgrades requiring reinstallation\n")
        console.print("[bold red]REQUIRED before proceeding:[/bold red]")
        console.print("  ✓ Backup ALL data to external storage")
        console.print("  ✓ Verify backups are restorable")
        console.print("  ✓ Have recovery plan ready")
        console.print("  ✓ Test on non-production system first\n")
        console.print("[dim]To proceed, add flag: --i-accept-the-risks[/dim]\n")
        sys.exit(1)

    system = SystemDetector.detect()
    paths = UpgradePathFinder.find_paths(system)
    recommended_path = UpgradePathFinder.recommend_best_path(paths)

    if not recommended_path:
        console.print("[bold red]No upgrade path available[/bold red]")
        sys.exit(1)

    console.print(f"[bold]Upgrade Plan:[/bold] {system.os_name} {recommended_path.from_version} → {recommended_path.to_version}")
    console.print(f"[bold]Method:[/bold] {recommended_path.method}")

    if not dry_run:
        console.print("\n[bold yellow]⚠️  You are using experimental software[/bold yellow]")
        console.print("[yellow]Rollback features are untested and may fail[/yellow]")

        if not click.confirm('\nDo you have verified backups and accept all risks?', default=False):
            console.print("\n[green]Wise choice. Backup your data first.[/green]")
            sys.exit(0)

    if dry_run:
        console.print("\n[bold yellow]DRY RUN - No changes will be made[/bold yellow]")
        executor = UpgradeExecutor(system, recommended_path)
        prep = executor.prepare_upgrade()
        console.print(f"\nMethod: {prep['method']}")
        console.print(f"Ready: {prep['ready']}")
        if prep['actions_needed']:
            console.print("\nActions needed:")
            for action in prep['actions_needed']:
                console.print(f"  • {action}")
        return

    prereqs = SystemDetector.check_prerequisites()
    if not prereqs.get('has_root'):
        console.print("[bold red]Root privileges required for upgrade[/bold red]")
        sys.exit(1)

    executor = UpgradeExecutor(system, recommended_path)

    if recommended_path.method == 'leapp':
        result = executor.execute_leapp_upgrade()
    else:
        result = executor.execute_ansible_upgrade()

    if result['success']:
        console.print(f"\n[bold green]Upgrade {result['phase']} successful![/bold green]")
        console.print(result['message'])
        if result.get('rollback_point'):
            console.print(f"\n[cyan]Rollback point available:[/cyan] {result['rollback_point']}")
            console.print(f"[cyan]To rollback if needed:[/cyan] ./upgrade-advisor.py rollback {result['rollback_point']}")
    else:
        console.print(f"\n[bold red]Upgrade {result['phase']} failed[/bold red]")
        console.print(result['message'])
        if result.get('rollback_point'):
            console.print(f"\n[yellow]Rollback point available:[/yellow] {result['rollback_point']}")
            console.print(f"[yellow]To rollback:[/yellow] ./upgrade-advisor.py rollback {result['rollback_point']}")
        if 'output' in result:
            console.print("\nDetails:")
            console.print(result['output'])


@cli.command()
@click.option('--export', help='Export conversation to file when done')
def assistant(export):
    """Interactive AI assistant to guide you through the upgrade process."""
    console.print("[bold blue]🤖 AI Upgrade Assistant[/bold blue]\n")

    try:
        with console.status("[bold green]Initializing AI assistant..."):
            ai = UpgradeAssistant()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print("\n[yellow]To use the AI assistant:[/yellow]")
        console.print("1. Get an API key from https://console.anthropic.com/")
        console.print("2. Create a .env file with: ANTHROPIC_API_KEY=your_key_here")
        console.print("3. Or set environment variable: export ANTHROPIC_API_KEY=your_key")
        sys.exit(1)

    context = ai.get_context_summary()
    console.print("[dim]AI assistant loaded with your system context[/dim]\n")

    greeting = ai.start_guided_session()
    console.print(f"[bold cyan]Assistant:[/bold cyan] {greeting}\n")

    console.print("[dim]Type 'exit' or 'quit' to end the session[/dim]")
    console.print("[dim]Type 'context' to see system information[/dim]")
    console.print("[dim]Type 'reset' to start a new conversation[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'bye']:
                console.print("\n[cyan]Assistant: Goodbye! Stay safe with your upgrade.[/cyan]")
                break

            if user_input.lower() == 'context':
                console.print("\n[bold]System Context:[/bold]")
                console.print(context)
                console.print()
                continue

            if user_input.lower() == 'reset':
                ai.reset_conversation()
                console.print("\n[yellow]Conversation reset. Starting fresh![/yellow]\n")
                greeting = ai.start_guided_session()
                console.print(f"[bold cyan]Assistant:[/bold cyan] {greeting}\n")
                continue

            with console.status("[bold green]Assistant is thinking..."):
                response = ai.chat(user_input)

            console.print(f"\n[bold cyan]Assistant:[/bold cyan] {response}\n")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Session interrupted[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}\n")

    if export:
        ai.export_conversation(export)
        console.print(f"\n[green]Conversation exported to {export}[/green]")


@cli.command()
def list_rollbacks():
    """List available rollback points."""
    console.print("[bold blue]Available Rollback Points[/bold blue]\n")

    rollback_caps = SystemDetector.check_rollback_capabilities()

    console.print(f"[bold]Rollback Capabilities:[/bold]")
    for method in rollback_caps.get('methods', []):
        console.print(f"  ✓ {method}")

    if not rollback_caps.get('methods'):
        console.print("  [yellow]No automatic rollback methods available[/yellow]")
        console.print("  [dim]Install boom-boot or snapm for automatic rollback support[/dim]")
        return

    rollback_points = RollbackManager.list_rollback_points()

    if not rollback_points:
        console.print("\n[yellow]No rollback points created yet[/yellow]")
        console.print("[dim]Rollback points are created automatically before upgrades[/dim]")
        return

    console.print(f"\n[bold]Saved Rollback Points:[/bold]")
    table = Table()
    table.add_column("ID", style="cyan")
    table.add_column("Method", style="magenta")
    table.add_column("Created", style="green")
    table.add_column("Description")

    for rp in rollback_points:
        table.add_row(
            rp.identifier,
            rp.method,
            rp.timestamp[:19],
            rp.description
        )

    console.print(table)
    console.print(f"\n[dim]To rollback: ./upgrade-advisor.py rollback <ID>[/dim]")


@cli.command()
@click.argument('identifier')
@click.option('--i-accept-the-risks', is_flag=True, help='Acknowledge experimental software risks')
def rollback(identifier, i_accept_the_risks):
    """Rollback to a previous snapshot.

    ⚠️  EXPERIMENTAL - Rollback may fail and cause data loss!
    """
    if not i_accept_the_risks:
        console.print("\n[bold red]⚠️  EXPERIMENTAL ROLLBACK WARNING ⚠️[/bold red]\n")
        console.print("[yellow]Rollback features are UNTESTED and may:[/yellow]")
        console.print("  • Fail to restore your system")
        console.print("  • Cause additional data loss")
        console.print("  • Leave system in unbootable state")
        console.print("  • Corrupt existing snapshots\n")
        console.print("[bold]Only use if you have external backups![/bold]\n")
        console.print("[dim]To proceed, add flag: --i-accept-the-risks[/dim]\n")
        sys.exit(1)

    if not click.confirm('Do you have verified external backups and accept all risks?', default=False):
        console.print("\n[green]Recommended. Ensure you have external backups before rollback.[/green]")
        sys.exit(0)

    console.print(f"\n[bold blue]Rolling back to: {identifier}[/bold blue]\n")

    try:
        rollback_points = RollbackManager.list_rollback_points()
        target = next((rp for rp in rollback_points if rp.identifier == identifier), None)

        if not target:
            console.print(f"[bold red]Rollback point '{identifier}' not found[/bold red]")
            console.print("\nAvailable rollback points:")
            for rp in rollback_points:
                console.print(f"  - {rp.identifier} ({rp.method})")
            sys.exit(1)

        console.print(f"[bold]Method:[/bold] {target.method}")
        console.print(f"[bold]Created:[/bold] {target.timestamp}")
        console.print(f"[bold]Description:[/bold] {target.description}\n")

        with console.status("[bold yellow]Initiating rollback..."):
            success = RollbackManager.execute_rollback(identifier)

        if success:
            console.print("\n[bold green]Rollback initiated successfully![/bold green]")
            console.print("[yellow]System may reboot to complete rollback[/yellow]")
        else:
            console.print("\n[bold yellow]Manual intervention required[/bold yellow]")
            console.print("See instructions above")

    except Exception as e:
        console.print(f"\n[bold red]Rollback failed:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option('--method', type=click.Choice(['auto', 'snapm', 'boom', 'lvm', 'btrfs']),
              default='auto', help='Rollback method to use')
def create_snapshot(method):
    """Create a manual system snapshot for rollback.

    ⚠️  EXPERIMENTAL - Snapshots may be unreliable!
    """
    console.print("[bold blue]Creating System Snapshot[/bold blue]\n")
    console.print("[yellow]⚠️  Snapshot features are experimental and untested[/yellow]")
    console.print("[yellow]Do not rely on snapshots as your only backup![/yellow]\n")

    prereqs = SystemDetector.check_prerequisites()
    if not prereqs.get('has_root'):
        console.print("[bold red]Root privileges required to create snapshots[/bold red]")
        sys.exit(1)

    try:
        with console.status(f"[bold green]Creating snapshot using {method}..."):
            rollback_point = RollbackManager.create_pre_upgrade_snapshot(
                method=method,
                description=f"Manual snapshot created via upgrade-advisor"
            )

        console.print(f"[bold green]✓ Snapshot created successfully![/bold green]")
        console.print(f"\n[bold]Details:[/bold]")
        console.print(f"  ID: {rollback_point.identifier}")
        console.print(f"  Method: {rollback_point.method}")
        console.print(f"  Timestamp: {rollback_point.timestamp}")
        console.print(f"\n[cyan]To rollback:[/cyan] ./upgrade-advisor.py rollback {rollback_point.identifier}")

    except Exception as e:
        console.print(f"\n[bold red]Snapshot creation failed:[/bold red] {e}")
        console.print("\n[yellow]Troubleshooting:[/yellow]")
        console.print("  - Ensure boom-boot or snapm is installed")
        console.print("  - Check available disk space for snapshots")
        console.print("  - Verify LVM/Btrfs configuration if using those methods")
        sys.exit(1)


if __name__ == '__main__':
    cli()
