#!/usr/bin/env python3
"""
Comprehensive Security Audit Runner

This script runs all security audit modules on the Soleco codebase
and generates a comprehensive report.
"""

import os
import sys
import json
import logging
import argparse
import importlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('comprehensive_audit')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Comprehensive Security Audit Runner')
    parser.add_argument('--codebase-path', type=str, 
                        default=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')),
                        help='Path to the codebase to audit (default: ../backend)')
    parser.add_argument('--output-report', type=str, default='comprehensive_security_audit_report.json',
                        help='Path to the output report file (default: comprehensive_security_audit_report.json)')
    parser.add_argument('--html', action='store_true',
                        help='Generate HTML report in addition to JSON')
    parser.add_argument('--modules', type=str, nargs='+',
                        help='Specific audit modules to run (default: all)')
    parser.add_argument('--exclude-modules', type=str, nargs='+',
                        help='Audit modules to exclude from the run')
    parser.add_argument('--severity-threshold', type=str, choices=['low', 'medium', 'high'], default='low',
                        help='Minimum severity level to include in the report (default: low)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    return parser.parse_args()

def run_comprehensive_audit(codebase_path, modules=None, exclude_modules=None, severity_threshold='low'):
    """
    Run a comprehensive security audit.
    
    Args:
        codebase_path: Path to the codebase to audit
        modules: List of specific modules to run (default: all)
        exclude_modules: List of modules to exclude from the run
        severity_threshold: Minimum severity level to include in the report
        
    Returns:
        dict: Audit results
    """
    # Normalize path
    codebase_path = os.path.abspath(os.path.expanduser(codebase_path))
    
    # Validate path
    if not os.path.exists(codebase_path):
        logger.error(f"Codebase path does not exist: {codebase_path}")
        return None
    
    # Add the current directory to the Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    # Import audit modules
    audit_modules = {}
    
    try:
        # Import the audit_modules package
        from audit_modules import __all__ as available_modules
        
        # Filter modules if specified
        if modules:
            module_list = [m for m in modules if m in available_modules]
            if not module_list:
                logger.error(f"No valid modules specified. Available modules: {', '.join(available_modules)}")
                return None
        else:
            module_list = available_modules
        
        # Exclude modules if specified
        if exclude_modules:
            module_list = [m for m in module_list if m not in exclude_modules]
            if not module_list:
                logger.error(f"All modules were excluded. No modules to run.")
                return None
        
        # Import each module
        for module_name in module_list:
            try:
                module = importlib.import_module(f'audit_modules.{module_name}')
                audit_modules[module_name] = module
                logger.info(f"Loaded audit module: {module_name}")
            except ImportError as e:
                logger.error(f"Failed to import audit module {module_name}: {e}")
    except ImportError as e:
        logger.error(f"Failed to import audit_modules package: {e}")
        return None
    
    # Run each audit module
    all_findings = []
    module_findings = {}
    
    for module_name, module in audit_modules.items():
        logger.info(f"Running audit module: {module_name}")
        try:
            findings = module.run_audit(codebase_path)
            module_findings[module_name] = findings
            all_findings.extend(findings)
            logger.info(f"Completed audit module: {module_name} (found {len(findings)} issues)")
        except Exception as e:
            logger.error(f"Error running audit module {module_name}: {e}")
    
    # Filter findings by severity threshold
    severity_levels = {'low': 0, 'medium': 1, 'high': 2}
    threshold_level = severity_levels.get(severity_threshold.lower(), 0)
    
    filtered_findings = []
    for finding in all_findings:
        finding_severity = finding.get('severity', '').lower()
        finding_level = severity_levels.get(finding_severity, 0)
        if finding_level >= threshold_level:
            filtered_findings.append(finding)
    
    # Compile the results
    results = {
        'timestamp': datetime.now().isoformat(),
        'codebase_path': codebase_path,
        'modules_run': list(audit_modules.keys()),
        'severity_threshold': severity_threshold,
        'total_findings': len(filtered_findings),
        'findings_by_severity': {
            'high': len([f for f in filtered_findings if f.get('severity') == 'high']),
            'medium': len([f for f in filtered_findings if f.get('severity') == 'medium']),
            'low': len([f for f in filtered_findings if f.get('severity') == 'low']),
        },
        'findings_by_module': {module: len(findings) for module, findings in module_findings.items()},
        'findings': filtered_findings,
    }
    
    return results

def generate_html_report(json_report_path, html_report_path):
    """
    Generate an HTML report from the JSON report.
    
    Args:
        json_report_path: Path to the JSON report
        html_report_path: Path to the HTML report to generate
        
    Returns:
        bool: True if the report was generated successfully, False otherwise
    """
    try:
        with open(json_report_path, 'r') as f:
            report = json.load(f)
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Soleco Security Audit Report</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }}
                h1, h2, h3 {{
                    color: #2c3e50;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                .summary {{
                    background-color: #f8f9fa;
                    border-radius: 5px;
                    padding: 20px;
                    margin-bottom: 20px;
                }}
                .severity-high {{
                    color: #e74c3c;
                }}
                .severity-medium {{
                    color: #f39c12;
                }}
                .severity-low {{
                    color: #3498db;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }}
                th, td {{
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .finding {{
                    background-color: #fff;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 15px;
                    margin-bottom: 15px;
                }}
                .finding-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }}
                .finding-title {{
                    margin: 0;
                    font-size: 18px;
                }}
                .finding-severity {{
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }}
                .severity-high-bg {{
                    background-color: #ffebee;
                }}
                .severity-medium-bg {{
                    background-color: #fff8e1;
                }}
                .severity-low-bg {{
                    background-color: #e3f2fd;
                }}
                .collapsible {{
                    cursor: pointer;
                }}
                .content {{
                    display: none;
                    padding: 10px;
                }}
                .active {{
                    display: block;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Soleco Security Audit Report</h1>
                
                <div class="summary">
                    <h2>Summary</h2>
                    <p><strong>Timestamp:</strong> {report['timestamp']}</p>
                    <p><strong>Codebase Path:</strong> {report['codebase_path']}</p>
                    <p><strong>Modules Run:</strong> {', '.join(report['modules_run'])}</p>
                    <p><strong>Severity Threshold:</strong> {report['severity_threshold']}</p>
                    <p><strong>Total Findings:</strong> {report['total_findings']}</p>
                    
                    <h3>Findings by Severity</h3>
                    <table>
                        <tr>
                            <th>Severity</th>
                            <th>Count</th>
                        </tr>
                        <tr>
                            <td class="severity-high">High</td>
                            <td>{report['findings_by_severity']['high']}</td>
                        </tr>
                        <tr>
                            <td class="severity-medium">Medium</td>
                            <td>{report['findings_by_severity']['medium']}</td>
                        </tr>
                        <tr>
                            <td class="severity-low">Low</td>
                            <td>{report['findings_by_severity']['low']}</td>
                        </tr>
                    </table>
                    
                    <h3>Findings by Module</h3>
                    <table>
                        <tr>
                            <th>Module</th>
                            <th>Count</th>
                        </tr>
        """
        
        for module, count in report['findings_by_module'].items():
            html += f"""
                        <tr>
                            <td>{module}</td>
                            <td>{count}</td>
                        </tr>
            """
        
        html += f"""
                    </table>
                </div>
                
                <h2>Findings</h2>
        """
        
        # Group findings by severity
        severity_order = ['high', 'medium', 'low']
        for severity in severity_order:
            severity_findings = [f for f in report['findings'] if f.get('severity') == severity]
            if severity_findings:
                html += f"""
                <h3 class="severity-{severity}">Severity: {severity.capitalize()} ({len(severity_findings)})</h3>
                """
                
                for i, finding in enumerate(severity_findings, 1):
                    html += f"""
                <div class="finding severity-{severity}-bg">
                    <div class="finding-header">
                        <h4 class="finding-title collapsible" onclick="toggleContent('finding-{severity}-{i}')">{finding['title']}</h4>
                        <span class="finding-severity severity-{severity}">{severity.upper()}</span>
                    </div>
                    <div id="finding-{severity}-{i}" class="content">
                        <p><strong>Location:</strong> {finding.get('location', 'N/A')}</p>
                        <p><strong>Description:</strong> {finding.get('description', 'N/A')}</p>
                        <p><strong>Recommendation:</strong> {finding.get('recommendation', 'N/A')}</p>
                        <p><strong>CWE:</strong> {finding.get('cwe', 'N/A')}</p>
                    </div>
                </div>
                    """
        
        html += """
            </div>
            
            <script>
                function toggleContent(id) {
                    var content = document.getElementById(id);
                    content.classList.toggle("active");
                }
                
                // Expand all high severity findings by default
                document.addEventListener("DOMContentLoaded", function() {
                    var highFindings = document.querySelectorAll('[id^="finding-high-"]');
                    highFindings.forEach(function(finding) {
                        finding.classList.add("active");
                    });
                });
            </script>
        </body>
        </html>
        """
        
        with open(html_report_path, 'w') as f:
            f.write(html)
        
        logger.info(f"Generated HTML report: {html_report_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to generate HTML report: {e}")
        return False

def display_summary(results):
    """
    Display a summary of the audit results.
    
    Args:
        results: Audit results
    """
    console = Console()
    
    # Create a summary panel
    summary_text = Text()
    summary_text.append("Soleco Security Audit Summary\n\n", style="bold")
    summary_text.append(f"Timestamp: {results['timestamp']}\n")
    summary_text.append(f"Codebase Path: {results['codebase_path']}\n")
    summary_text.append(f"Modules Run: {', '.join(results['modules_run'])}\n")
    summary_text.append(f"Severity Threshold: {results['severity_threshold']}\n")
    summary_text.append(f"Total Findings: {results['total_findings']}\n\n")
    
    console.print(Panel(summary_text, title="Summary", expand=False))
    
    # Create a severity table
    severity_table = Table(title="Findings by Severity")
    severity_table.add_column("Severity", style="bold")
    severity_table.add_column("Count")
    
    severity_table.add_row("High", str(results['findings_by_severity']['high']), style="red")
    severity_table.add_row("Medium", str(results['findings_by_severity']['medium']), style="yellow")
    severity_table.add_row("Low", str(results['findings_by_severity']['low']), style="blue")
    
    console.print(severity_table)
    
    # Create a module table
    module_table = Table(title="Findings by Module")
    module_table.add_column("Module", style="bold")
    module_table.add_column("Count")
    
    for module, count in results['findings_by_module'].items():
        module_table.add_row(module, str(count))
    
    console.print(module_table)
    
    # Display high severity findings
    high_findings = [f for f in results['findings'] if f.get('severity') == 'high']
    if high_findings:
        console.print("\n[bold red]High Severity Findings:[/bold red]")
        for i, finding in enumerate(high_findings, 1):
            console.print(f"[bold]{i}. {finding['title']}[/bold]")
            console.print(f"   Location: {finding.get('location', 'N/A')}")
            console.print(f"   Description: {finding.get('description', 'N/A')}")
            console.print(f"   Recommendation: {finding.get('recommendation', 'N/A')}")
            console.print(f"   CWE: {finding.get('cwe', 'N/A')}")
            console.print("")

def main():
    """Main entry point."""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the comprehensive audit
    results = run_comprehensive_audit(
        args.codebase_path, 
        args.modules, 
        args.exclude_modules, 
        args.severity_threshold
    )
    
    if results is None:
        logger.error("Comprehensive audit failed")
        return 1
    
    # Save the results to a JSON file
    with open(args.output_report, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Saved audit results to {args.output_report}")
    
    # Generate HTML report if requested
    if args.html:
        html_report_path = os.path.splitext(args.output_report)[0] + '.html'
        if generate_html_report(args.output_report, html_report_path):
            logger.info(f"Generated HTML report: {html_report_path}")
        else:
            logger.error("Failed to generate HTML report")
    
    # Display summary
    display_summary(results)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
