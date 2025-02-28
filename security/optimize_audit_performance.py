#!/usr/bin/env python3
"""
Optimize the performance of security audits by analyzing the codebase structure
and creating a configuration file that specifies which directories to include/exclude.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('optimize_audit_performance')

def analyze_codebase_structure(codebase_path):
    """Analyze the structure of the codebase to identify key directories."""
    logger.info(f"Analyzing codebase structure in {codebase_path}")
    start_time = time.time()
    
    # Get all Python files
    python_files = list(Path(codebase_path).rglob('*.py'))
    logger.info(f"Found {len(python_files)} Python files")
    
    # Analyze directory structure
    dir_stats = defaultdict(lambda: {'file_count': 0, 'size': 0})
    
    for file_path in python_files:
        # Get the relative path from the codebase root
        rel_path = file_path.relative_to(codebase_path)
        dir_path = str(rel_path.parent)
        
        # Skip venv directories
        if 'venv' in dir_path or 'env' in dir_path:
            continue
            
        # Count files and size per directory
        dir_stats[dir_path]['file_count'] += 1
        dir_stats[dir_path]['size'] += file_path.stat().st_size
    
    # Sort directories by file count
    sorted_dirs = sorted(dir_stats.items(), key=lambda x: x[1]['file_count'], reverse=True)
    
    # Identify key directories (those with the most files)
    key_dirs = []
    total_files = sum(stats['file_count'] for _, stats in dir_stats.items())
    cumulative_files = 0
    coverage_threshold = 0.80  # Target 80% coverage
    
    for dir_path, stats in sorted_dirs:
        key_dirs.append({
            'path': dir_path,
            'file_count': stats['file_count'],
            'size_kb': stats['size'] / 1024,
            'percentage': stats['file_count'] / total_files * 100
        })
        
        cumulative_files += stats['file_count']
        if cumulative_files / total_files >= coverage_threshold:
            break
    
    # Identify directories to exclude (test directories, examples, etc.)
    exclude_patterns = [
        'tests',
        'test',
        'examples',
        'docs',
        'venv',
        'env',
        '__pycache__'
    ]
    
    exclude_dirs = []
    for dir_path in dir_stats.keys():
        for pattern in exclude_patterns:
            if pattern in dir_path:
                exclude_dirs.append(dir_path)
                break
    
    # Create configuration
    config = {
        'include_dirs': [d['path'] for d in key_dirs if d['path'] not in exclude_dirs],
        'exclude_dirs': exclude_dirs,
        'statistics': {
            'total_python_files': len(python_files),
            'covered_files': cumulative_files,
            'coverage_percentage': cumulative_files / total_files * 100,
            'key_directories': key_dirs
        }
    }
    
    logger.info(f"Analysis completed in {time.time() - start_time:.2f} seconds")
    return config

def create_audit_config(codebase_path, output_file):
    """Create an audit configuration file based on codebase analysis."""
    config = analyze_codebase_structure(codebase_path)
    
    # Add additional configuration for audit modules
    config['audit_modules'] = {
        'transaction_validation': {
            'timeout': 60,
            'include_dirs': config['include_dirs'],
            'exclude_dirs': config['exclude_dirs']
        },
        'solana_security': {
            'timeout': 60,
            'include_dirs': config['include_dirs'],
            'exclude_dirs': config['exclude_dirs']
        },
        'rpc_error_handling': {
            'timeout': 60,
            'include_dirs': config['include_dirs'],
            'exclude_dirs': config['exclude_dirs']
        }
    }
    
    # Write configuration to file
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Audit configuration saved to {output_file}")
    
    # Print summary
    print("\nAudit Optimization Summary:")
    print(f"Total Python files: {config['statistics']['total_python_files']}")
    print(f"Files covered by optimized audit: {config['statistics']['covered_files']} ({config['statistics']['coverage_percentage']:.2f}%)")
    print("\nKey directories to include:")
    for dir_path in config['include_dirs']:
        print(f"  - {dir_path}")
    print("\nDirectories to exclude:")
    for dir_path in config['exclude_dirs']:
        print(f"  - {dir_path}")
    
    return config

def main():
    """Main entry point."""
    # Get the path to the backend directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(current_dir, '..', 'backend'))
    
    # Ensure the backend directory exists
    if not os.path.exists(backend_dir):
        logger.error(f"Backend directory does not exist: {backend_dir}")
        return 1
    
    # Create audit configuration
    output_file = os.path.join(current_dir, 'audit_config.json')
    create_audit_config(backend_dir, output_file)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
