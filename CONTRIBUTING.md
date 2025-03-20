# Contributing to Soleco

## 🌟 Welcome Contributors!

First off, thank you for considering contributing to Soleco! It's people like you that make Soleco such a great tool for the Solana ecosystem.

## 📖 Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to keep our community approachable and respectful.

## 🚀 How Can I Contribute?

### 🐛 Reporting Bugs

- **Ensure the bug was not already reported** by searching existing GitHub issues.
- If you can't find an open issue addressing the problem, open a new one using the bug report template.
- Be sure to include a **title and clear description**, as much relevant information as possible, and a **code sample** or an **executable test case** demonstrating the expected behavior that is not occurring.
- Include details about your environment: OS, Python version, package versions, etc.
- Screenshots and logs are extremely helpful.

### 🌈 Feature Requests

- Open a GitHub issue with the tag "enhancement".
- Provide a clear and detailed explanation of the feature.
- Explain why this feature would be useful to most Soleco users.
- Include mockups or diagrams if applicable.
- Suggest an implementation approach if possible.

### 📝 Documentation Improvements

- Documentation is crucial for Soleco's usability.
- Suggest improvements to README, inline code documentation, or wiki pages.
- Fix typos, clarify explanations, or add missing information.
- Add examples and use cases to help users understand features.

### 🔧 Pull Requests

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

#### Pull Request Guidelines

- **Code Style**: Follow the existing code style (PEP 8 for Python, ESLint rules for JavaScript).
- **Documentation**: Update documentation for any changed functionality.
- **Tests**: Add tests for new features and ensure all tests pass.
- **Commits**: Use clear, descriptive commit messages.
- **Branch**: Create a feature branch, never commit directly to `main` or `develop`.
- **CI/CD**: Ensure all CI/CD checks pass before requesting review.
- **Review**: Address review comments promptly.
- **Scope**: Keep PRs focused on a single feature or fix.

## 🛠 Development Setup

### Prerequisites

- Python 3.9+
- Node.js 16+ (for frontend)
- pip
- npm or yarn
- Git
- (Optional) Docker

### Local Development

1. Clone the repository
```bash
git clone https://github.com/yourusername/soleco.git
cd soleco
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install backend dependencies
```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

4. Install frontend dependencies
```bash
cd ../frontend
npm install  # or yarn install
```

5. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. Run tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd ../frontend
npm test
```

7. Start development servers
```bash
# Backend
cd backend
uvicorn app.main:app --reload

# Frontend (in a separate terminal)
cd frontend
npm start
```

## 🧪 Testing Guidelines

- Write tests for all new features and bug fixes.
- Aim for high test coverage, especially for critical components.
- Include unit tests, integration tests, and end-to-end tests as appropriate.
- Mock external dependencies to ensure tests are reliable and fast.
- Use pytest for backend testing and Jest for frontend testing.

## 📊 Branching Strategy

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: New features or enhancements
- `bugfix/*`: Bug fixes
- `hotfix/*`: Urgent fixes for production
- `release/*`: Release preparation

## 🏆 Contribution Levels

### 🥉 Bronze Contributor
- Bug reports
- Documentation improvements
- Small code fixes
- First-time contributors

### 🥈 Silver Contributor
- New feature implementations
- Significant documentation updates
- Comprehensive bug fixes
- Regular contributions

### 🥇 Gold Contributor
- Major architectural improvements
- New API integrations
- Sustained, high-quality contributions
- Community leadership

## 💡 Community

- Join our [Discord](https://discord.gg/your-discord)
- Follow us on [Twitter](https://twitter.com/soleco)
- Participate in [GitHub Discussions](https://github.com/yourusername/soleco/discussions)
- Attend our monthly community calls

## 📝 License

By contributing, you agree that your contributions will be licensed under the project's license. See the [LICENSE](LICENSE) file for details.

## 🔄 Review Process

1. A maintainer will review your PR within 5 business days.
2. Feedback will be provided as GitHub comments.
3. Once approved, your PR will be merged by a maintainer.
4. Your contribution will be acknowledged in release notes.

## 🚩 Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Documentation improvements
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `question`: Further information is requested
- `wontfix`: This will not be worked on

---

**Thank you for your contribution!** 🎉
