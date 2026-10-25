.PHONY: build install lint test package clean

install:
	uv sync

build: install
	uv build

lint: install
	uv run ruff check --force-exclude src/ tests/
	uv run ruff format --check src/ tests/
	uv run mypy src/
	uv run vulture

test: install
	uv run pytest --cov=earnest --cov-report=term-missing --cov-report=xml:coverage.xml

package: build

clean:
	rm -rf dist .mypy_cache .pytest_cache .ruff_cache coverage.xml
