.PHONY: help lint format check test test-mcp test-core test-auth test-metrics clean install-dev build ci

# Default target
help:
	@echo "🔧 Garmy Development Commands"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "📦 Setup:"
	@echo "  install-dev    - Install development dependencies"
	@echo "  build          - Build package for distribution"
	@echo ""
	@echo "🎨 Code Quality:"
	@echo "  format         - Format code with black and isort"
	@echo "  check          - Check formatting without modifying files"
	@echo "  lint           - Run all linters (ruff, flake8, mypy, bandit)"
	@echo "  lint-ruff      - Run ruff linter (fast)"
	@echo "  lint-mypy      - Run mypy type checker"
	@echo "  lint-bandit    - Run bandit security scanner"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test           - Run all tests with coverage"
	@echo "  test-core      - Run core module tests"
	@echo "  test-auth      - Run authentication tests"
	@echo "  test-metrics   - Run metrics tests"
	@echo "  test-mcp       - Run MCP server tests"
	@echo ""
	@echo "🚀 CI/CD:"
	@echo "  ci             - Run full CI pipeline (format, lint, test)"
	@echo "  quick-check    - Quick quality check (format check + ruff + mypy)"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  clean          - Clean build artifacts and cache"
	@echo ""
	@echo "💡 Example workflows:"
	@echo "  make install-dev  # First time setup"
	@echo "  make ci           # Full pipeline before commit"
	@echo "  make quick-check  # Fast check during development"

# Install development dependencies
install-dev:
	@echo "📦 Installing development dependencies..."
	pip install -e ".[dev]"
	@echo "✅ Development dependencies installed!"

# Build package
build:
	@echo "🏗️  Building package..."
	python -m build
	@echo "✅ Package built successfully!"

# Format code
format:
	@echo "🎨 Formatting code with black..."
	black src/ tests/ examples/
	@echo "📦 Organizing imports with isort..."
	isort src/ tests/ examples/
	@echo "✅ Code formatting complete!"

# Check formatting without modifying files
check:
	@echo "🔍 Checking code formatting..."
	black --check --diff src/ tests/ examples/
	isort --check-only --diff src/ tests/ examples/
	@echo "✅ Format check complete!"

# Run all linters
lint: lint-ruff lint-mypy lint-bandit
	@echo "🎉 All linting complete!"

# Run ruff (fast modern linter)
lint-ruff:
	@echo "⚡ Running ruff..."
	ruff check src/ tests/ examples/

# Run mypy type checker
lint-mypy:
	@echo "🔍 Running mypy type checker..."
	mypy src/garmy/

# Run bandit security scanner
lint-bandit:
	@echo "🛡️ Running bandit security scanner..."
	bandit -r src/garmy/ --skip B101,B601 --quiet || true

# Run all tests with coverage
test:
	@echo "🧪 Running all tests with coverage..."
	pytest tests/ --cov=src/garmy --cov-report=term-missing --cov-report=html
	@echo "✅ Tests complete!"

# Run core module tests
test-core:
	@echo "🧪 Running core module tests..."
	pytest tests/test_core_*.py -v
	@echo "✅ Core tests complete!"

# Run authentication tests
test-auth:
	@echo "🧪 Running authentication tests..."
	pytest tests/test_auth_*.py -v
	@echo "✅ Auth tests complete!"

# Run metrics tests  
test-metrics:
	@echo "🧪 Running metrics tests..."
	pytest tests/test_metrics_*.py -v
	@echo "✅ Metrics tests complete!"

# Run MCP server tests
test-mcp:
	@echo "🧪 Running MCP server tests..."
	pytest tests/test_mcp_*.py -v
	@echo "✅ MCP tests complete!"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf bandit-report.json
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	@echo "✅ Clean complete!"

# Quick quality check
quick-check: check lint-ruff lint-mypy
	@echo "⚡ Quick quality check complete!"

# Full CI pipeline
ci: clean format lint test
	@echo "🚀 Full CI pipeline complete!"