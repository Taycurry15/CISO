#!/usr/bin/env python3
"""
Security Vulnerability Scanner for CMMC Platform
=================================================
Scans dependencies for known vulnerabilities and generates security reports.

Requirements:
  pip install safety pip-audit bandit

Usage:
  python security_scan.py
  python security_scan.py --report json
"""

import subprocess
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path


class SecurityScanner:
    """Comprehensive security scanner for the CMMC platform."""

    def __init__(self, output_format='text'):
        self.output_format = output_format
        self.results = {
            'timestamp': datetime.utcnow().isoformat(),
            'scans': {}
        }

    def run_safety_check(self):
        """Run Safety to check for known security vulnerabilities in dependencies."""
        print("[*] Running Safety vulnerability scan...")

        try:
            result = subprocess.run(
                ['safety', 'check', '--json', '--output', 'json'],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )

            if result.returncode == 0:
                print("[+] Safety scan completed: No known vulnerabilities found")
                self.results['scans']['safety'] = {
                    'status': 'pass',
                    'vulnerabilities': []
                }
            else:
                vulnerabilities = json.loads(result.stdout) if result.stdout else []
                print(f"[!] Safety scan found {len(vulnerabilities)} vulnerabilities")

                self.results['scans']['safety'] = {
                    'status': 'fail',
                    'vulnerabilities': vulnerabilities
                }

                # Print summary
                for vuln in vulnerabilities:
                    print(f"  - {vuln.get('package')}: {vuln.get('vulnerability')}")

        except FileNotFoundError:
            print("[!] Safety not installed. Install with: pip install safety")
            self.results['scans']['safety'] = {'status': 'not_run', 'error': 'safety not installed'}
        except Exception as e:
            print(f"[!] Error running Safety: {str(e)}")
            self.results['scans']['safety'] = {'status': 'error', 'error': str(e)}

    def run_pip_audit(self):
        """Run pip-audit to check for vulnerabilities."""
        print("\n[*] Running pip-audit vulnerability scan...")

        try:
            result = subprocess.run(
                ['pip-audit', '--format', 'json'],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )

            output_data = json.loads(result.stdout) if result.stdout else {}

            if result.returncode == 0:
                print("[+] pip-audit scan completed: No known vulnerabilities found")
                self.results['scans']['pip_audit'] = {
                    'status': 'pass',
                    'vulnerabilities': []
                }
            else:
                vulnerabilities = output_data.get('vulnerabilities', [])
                print(f"[!] pip-audit found {len(vulnerabilities)} vulnerabilities")

                self.results['scans']['pip_audit'] = {
                    'status': 'fail',
                    'vulnerabilities': vulnerabilities
                }

                # Print summary
                for vuln in vulnerabilities:
                    pkg = vuln.get('package', 'unknown')
                    version = vuln.get('version', 'unknown')
                    advisory = vuln.get('advisory', 'unknown')
                    print(f"  - {pkg}=={version}: {advisory}")

        except FileNotFoundError:
            print("[!] pip-audit not installed. Install with: pip install pip-audit")
            self.results['scans']['pip_audit'] = {'status': 'not_run', 'error': 'pip-audit not installed'}
        except Exception as e:
            print(f"[!] Error running pip-audit: {str(e)}")
            self.results['scans']['pip_audit'] = {'status': 'error', 'error': str(e)}

    def run_bandit_scan(self):
        """Run Bandit to find common security issues in Python code."""
        print("\n[*] Running Bandit security code scan...")

        try:
            result = subprocess.run(
                ['bandit', '-r', 'api/', '-f', 'json', '-ll'],  # -ll = medium/high severity only
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )

            output_data = json.loads(result.stdout) if result.stdout else {}
            results = output_data.get('results', [])

            if len(results) == 0:
                print("[+] Bandit scan completed: No security issues found")
                self.results['scans']['bandit'] = {
                    'status': 'pass',
                    'issues': []
                }
            else:
                print(f"[!] Bandit found {len(results)} potential security issues")

                self.results['scans']['bandit'] = {
                    'status': 'warn' if result.returncode == 0 else 'fail',
                    'issues': results
                }

                # Print summary
                for issue in results[:10]:  # First 10 issues
                    test_id = issue.get('test_id', 'unknown')
                    severity = issue.get('issue_severity', 'unknown')
                    filename = issue.get('filename', 'unknown')
                    line = issue.get('line_number', 'unknown')
                    text = issue.get('issue_text', 'unknown')
                    print(f"  - [{severity}] {test_id} in {filename}:{line}")
                    print(f"    {text}")

                if len(results) > 10:
                    print(f"  ... and {len(results) - 10} more")

        except FileNotFoundError:
            print("[!] Bandit not installed. Install with: pip install bandit")
            self.results['scans']['bandit'] = {'status': 'not_run', 'error': 'bandit not installed'}
        except Exception as e:
            print(f"[!] Error running Bandit: {str(e)}")
            self.results['scans']['bandit'] = {'status': 'error', 'error': str(e)}

    def check_docker_security(self):
        """Check Docker image security best practices."""
        print("\n[*] Checking Docker security configuration...")

        dockerfile_path = Path(__file__).parent / 'Dockerfile'

        if not dockerfile_path.exists():
            print("[!] Dockerfile not found")
            self.results['scans']['docker'] = {'status': 'not_run', 'error': 'Dockerfile not found'}
            return

        issues = []

        with open(dockerfile_path, 'r') as f:
            dockerfile_content = f.read()

            # Check for common security issues
            if 'USER root' in dockerfile_content:
                issues.append("Running as root user (use non-root user)")

            if 'FROM' in dockerfile_content and ':latest' in dockerfile_content:
                issues.append("Using :latest tag (pin to specific version)")

            if 'COPY . .' in dockerfile_content:
                issues.append("Copying entire directory (use specific files)")

        if len(issues) == 0:
            print("[+] Docker configuration looks secure")
            self.results['scans']['docker'] = {'status': 'pass', 'issues': []}
        else:
            print(f"[!] Found {len(issues)} Docker security issues:")
            for issue in issues:
                print(f"  - {issue}")

            self.results['scans']['docker'] = {'status': 'warn', 'issues': issues}

    def generate_report(self):
        """Generate and save security report."""
        print("\n" + "=" * 70)
        print("SECURITY SCAN SUMMARY")
        print("=" * 70)

        total_scans = len(self.results['scans'])
        passed = sum(1 for s in self.results['scans'].values() if s['status'] == 'pass')
        failed = sum(1 for s in self.results['scans'].values() if s['status'] == 'fail')
        warned = sum(1 for s in self.results['scans'].values() if s['status'] == 'warn')

        print(f"Total scans: {total_scans}")
        print(f"Passed: {passed}")
        print(f"Warned: {warned}")
        print(f"Failed: {failed}")
        print("=" * 70)

        # Determine overall status
        if failed > 0:
            print("\n[!] SECURITY AUDIT FAILED - Critical vulnerabilities found!")
            overall_status = 'FAIL'
        elif warned > 0:
            print("\n[!] SECURITY AUDIT WARNING - Potential issues found")
            overall_status = 'WARN'
        else:
            print("\n[+] SECURITY AUDIT PASSED - No vulnerabilities found")
            overall_status = 'PASS'

        self.results['overall_status'] = overall_status

        # Save report
        report_path = Path(__file__).parent / 'security_report.json'
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\nFull report saved to: {report_path}")

        return overall_status == 'PASS'

    def run_all_scans(self):
        """Run all security scans."""
        print("=" * 70)
        print("CMMC Platform Security Scanner")
        print("=" * 70)
        print()

        self.run_safety_check()
        self.run_pip_audit()
        self.run_bandit_scan()
        self.check_docker_security()

        return self.generate_report()


def main():
    parser = argparse.ArgumentParser(description='Security scanner for CMMC platform')
    parser.add_argument('--report', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')

    args = parser.parse_args()

    scanner = SecurityScanner(output_format=args.report)
    success = scanner.run_all_scans()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
