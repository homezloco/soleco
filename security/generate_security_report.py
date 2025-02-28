#!/usr/bin/env python3
"""
Generate a comprehensive security report for the Soleco project.

This script runs various security tools and combines their results into
a single comprehensive report.
"""

import os
import sys
import subprocess
import argparse
import logging
import json
import importlib.util
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('generate_security_report')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate a comprehensive security report')
    parser.add_argument('--codebase', type=str, default='../backend',
                        help='Path to the codebase to scan')
    parser.add_argument('--requirements', type=str, default='../backend/requirements.txt',
                        help='Path to requirements.txt file')
    parser.add_argument('--output', type=str, default='security_report.json',
                        help='Output file for the security report')
    parser.add_argument('--html', action='store_true',
                        help='Generate HTML report in addition to JSON')
    return parser.parse_args()

def run_security_audit(codebase_path, output_file):
    """
    Run the security audit script.
    
    Args:
        codebase_path: Path to the codebase to audit
        output_file: Output file for the audit report
        
    Returns:
        dict: Audit results
    """
    logger.info(f"Running security audit on {codebase_path}")
    
    # Import the security_audit module
    spec = importlib.util.spec_from_file_location(
        "security_audit",
        os.path.join(os.path.dirname(__file__), "security_audit.py")
    )
    security_audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(security_audit)
    
    # Run the audit
    results = security_audit.run_security_audit(codebase_path)
    
    # Write results to file
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Security audit complete. Results written to {output_file}")
    
    return results

def run_bandit_scan(codebase_path, output_file):
    """
    Run Bandit security scan.
    
    Args:
        codebase_path: Path to the codebase to scan
        output_file: Output file for the scan report
        
    Returns:
        bool: True if the scan completed successfully, False otherwise
    """
    logger.info(f"Running Bandit security scan on {codebase_path}")
    
    try:
        # Check if Bandit is installed
        subprocess.run(['bandit', '--version'], capture_output=True, check=True)
        
        # Run Bandit
        cmd = [
            'bandit',
            '-r',  # Recursive
            codebase_path,
            '-f', 'json',  # Output format
            '-o', output_file,  # Output file
            '--exclude', '*/tests/*,*/venv/*,*/.venv/*'  # Exclude test files and virtual environments
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return result.returncode == 0 or "Issues found" in result.stderr or "Issues found" in result.stdout
    
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Bandit not installed, skipping scan")
        return False

def run_safety_check(requirements_file, output_file):
    """
    Run safety check on the requirements file.
    
    Args:
        requirements_file: Path to requirements.txt file
        output_file: Output file for the scan report
        
    Returns:
        bool: True if the scan completed successfully, False otherwise
    """
    logger.info(f"Checking dependencies in {requirements_file} for vulnerabilities")
    
    try:
        # Check if safety is installed
        subprocess.run(['safety', '--version'], capture_output=True, check=True)
        
        # Run safety check
        cmd = [
            'safety',
            'check',
            '-r', requirements_file,  # Requirements file
            '--json',  # JSON output
            '--output', output_file,  # Output file
            '--full-report'  # Include full vulnerability details
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return True
    
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Safety not installed, skipping check")
        return False

def generate_html_report(json_report_path, html_report_path):
    """
    Generate an HTML report from the JSON report.
    
    Args:
        json_report_path: Path to the JSON report
        html_report_path: Path to the HTML report to generate
        
    Returns:
        bool: True if the report was generated successfully, False otherwise
    """
    logger.info(f"Generating HTML report from {json_report_path}")
    
    try:
        # Load the JSON report
        with open(json_report_path, 'r') as f:
            report = json.load(f)
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Soleco Security Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3 {{
            color: #333;
        }}
        .summary {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .finding {{
            border: 1px solid #ddd;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
        }}
        .high {{
            border-left: 5px solid #d9534f;
        }}
        .medium {{
            border-left: 5px solid #f0ad4e;
        }}
        .low {{
            border-left: 5px solid #5bc0de;
        }}
        .info {{
            border-left: 5px solid #5cb85c;
        }}
        .severity {{
            display: inline-block;
            padding: 3px 7px;
            border-radius: 3px;
            color: white;
            font-weight: bold;
        }}
        .severity.high {{
            background-color: #d9534f;
        }}
        .severity.medium {{
            background-color: #f0ad4e;
        }}
        .severity.low {{
            background-color: #5bc0de;
        }}
        .severity.info {{
            background-color: #5cb85c;
        }}
        pre {{
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <h1>Soleco Security Report</h1>
    <p>Generated on {report.get('timestamp', datetime.now().isoformat())}</p>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>High Severity Issues: {report.get('summary', {}).get('high_severity', 0)}</p>
        <p>Medium Severity Issues: {report.get('summary', {}).get('medium_severity', 0)}</p>
        <p>Low Severity Issues: {report.get('summary', {}).get('low_severity', 0)}</p>
        <p>Informational Items: {report.get('summary', {}).get('info', 0)}</p>
        <p>Total Findings: {sum(report.get('summary', {}).values())}</p>
    </div>
    
    <h2>Findings</h2>
"""
        
        # Add findings
        for finding in sorted(report.get('findings', []), 
                             key=lambda x: 0 if x.get('severity', '').lower() == 'high' else 
                                          1 if x.get('severity', '').lower() == 'medium' else 
                                          2 if x.get('severity', '').lower() == 'low' else 3):
            severity = finding.get('severity', 'info').lower()
            html += f"""
    <div class="finding {severity}">
        <h3>{finding.get('title', 'Unknown Finding')}</h3>
        <p><span class="severity {severity}">{severity.upper()}</span></p>
        <p><strong>Description:</strong> {finding.get('description', 'No description provided')}</p>
        <p><strong>Location:</strong> {finding.get('location', 'Unknown')}</p>
        <p><strong>Recommendation:</strong> {finding.get('recommendation', 'No recommendation provided')}</p>
        <p><strong>CWE:</strong> {finding.get('cwe', 'Not specified')}</p>
    </div>
"""
        
        # Close HTML
        html += """
</body>
</html>
"""
        
        # Write HTML to file
        with open(html_report_path, 'w') as f:
            f.write(html)
        
        logger.info(f"HTML report generated at {html_report_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error generating HTML report: {e}")
        return False

def main():
    """Main entry point."""
    args = parse_args()
    
    # Normalize paths
    codebase_path = os.path.abspath(os.path.expanduser(args.codebase))
    requirements_file = os.path.abspath(os.path.expanduser(args.requirements))
    output_file = args.output
    
    # Validate paths
    if not os.path.exists(codebase_path):
        logger.error(f"Codebase path does not exist: {codebase_path}")
        sys.exit(1)
    
    if not os.path.exists(requirements_file):
        logger.error(f"Requirements file does not exist: {requirements_file}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Run security audit
    audit_output = os.path.join(os.path.dirname(output_file), 'audit_results.json')
    audit_results = run_security_audit(codebase_path, audit_output)
    
    # Run Bandit scan
    bandit_output = os.path.join(os.path.dirname(output_file), 'bandit_results.json')
    run_bandit_scan(codebase_path, bandit_output)
    
    # Run safety check
    safety_output = os.path.join(os.path.dirname(output_file), 'safety_results.json')
    run_safety_check(requirements_file, safety_output)
    
    # Combine results
    combined_results = {
        'timestamp': datetime.now().isoformat(),
        'codebase_path': codebase_path,
        'requirements_file': requirements_file,
        'summary': audit_results.get('summary', {}),
        'findings': audit_results.get('findings', [])
    }
    
    # Add Bandit results if available
    if os.path.exists(bandit_output):
        try:
            with open(bandit_output, 'r') as f:
                bandit_results = json.load(f)
            
            # Convert Bandit results to our format
            for result in bandit_results.get('results', []):
                severity = result.get('issue_severity', 'low').lower()
                finding = {
                    'title': f"Bandit: {result.get('test_name', 'Unknown')}",
                    'description': result.get('issue_text', 'No description provided'),
                    'location': f"{result.get('filename', 'Unknown')}:{result.get('line_number', 0)}",
                    'severity': severity,
                    'recommendation': result.get('more_info', 'No recommendation provided'),
                    'cwe': result.get('cwe', 'Not specified')
                }
                combined_results['findings'].append(finding)
                
                # Update summary
                if severity in combined_results['summary']:
                    combined_results['summary'][severity] += 1
                else:
                    combined_results['summary'][severity] = 1
        except Exception as e:
            logger.error(f"Error processing Bandit results: {e}")
    
    # Add Safety results if available
    if os.path.exists(safety_output):
        try:
            with open(safety_output, 'r') as f:
                safety_results = json.load(f)
            
            # Convert Safety results to our format
            for vuln in safety_results.get('vulnerabilities', []):
                finding = {
                    'title': f"Vulnerable Dependency: {vuln.get('package_name', 'Unknown')}",
                    'description': vuln.get('advisory', 'No description provided'),
                    'location': requirements_file,
                    'severity': 'high',  # Safety doesn't provide severity, assume high
                    'recommendation': f"Update {vuln.get('package_name', 'Unknown')} to {vuln.get('fixed_version', 'the latest version')}",
                    'cwe': 'CWE-1104: Use of Unmaintained Third Party Components'
                }
                combined_results['findings'].append(finding)
                
                # Update summary
                if 'high_severity' in combined_results['summary']:
                    combined_results['summary']['high_severity'] += 1
                else:
                    combined_results['summary']['high_severity'] = 1
        except Exception as e:
            logger.error(f"Error processing Safety results: {e}")
    
    # Write combined results to file
    with open(output_file, 'w') as f:
        json.dump(combined_results, f, indent=2)
    
    logger.info(f"Combined security report written to {output_file}")
    
    # Generate HTML report if requested
    if args.html:
        html_output = os.path.splitext(output_file)[0] + '.html'
        generate_html_report(output_file, html_output)
    
    logger.info("""
Security report generation complete!

The report includes:
- Custom security audit findings
- Bandit static analysis results
- Safety dependency vulnerability check results

Review the report and address the findings based on their severity.
""")

if __name__ == "__main__":
    main()
