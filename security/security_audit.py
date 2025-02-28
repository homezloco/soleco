#!/usr/bin/env python3
"""
Soleco Security Audit Tool

This script performs a comprehensive security audit of the Soleco codebase,
focusing on identifying potential vulnerabilities and providing recommendations
for enhancing the security of the codebase.

Usage:
    python security_audit.py --codebase-path /path/to/codebase --output-report report.json

The tool runs various audit modules, each focusing on a specific security aspect,
and compiles the findings into a comprehensive report.
"""

import os
import sys
import argparse
import logging
import json
import importlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('security_audit')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Soleco Security Audit Tool')
    parser.add_argument('--codebase-path', type=str, required=True,
                        help='Path to the codebase to audit')
    parser.add_argument('--output-report', type=str, default='security_audit_report.json',
                        help='Path to the output report file')
    parser.add_argument('--html', action='store_true',
                        help='Generate HTML report in addition to JSON')
    parser.add_argument('--modules', type=str, nargs='+',
                        help='Specific audit modules to run (default: all)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--exclude-modules', type=str, nargs='+',
                        help='Audit modules to exclude from the run')
    parser.add_argument('--severity-threshold', type=str, choices=['low', 'medium', 'high'], default='low',
                        help='Minimum severity level to include in the report (default: low)')
    return parser.parse_args()

def run_security_audit(codebase_path, modules=None, exclude_modules=None, severity_threshold='low'):
    """
    Run the security audit.
    
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
    
    # Import audit modules
    audit_modules = {}
    
    try:
        # Import the audit_modules package
        from security.audit_modules import __all__ as available_modules
        
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
                module = importlib.import_module(f'security.audit_modules.{module_name}')
                audit_modules[module_name] = module
                logger.info(f"Loaded audit module: {module_name}")
            except ImportError as e:
                logger.error(f"Failed to import audit module {module_name}: {e}")
    except ImportError:
        # If we can't import from security.audit_modules, try relative import
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.dirname(current_dir))
        
        try:
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
    
    # Run the audit modules
    findings = []
    
    for module_name, module in audit_modules.items():
        logger.info(f"Running audit module: {module_name}")
        try:
            module_findings = module.run_audit(codebase_path)
            findings.extend(module_findings)
            logger.info(f"Audit module {module_name} found {len(module_findings)} issues")
        except Exception as e:
            logger.error(f"Error running audit module {module_name}: {e}")
    
    # Filter findings by severity threshold
    findings = [f for f in findings if f.get('severity', '').lower() >= severity_threshold.lower()]
    
    # Compile the results
    results = {
        'timestamp': datetime.now().isoformat(),
        'codebase_path': codebase_path,
        'findings': findings,
        'summary': {
            'high_severity': len([f for f in findings if f.get('severity', '').lower() == 'high']),
            'medium_severity': len([f for f in findings if f.get('severity', '').lower() == 'medium']),
            'low_severity': len([f for f in findings if f.get('severity', '').lower() == 'low']),
            'info': len([f for f in findings if f.get('severity', '').lower() == 'info']),
        }
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
    logger.info(f"Generating HTML report from {json_report_path}")
    
    try:
        # Load the JSON report
        with open(json_report_path, 'r') as f:
            report = json.load(f)
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Soleco Security Audit Report</title>
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
    <h1>Soleco Security Audit Report</h1>
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
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the security audit
    results = run_security_audit(args.codebase_path, args.modules, args.exclude_modules, args.severity_threshold)
    
    if results is None:
        logger.error("Security audit failed")
        sys.exit(1)
    
    # Write the report
    with open(args.output_report, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Security audit report written to {args.output_report}")
    
    # Generate HTML report if requested
    if args.html:
        html_report_path = os.path.splitext(args.output_report)[0] + '.html'
        generate_html_report(args.output_report, html_report_path)
    
    # Print summary
    print("\nSecurity Audit Summary:")
    print(f"High Severity Issues: {results['summary']['high_severity']}")
    print(f"Medium Severity Issues: {results['summary']['medium_severity']}")
    print(f"Low Severity Issues: {results['summary']['low_severity']}")
    print(f"Informational Items: {results['summary']['info']}")
    print(f"Total Findings: {sum(results['summary'].values())}")
    
    # Exit with status code based on findings
    if results['summary']['high_severity'] > 0:
        logger.warning("High severity issues found")
        sys.exit(2)
    elif results['summary']['medium_severity'] > 0:
        logger.warning("Medium severity issues found")
        sys.exit(3)
    else:
        logger.info("No high or medium severity issues found")
        sys.exit(0)

if __name__ == "__main__":
    main()
