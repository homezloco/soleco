# Soleco Security Audit Tools

A comprehensive suite of security audit tools for the Soleco project, designed to identify potential vulnerabilities and enhance the security posture of the codebase.

## Overview

The Soleco Security Audit Tools provide a systematic approach to identifying security vulnerabilities across various aspects of the codebase, including:

- API Security
- Key Management
- Dependency Security
- Input Validation
- Transaction Security
- Data Protection
- Monitoring and Incident Response
- Web Security
- Infrastructure Security

## Installation

To install the required dependencies for the security audit tools:

```bash
# Navigate to the security directory
cd security

# Install dependencies
python setup_security_tools.py
```

This will install all necessary tools and set up a pre-commit hook for basic security scanning.

## Usage

### Running a Full Security Audit

To run a comprehensive security audit on the Soleco codebase:

```bash
python security_audit.py --codebase-path ../backend --output-report security_audit_report.json --html
```

Options:
- `--codebase-path`: Path to the codebase to audit (required)
- `--output-report`: Path to the output report file (default: security_audit_report.json)
- `--html`: Generate an HTML report in addition to JSON
- `--modules`: Specific audit modules to run (default: all)
- `--verbose`, `-v`: Enable verbose logging

### Running Individual Tools

#### Bandit Static Analysis

```bash
python run_bandit_scan.py --path ../backend --output bandit_report.html
```

Options:
- `--path`: Path to the codebase to scan (default: ../backend)
- `--output`: Output file for the scan report (default: bandit_report.html)
- `--severity`: Minimum severity level to report (default: low)
- `--confidence`: Minimum confidence level to report (default: low)

#### Dependency Vulnerability Check

```bash
python check_dependencies.py --requirements ../backend/requirements.txt --output dependency_check_report.json
```

Options:
- `--requirements`: Path to requirements.txt file (default: ../backend/requirements.txt)
- `--output`: Output file for the scan report (default: dependency_check_report.json)

#### Comprehensive Security Report

```bash
python generate_security_report.py --codebase ../backend --requirements ../backend/requirements.txt --output security_report.json --html
```

Options:
- `--codebase`: Path to the codebase to scan (default: ../backend)
- `--requirements`: Path to requirements.txt file (default: ../backend/requirements.txt)
- `--output`: Output file for the security report (default: security_report.json)
- `--html`: Generate HTML report in addition to JSON

## Audit Modules

The security audit is composed of several modules, each focusing on a specific security aspect:

### API Security
Checks for issues related to API security, including rate limiting, CORS configuration, authentication, and input validation.

### Key Management
Checks for issues related to key management, including hardcoded API keys, insecure storage of secrets, and lack of key rotation mechanisms.

### Dependency Security
Checks for issues related to dependencies, including outdated packages with known vulnerabilities, insecure dependency sources, and lack of dependency pinning.

### Input Validation
Checks for issues related to input validation, including proper validation in API endpoints, user-provided data sanitization, and prevention of injection attacks.

### Transaction Security
Checks for issues related to transaction security, including transaction validation, signature verification, simulation before execution, and gas limit controls.

### Data Protection
Checks for issues related to data protection, including PII handling, data encryption, data minimization, and secure storage.

### Monitoring and Incident Response
Checks for issues related to monitoring and incident response, including logging configuration, error handling, intrusion detection, and incident response procedures.

### Web Security
Checks for issues related to web security, including CSRF protection, XSS prevention, Content Security Policy, HTTP security headers, and cookie security.

### Infrastructure Security
Checks for issues related to infrastructure security, including deployment security, container security, network security, and configuration management.

## Best Practices

1. **Regular Scanning**: Run the security audit regularly, especially before major releases.
2. **CI/CD Integration**: Integrate security scanning into your CI/CD pipeline.
3. **Address High Severity Issues**: Prioritize addressing high and medium severity issues.
4. **Keep Dependencies Updated**: Regularly update dependencies to patch known vulnerabilities.
5. **Follow Recommendations**: Implement the recommendations provided in the audit reports.

## Contributing

To add a new audit module:

1. Create a new Python file in the `audit_modules` directory
2. Implement the `run_audit(codebase_path)` function that returns a list of findings
3. Add the module name to `__all__` in `audit_modules/__init__.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
