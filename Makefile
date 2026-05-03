.PHONY: dev dev-stop check format clean tail-log help

# Default target
help:
	@echo "Available targets:"
	@echo "  dev       - Start development server (auto-restarts on changes)"
	@echo "  dev-stop  - Stop background development server"
	@echo "  check     - Run ruff linting"
	@echo "  format    - Format Python code with ruff"
	@echo "  clean     - Clean __pycache__ directories"
	@echo "  tail-log  - Show the last 100 lines of the log"

# Development mode - start server with auto-reload via shoreman
dev:
	@./scripts/shoreman.sh

# Stop background development server
dev-stop:
	@if [ -f .shoreman.pid ]; then \
		kill -- -$$(cat .shoreman.pid) 2>/dev/null && echo "Stopped." || echo "Process already gone."; \
		rm -f .shoreman.pid; \
	else \
		echo "No .shoreman.pid found — server not running."; \
	fi

# Linting
check:
	@echo "Running ruff..."
	@uv run ruff check .

# Format code
format:
	@echo "Formatting Python code..."
	@uv run ruff format .
	@uv run ruff check --fix .

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Display the last 100 lines of development log with ANSI codes stripped
tail-log:
	@tail -100 ./dev.log | perl -pe 's/\e\[[0-9;]*m(?:\e\[K)?//g'
