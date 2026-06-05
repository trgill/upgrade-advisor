#!/usr/bin/env python3
# Copyright Red Hat
# SPDX-License-Identifier: Apache-2.0

"""Reporting and visualization for test results."""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class TestReporter:
    """Generate reports from test results."""

    def __init__(self, results_dir: str = "vm_test_framework/results"):
        """Initialize reporter."""
        self.results_dir = Path(results_dir)

    def get_latest_run(self) -> Optional[Path]:
        """Get the most recent test run directory."""
        if not self.results_dir.exists():
            return None

        runs = sorted(self.results_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        return runs[0] if runs else None

    def load_summary(self, run_dir: Path) -> Dict:
        """Load summary.json from a test run."""
        summary_file = run_dir / 'summary.json'
        if not summary_file.exists():
            return {}

        with open(summary_file) as f:
            return json.load(f)

    def print_summary(self, run_dir: Optional[Path] = None):
        """Print a formatted summary of test results."""
        if run_dir is None:
            run_dir = self.get_latest_run()

        if not run_dir:
            print("No test results found")
            return

        summary = self.load_summary(run_dir)
        if not summary:
            print(f"No summary found in {run_dir}")
            return

        # Header
        print(f"\n{'='*80}")
        print(f"TEST RESULTS SUMMARY")
        print(f"{'='*80}")
        print(f"Run: {run_dir.name}")
        print(f"Timestamp: {summary.get('timestamp', 'unknown')}")
        print(f"{'='*80}\n")

        # Overall statistics
        total = summary.get('total_tests', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        errors = summary.get('errors', 0)
        timeouts = summary.get('timeouts', 0)
        skipped = summary.get('skipped', 0)
        duration = summary.get('total_duration_seconds', 0)

        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"Overall Statistics:")
        print(f"  Total Tests:    {total}")
        print(f"  ✓ Passed:       {passed} ({pass_rate:.1f}%)")
        print(f"  ✗ Failed:       {failed}")
        print(f"  ⚠ Errors:       {errors}")
        print(f"  ⏱ Timeouts:     {timeouts}")
        print(f"  ⊘ Skipped:      {skipped}")
        print(f"  Duration:       {self._format_duration(duration)}")
        print()

        # Results by test
        results = summary.get('results', [])

        if passed > 0:
            print(f"Passed Tests ({passed}):")
            for r in results:
                if r['status'] == 'pass':
                    print(f"  ✓ {r['test_name']}")
                    print(f"    {r['source_version']} → {r['target_version']}")
                    print(f"    Duration: {self._format_duration(r['duration_seconds'])}")
            print()

        if failed > 0:
            print(f"Failed Tests ({failed}):")
            for r in results:
                if r['status'] == 'fail':
                    print(f"  ✗ {r['test_name']}")
                    print(f"    {r['source_version']} → {r['target_version']}")
                    print(f"    Error: {r.get('error_message', 'Unknown error')}")
                    if r.get('validation_results'):
                        failed_validations = [v for v in r['validation_results'] if not v['passed']]
                        if failed_validations:
                            print(f"    Failed validations:")
                            for v in failed_validations:
                                critical = " [CRITICAL]" if v.get('critical') else ""
                                print(f"      - {v['name']}{critical}")
            print()

        if errors > 0:
            print(f"Error Tests ({errors}):")
            for r in results:
                if r['status'] == 'error':
                    print(f"  ⚠ {r['test_name']}")
                    print(f"    Error: {r.get('error_message', 'Unknown error')}")
            print()

        if timeouts > 0:
            print(f"Timeout Tests ({timeouts}):")
            for r in results:
                if r['status'] == 'timeout':
                    print(f"  ⏱ {r['test_name']}")
                    print(f"    Exceeded timeout limit")
            print()

        # Footer
        print(f"{'='*80}")
        print(f"Results directory: {run_dir}")
        print(f"{'='*80}\n")

        # Return exit code
        return 0 if failed == 0 and errors == 0 else 1

    def generate_html_report(self, run_dir: Optional[Path] = None, output_file: Optional[str] = None):
        """Generate an HTML report."""
        if run_dir is None:
            run_dir = self.get_latest_run()

        if not run_dir:
            print("No test results found")
            return

        summary = self.load_summary(run_dir)
        if not summary:
            print(f"No summary found in {run_dir}")
            return

        if output_file is None:
            output_file = str(run_dir / 'report.html')

        html = self._generate_html(summary, run_dir)

        with open(output_file, 'w') as f:
            f.write(html)

        print(f"HTML report generated: {output_file}")

    def _generate_html(self, summary: Dict, run_dir: Path) -> str:
        """Generate HTML report content."""
        total = summary.get('total_tests', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        pass_rate = (passed / total * 100) if total > 0 else 0

        # Generate HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Upgrade Test Results - {run_dir.name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-box {{
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-box.total {{ background: #e3f2fd; }}
        .stat-box.passed {{ background: #e8f5e9; }}
        .stat-box.failed {{ background: #ffebee; }}
        .stat-box .number {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-box .label {{
            color: #666;
            font-size: 0.9em;
        }}
        .pass-rate {{
            font-size: 3em;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
            color: {'#4caf50' if pass_rate >= 80 else '#ff9800' if pass_rate >= 60 else '#f44336'};
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f5f5f5;
            font-weight: bold;
        }}
        .status-pass {{ color: #4caf50; font-weight: bold; }}
        .status-fail {{ color: #f44336; font-weight: bold; }}
        .status-error {{ color: #ff9800; font-weight: bold; }}
        .status-timeout {{ color: #ff9800; font-weight: bold; }}
        .test-details {{
            background: #f9f9f9;
            padding: 10px;
            border-left: 3px solid #ddd;
            margin: 5px 0;
        }}
        .validation-item {{
            margin: 5px 0;
            padding: 5px;
        }}
        .validation-pass {{ color: #4caf50; }}
        .validation-fail {{ color: #f44336; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Upgrade Test Results</h1>
        <p><strong>Run:</strong> {run_dir.name}</p>
        <p><strong>Timestamp:</strong> {summary.get('timestamp', 'unknown')}</p>

        <div class="pass-rate">{pass_rate:.1f}% Pass Rate</div>

        <div class="summary">
            <div class="stat-box total">
                <div class="label">Total Tests</div>
                <div class="number">{total}</div>
            </div>
            <div class="stat-box passed">
                <div class="label">Passed</div>
                <div class="number">{passed}</div>
            </div>
            <div class="stat-box failed">
                <div class="label">Failed</div>
                <div class="number">{failed}</div>
            </div>
        </div>

        <h2>Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Upgrade Path</th>
                    <th>Status</th>
                    <th>Duration</th>
                </tr>
            </thead>
            <tbody>
"""

        # Add test results
        for result in summary.get('results', []):
            status_class = f"status-{result['status']}"
            status_symbol = {
                'pass': '✓',
                'fail': '✗',
                'error': '⚠',
                'timeout': '⏱',
                'skipped': '⊘'
            }.get(result['status'], '?')

            html += f"""
                <tr>
                    <td>{result['test_name']}</td>
                    <td>{result['source_version']} → {result['target_version']}</td>
                    <td class="{status_class}">{status_symbol} {result['status'].upper()}</td>
                    <td>{self._format_duration(result['duration_seconds'])}</td>
                </tr>
"""

            # Add error details if present
            if result.get('error_message'):
                html += f"""
                <tr>
                    <td colspan="4">
                        <div class="test-details">
                            <strong>Error:</strong> {result['error_message']}
                        </div>
                    </td>
                </tr>
"""

            # Add validation results if present
            if result.get('validation_results'):
                validation_html = "<strong>Validations:</strong><br>"
                for v in result['validation_results']:
                    v_class = 'validation-pass' if v['passed'] else 'validation-fail'
                    v_symbol = '✓' if v['passed'] else '✗'
                    critical = ' [CRITICAL]' if v.get('critical') else ''
                    validation_html += f"<div class='validation-item {v_class}'>{v_symbol} {v['name']}{critical}</div>"

                html += f"""
                <tr>
                    <td colspan="4">
                        <div class="test-details">
                            {validation_html}
                        </div>
                    </td>
                </tr>
"""

        html += """
            </tbody>
        </table>

        <h2>Statistics</h2>
        <p><strong>Total Duration:</strong> """ + self._format_duration(summary.get('total_duration_seconds', 0)) + """</p>
        <p><strong>Results Directory:</strong> <code>""" + str(run_dir) + """</code></p>
    </div>
</body>
</html>
"""

        return html

    def compare_runs(self, run1_dir: Path, run2_dir: Path):
        """Compare two test runs."""
        summary1 = self.load_summary(run1_dir)
        summary2 = self.load_summary(run2_dir)

        print(f"\n{'='*80}")
        print(f"COMPARISON: {run1_dir.name} vs {run2_dir.name}")
        print(f"{'='*80}\n")

        print(f"{'Metric':<30} {'Run 1':<20} {'Run 2':<20} {'Change':<20}")
        print(f"{'-'*90}")

        metrics = [
            ('Total Tests', 'total_tests'),
            ('Passed', 'passed'),
            ('Failed', 'failed'),
            ('Errors', 'errors'),
            ('Duration (s)', 'total_duration_seconds')
        ]

        for label, key in metrics:
            val1 = summary1.get(key, 0)
            val2 = summary2.get(key, 0)
            change = val2 - val1
            change_str = f"{change:+.0f}" if isinstance(change, (int, float)) else str(change)

            print(f"{label:<30} {val1:<20} {val2:<20} {change_str:<20}")

        print()

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable form."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"


def main():
    """CLI for test reporting."""
    import argparse

    parser = argparse.ArgumentParser(description='VM Test Framework - Reporting')
    parser.add_argument('--show-latest', action='store_true',
                       help='Show summary of latest test run')
    parser.add_argument('--run-dir', help='Specific run directory to report on')
    parser.add_argument('--html', action='store_true',
                       help='Generate HTML report')
    parser.add_argument('--output', help='HTML output file')
    parser.add_argument('--compare', nargs=2, metavar=('RUN1', 'RUN2'),
                       help='Compare two test runs')

    args = parser.parse_args()

    reporter = TestReporter()

    if args.compare:
        run1 = Path(args.compare[0])
        run2 = Path(args.compare[1])
        reporter.compare_runs(run1, run2)

    elif args.html:
        run_dir = Path(args.run_dir) if args.run_dir else None
        reporter.generate_html_report(run_dir, args.output)

    elif args.show_latest or args.run_dir:
        run_dir = Path(args.run_dir) if args.run_dir else None
        exit_code = reporter.print_summary(run_dir)
        sys.exit(exit_code)

    else:
        # Default: show latest
        exit_code = reporter.print_summary()
        sys.exit(exit_code)


if __name__ == '__main__':
    main()
