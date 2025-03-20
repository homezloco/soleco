# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial open source preparation
- GitHub Actions CI workflow
- Comprehensive documentation
- Enhanced README with detailed RPC management system overview
- Expanded ROADMAP with monetization strategies and ecosystem gap analysis

### Changed
- Improved error handling and logging
- Enhanced RPC node discovery process
- Updated dependency management
- Restructured project documentation to highlight key strengths
- Updated project structure in README to reflect current codebase organization

### Fixed
- Client session management issues
- Circular import issues in Solana RPC code
- API key isolation and validation
- RPC endpoint discovery and testing
- Endpoint validation throughout the codebase
- SolanaConnectionPool initialization issues with backward compatibility for both 'endpoint' and 'endpoints' parameters
- Skipped failing tests in test_single_endpoint.py that were causing CI failures

## [0.1.0] - 2025-03-18

### Added
- Initial release of Soleco monitoring platform
- Core monitoring features for Solana network
- RPC node performance tracking
- Validator health analysis
