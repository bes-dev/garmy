# 🔧 Garmy Development Guide

Complete guide for local development and testing of the Garmy library.

## 📦 Quick Start

### Initial Setup
```bash
# Clone and navigate to directory
git clone <repository-url>
cd garmy

# Install in development mode
make install-dev
```

## 🚀 Main Commands

### Help
```bash
make help  # Show all available commands
```

### Development Environment Setup
```bash
make install-dev    # Install development dependencies
```

### Code Formatting and Linting
```bash
make format         # Format code (black + isort)
make check          # Check formatting without changes
make lint           # Run all linters
make lint-ruff      # Fast linting with ruff
make lint-mypy      # Type checking with mypy
make lint-bandit    # Security scanning with bandit
```

### Testing
```bash
make test           # Run all tests with coverage
make test-core      # Core module tests
make test-auth      # Authentication tests  
make test-metrics   # Metrics tests
make test-mcp       # MCP server tests
```

### CI/CD Pipelines
```bash
make quick-check    # Quick check (format + ruff + mypy)
make ci             # Full pipeline (format + lint + tests)
```

### Build and Cleanup
```bash
make build          # Build package for distribution
make clean          # Clean temporary files and cache
```

## 💡 Recommended Workflows

### Daily Development
```bash
# 1. Quick check during development
make quick-check

# 2. Test specific module
make test-core      # or other needed module
```

### Before Commit
```bash
# Full pipeline before commit
make ci
```

### Fixing Code Issues
```bash
# 1. Automatic formatting
make format

# 2. Automatic ruff fixes
ruff check src/ tests/ examples/ --fix

# 3. Check results
make quick-check
```

## 📊 Test Coverage Analysis

After running `make test`, a coverage report is created:

- **Terminal**: Shows coverage percentage by file
- **HTML Report**: `htmlcov/index.html` (detailed view)

## 🔍 Debugging and Diagnostics

### Logging
```bash
# Enable debug mode for MCP
export GARMY_MCP_DEBUG=true

# View server logs
garmy-mcp serve --debug
```

### Environment Variables
```bash
# Credentials for testing
export GARMIN_EMAIL="your-email@example.com"
export GARMIN_PASSWORD="your-password"

# MCP configuration
export GARMY_MCP_DEBUG=true
export GARMY_MCP_CACHE_ENABLED=true
export GARMY_MCP_CACHE_SIZE=100
```

## ⚡ Quick Commands

| Purpose | Command |
|---------|---------|
| First run | `make install-dev` |
| Quick check | `make quick-check` |
| Before commit | `make ci` |
| Fix formatting | `make format` |
| Single module tests | `make test-mcp` |
| Clean all | `make clean` |

## 🏗️ Project Architecture

```
garmy/
├── src/garmy/           # Main code
│   ├── auth/           # Authentication
│   ├── core/           # Library core
│   ├── mcp/            # MCP server
│   └── metrics/        # Health metrics
├── tests/              # Tests
├── examples/           # Usage examples
└── Makefile           # Development commands
```

## 🐛 Troubleshooting

### Dependency Issues
```bash
# Reinstall dependencies
pip uninstall garmy
make install-dev
```

### Type Checking Issues
```bash
# Install types
pip install types-requests

# Check types
make lint-mypy
```

### Formatting Issues
```bash
# Force formatting
make format
make check
```

## 📝 Contributing

1. Create branch: `git checkout -b feature/new-feature`
2. Develop changes
3. Run: `make ci`
4. Create pull request

## 🔗 Useful Links

- [README.md](README.md) - Main documentation
- [CHANGELOG.md](CHANGELOG.md) - Change history
- [examples/](examples/) - Usage examples

---

💡 **Tip**: Use `make help` to view all available commands with descriptions.