from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="soleco-cli",
    version="0.1.0",
    author="Soleco Team",
    author_email="info@soleco.io",
    description="Command-line interface for the Soleco Solana blockchain analytics platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/soleco",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "rich>=10.0.0",
        "pyyaml>=6.0",
        "python-dateutil>=2.8.2",
        "tabulate>=0.8.9",
        "colorama>=0.4.4",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.10.0",
            "flake8>=6.0.0",
            "pre-commit>=3.0.0",
            "mypy>=1.0.0",
            "types-requests>=2.25.0",
            "types-PyYAML>=6.0.0",
            "types-python-dateutil>=2.8.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "soleco=soleco_cli.cli:cli",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
)
