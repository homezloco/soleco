#!/usr/bin/env python3
"""
Generate a consolidated security report from all individual reports.

This script reads all the individual security audit reports and generates
a consolidated report with statistics and findings.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime
from collections import Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('generate_consolidated_report')

def load_report(report_path):
    """Load a security audit report from a JSON file."""
    try:
        with open(report_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading report {report_path}: {e}")
        return None

def generate_html_report(consolidated_data, output_path):
    """Generate an HTML report from the consolidated data."""
    # Get the current date and time
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Count findings by severity
    severity_counts = Counter()
    for module_name, module_data in consolidated_data['modules'].items():
        for finding in module_data['findings']:
            severity_counts[finding['severity']] += 1
    
    # Count findings by module
    module_counts = {module_name: len(module_data['findings']) for module_name, module_data in consolidated_data['modules'].items()}
    
    # Generate the HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soleco Security Audit Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3, h4 {{
            color: #2c3e50;
        }}
        .header {{
            background-color: #3498db;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .summary {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }}
        .summary-box {{
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            flex: 1;
            margin: 0 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .severity-high {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .severity-medium {{
            color: #f39c12;
            font-weight: bold;
        }}
        .severity-low {{
            color: #3498db;
            font-weight: bold;
        }}
        .severity-info {{
            color: #2ecc71;
            font-weight: bold;
        }}
        .finding {{
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .finding h4 {{
            margin-top: 0;
        }}
        .module-section {{
            margin-bottom: 30px;
        }}
        .chart-container {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }}
        .chart {{
            width: 48%;
            height: 300px;
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="header">
        <h1>Soleco Security Audit Report</h1>
        <p>Generated on: {now}</p>
    </div>
    
    <h2>Executive Summary</h2>
    <div class="summary">
        <div class="summary-box">
            <h3>Total Findings</h3>
            <p style="font-size: 24px;">{consolidated_data['total_findings']}</p>
        </div>
        <div class="summary-box">
            <h3>Severity Breakdown</h3>
            <p><span class="severity-high">High: {severity_counts.get('high', 0)}</span></p>
            <p><span class="severity-medium">Medium: {severity_counts.get('medium', 0)}</span></p>
            <p><span class="severity-low">Low: {severity_counts.get('low', 0)}</span></p>
            <p><span class="severity-info">Info: {severity_counts.get('info', 0)}</span></p>
        </div>
        <div class="summary-box">
            <h3>Modules Analyzed</h3>
            <p style="font-size: 24px;">{len(consolidated_data['modules'])}</p>
        </div>
    </div>
    
    <div class="chart-container">
        <div class="chart">
            <canvas id="severityChart"></canvas>
        </div>
        <div class="chart">
            <canvas id="moduleChart"></canvas>
        </div>
    </div>
    
    <h2>Findings by Module</h2>
    
    <table>
        <tr>
            <th>Module</th>
            <th>High</th>
            <th>Medium</th>
            <th>Low</th>
            <th>Info</th>
            <th>Total</th>
        </tr>
"""
    
    # Add rows for each module
    for module_name, module_data in consolidated_data['modules'].items():
        module_severity_counts = Counter()
        for finding in module_data['findings']:
            module_severity_counts[finding['severity']] += 1
        
        html += f"""
        <tr>
            <td>{module_name}</td>
            <td>{module_severity_counts.get('high', 0)}</td>
            <td>{module_severity_counts.get('medium', 0)}</td>
            <td>{module_severity_counts.get('low', 0)}</td>
            <td>{module_severity_counts.get('info', 0)}</td>
            <td>{len(module_data['findings'])}</td>
        </tr>
"""
    
    html += """
    </table>
    
    <h2>Detailed Findings</h2>
"""
    
    # Add sections for each module
    for module_name, module_data in consolidated_data['modules'].items():
        if not module_data['findings']:
            continue
        
        html += f"""
    <div class="module-section">
        <h3>{module_name}</h3>
"""
        
        # Add findings for this module
        for finding in module_data['findings']:
            severity_class = f"severity-{finding['severity']}"
            html += f"""
        <div class="finding">
            <h4>{finding['title']} (<span class="{severity_class}">{finding['severity'].upper()}</span>)</h4>
            <p><strong>Location:</strong> {finding['location']}</p>
            <p><strong>Description:</strong> {finding['description']}</p>
            <p><strong>Recommendation:</strong> {finding['recommendation']}</p>
            <p><strong>CWE:</strong> {finding['cwe']}</p>
        </div>
"""
        
        html += """
    </div>
"""
    
    # Add JavaScript for charts
    html += f"""
    <script>
        // Severity chart
        const severityCtx = document.getElementById('severityChart').getContext('2d');
        const severityChart = new Chart(severityCtx, {{
            type: 'pie',
            data: {{
                labels: ['High', 'Medium', 'Low', 'Info'],
                datasets: [{{
                    data: [{severity_counts.get('high', 0)}, {severity_counts.get('medium', 0)}, {severity_counts.get('low', 0)}, {severity_counts.get('info', 0)}],
                    backgroundColor: ['#e74c3c', '#f39c12', '#3498db', '#2ecc71'],
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Findings by Severity',
                        font: {{
                            size: 16
                        }}
                    }}
                }}
            }}
        }});
        
        // Module chart
        const moduleCtx = document.getElementById('moduleChart').getContext('2d');
        const moduleChart = new Chart(moduleCtx, {{
            type: 'bar',
            data: {{
                labels: {list(module_counts.keys())},
                datasets: [{{
                    label: 'Findings',
                    data: {list(module_counts.values())},
                    backgroundColor: '#3498db',
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Findings by Module',
                        font: {{
                            size: 16
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            precision: 0
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    # Write the HTML to a file
    with open(output_path, 'w') as f:
        f.write(html)
    
    logger.info(f"Generated HTML report: {output_path}")

def main():
    """Main entry point."""
    start_time = time.time()
    logger.info("Generating consolidated security report")
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find all JSON report files
    report_files = list(Path(current_dir).glob('*_report.json'))
    logger.info(f"Found {len(report_files)} report files")
    
    # Load all reports
    consolidated_data = {
        'total_findings': 0,
        'modules': {}
    }
    
    for report_path in report_files:
        report_data = load_report(report_path)
        if report_data is None:
            continue
        
        module_name = report_data.get('module', os.path.basename(report_path).replace('_report.json', ''))
        findings = report_data.get('findings', [])
        
        consolidated_data['modules'][module_name] = {
            'findings': findings
        }
        consolidated_data['total_findings'] += len(findings)
    
    # Save the consolidated data to a JSON file
    output_json_path = os.path.join(current_dir, 'consolidated_security_report.json')
    with open(output_json_path, 'w') as f:
        json.dump(consolidated_data, f, indent=2)
    
    logger.info(f"Saved consolidated data to {output_json_path}")
    
    # Generate an HTML report
    output_html_path = os.path.join(current_dir, 'consolidated_security_report.html')
    generate_html_report(consolidated_data, output_html_path)
    
    logger.info(f"Generated consolidated report in {time.time() - start_time:.2f} seconds")
    logger.info(f"Total findings: {consolidated_data['total_findings']}")
    
    print(f"\nConsolidated report generated successfully:")
    print(f"- JSON: {output_json_path}")
    print(f"- HTML: {output_html_path}")
    print(f"\nTotal findings: {consolidated_data['total_findings']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
