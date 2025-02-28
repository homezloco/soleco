# Contributing to Soleco CLI

Thank you for your interest in contributing to the Soleco CLI! This document provides guidelines and instructions for contributing to the project.

## Development Setup

1. Fork the repository and clone your fork:
   ```bash
   git clone https://github.com/yourusername/soleco.git
   cd soleco/cli
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Code Style

We follow the PEP 8 style guide for Python code. Some key points:

- Use 4 spaces for indentation (not tabs)
- Maximum line length of 100 characters
- Use descriptive variable names
- Add docstrings to all functions, classes, and modules

We use the following tools to enforce code style:
- Black for code formatting
- isort for import sorting
- flake8 for linting

## Testing

We use pytest for testing. To run the tests:

```bash
pytest
```

To run tests with coverage:

```bash
pytest --cov=soleco_cli
```

Please ensure that your code changes include appropriate tests. We aim for high test coverage and all tests must pass before a pull request can be merged.

## Pull Request Process

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them with descriptive commit messages:
   ```bash
   git commit -m "Add feature X" -m "This feature adds the ability to do X, which helps users accomplish Y."
   ```

3. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Open a pull request against the main repository's `main` branch.

5. Ensure your PR includes:
   - A clear description of the changes
   - Any relevant issue numbers (e.g., "Fixes #123")
   - Tests for new functionality
   - Documentation updates if needed

6. Address any feedback from code reviews.

## Adding New Commands

When adding new commands to the CLI:

1. Create a new file in the `soleco_cli/commands/` directory if it's a major feature area.

2. Follow the existing command structure using Click decorators.

3. Add appropriate help text, options, and arguments.

4. Implement proper error handling and user feedback.

5. Add tests for the new command in the `tests/` directory.

6. Update the documentation to reflect the new command.

## Documentation

All new features should include documentation:

- Docstrings for all public functions, classes, and methods
- Updates to the README.md if adding new commands or features
- Example usage in docstrings or examples directory for complex features

## Reporting Issues

If you find a bug or have a suggestion for improvement:

1. Check if the issue already exists in the issue tracker.

2. If not, create a new issue with:
   - A clear, descriptive title
   - A detailed description of the issue or suggestion
   - Steps to reproduce (for bugs)
   - Expected vs. actual behavior (for bugs)
   - Your environment (OS, Python version, etc.)

## Code of Conduct

Please be respectful and considerate of others when contributing. We aim to maintain a welcoming and inclusive community.

## License

By contributing to this project, you agree that your contributions will be licensed under the project's license.
