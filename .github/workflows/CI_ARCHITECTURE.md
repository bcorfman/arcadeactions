# CI Architecture for Optional Dependencies

## Overview

The CI workflow has been split into two jobs to ensure proper testing of both core functionality and optional integrations:

## Job 1: `test` (Main Test Suite)

**Purpose**: Verify that the core ArcadeActions package works without any optional dependencies.

**Configuration**:
- Runs on: All platforms (ubuntu, windows, macos)
- Python versions: 3.11, 3.12, 3.13, 3.14
- Installation: `uv sync --dev` (bare package, NO extras)
- Tests: `pytest tests/ --ignore=tests/integration`

**Why this matters**:
- Ensures the core library doesn't accidentally depend on optional packages
- Tests across all supported platforms and Python versions
- Provides confidence that users installing `pip install arcadeactions` get a working package

**Test count**: 571 core tests

## Job 2: `test-integration` (Integration Tests)

**Purpose**: Verify compatibility with optional dependencies like python-statemachine.

**Configuration**:
- Runs on: ubuntu-latest only
- Python version: 3.12 only
- Installation: `uv sync --extra statemachine --dev`
- Tests:
  1. `pytest tests/integration/` - Run integration tests specifically
  2. `pytest tests/` - Run full suite to catch any regressions

**Why this matters**:
- Guarantees python-statemachine compatibility is always tested
- Catches integration issues early in the development cycle
- Provides confidence that optional features work as expected

**Test count**: 
- 3 integration tests (statemachine compatibility)
- 574 total tests (including core + integration)

## Test Coverage Strategy

Coverage is collected in the main `test` job (Linux Python 3.11) and excludes integration tests, focusing on core library coverage. This is appropriate because:

1. Integration tests are lightweight smoke tests
2. They test external library compatibility, not new code paths
3. Core coverage metrics remain focused on actual library code

## Adding New Optional Dependencies

When adding new optional dependencies:

1. Add to `pyproject.toml` under `[project.optional-dependencies]`
2. Create integration tests in `tests/integration/`
3. Use `pytest.importorskip("package_name")` at module level
4. Update `test-integration` job to install the extra if needed
5. Main `test` job automatically excludes integration tests

## Local Testing

Simulate CI behavior locally:

```bash
# Simulate main test job (bare package)
uv sync --dev
uv run pytest tests/ --ignore=tests/integration

# Simulate integration test job (with extras)
uv sync --extra statemachine --dev
uv run pytest tests/integration/
uv run pytest tests/
```

