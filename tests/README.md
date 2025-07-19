# Orchestra Testing Suite

This directory contains comprehensive unit tests for the Orchestra project.

## Test Structure

```
tests/
├── __init__.py                   # Test package initialization
├── conftest.py                   # Pytest configuration and shared fixtures
├── test_orchestra.py             # Main Orchestra class tests
├── test_mode_executors.py        # Mode executor tests
├── test_usage_tracker.py         # Usage tracking tests
├── test_github_integration.py    # GitHub integration tests
├── utils/
│   ├── __init__.py
│   └── test_time_utils.py        # Time utilities tests
└── fixtures/
    ├── sample_repos.yaml         # Test repository configuration
    └── sample_settings.yaml      # Test settings configuration
```

## Running Tests

### Prerequisites

1. **Activate Virtual Environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **Install Test Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Test Commands

**Run All Tests:**
```bash
python -m pytest
```

**Run Tests with Coverage:**
```bash
python -m pytest --cov=.
```

**Run Tests with Detailed Output:**
```bash
python -m pytest -v
```

**Run Specific Test File:**
```bash
python -m pytest tests/test_orchestra.py
python -m pytest tests/test_usage_tracker.py
python -m pytest tests/utils/test_time_utils.py
```

**Run Specific Test Class:**
```bash
python -m pytest tests/test_orchestra.py::TestOrchestra
python -m pytest tests/test_mode_executors.py::TestWorkdayExecutor
```

**Run Specific Test Function:**
```bash
python -m pytest tests/test_time_utils.py::TestGetWorkMode::test_workday_monday_morning
```

**Run Tests with Coverage Report:**
```bash
python -m pytest --cov=. --cov-report=html
open htmlcov/index.html  # View coverage report
```

## Test Coverage

The test suite covers:

### Core Functionality (100% coverage target)
- **Orchestra Main Class** (`test_orchestra.py`)
  - Configuration loading (repos.yaml, settings.yaml)
  - Cycle execution logic
  - Claude Code integration
  - Error handling and fallbacks
  - Daemon mode operation

- **Mode Executors** (`test_mode_executors.py`)
  - WorkdayExecutor (conservative planning mode)
  - WorknightExecutor (active development mode) 
  - WeekendExecutor (monitoring mode)
  - Usage limit checking
  - Repository processing logic

- **Usage Tracker** (`test_usage_tracker.py`)
  - JSONL file parsing
  - Token counting and aggregation
  - Usage limit calculations
  - Error handling for malformed data

- **Time Utils** (`test_time_utils.py`)
  - Work mode detection (workday/worknight/weekend/off)
  - Time boundary calculations
  - Work hours validation
  - Automation scheduling logic

### External Integrations
- **GitHub Integration** (`test_github_integration.py`)
  - GitHub CLI command execution
  - PR and issue data parsing
  - Error handling for API failures
  - Data structure validation

## Test Patterns

### Mocking External Dependencies
Tests extensively mock external dependencies to ensure:
- **Fast execution** (no real API calls)
- **Reliable results** (no network dependencies)
- **Isolated testing** (each test is independent)

Key mocked components:
- `claude_code_sdk` - Claude Code API calls
- `subprocess.run` - GitHub CLI commands
- `datetime.now()` - Time-dependent logic
- File system operations

### Fixtures and Test Data
- **Shared fixtures** in `conftest.py` provide reusable test data
- **Sample configurations** in `fixtures/` directory
- **Temporary directories** for file-based tests
- **Mock objects** for complex external dependencies

### Test Categories

**Unit Tests:**
- Test individual functions and methods in isolation
- Mock all external dependencies
- Focus on specific behavior and edge cases

**Integration Tests:**
- Test interaction between components
- Verify data flow between modules
- Validate configuration loading and parsing

**Error Handling Tests:**
- Test exception scenarios
- Verify graceful degradation
- Ensure proper error logging

## Continuous Integration

Tests are designed to run in CI/CD environments:
- No external dependencies required
- Deterministic results
- Fast execution (< 30 seconds for full suite)
- Clear error reporting

## Test Development Guidelines

When adding new tests:

1. **Follow naming conventions:**
   - Test files: `test_<module_name>.py`
   - Test classes: `Test<ClassName>`
   - Test methods: `test_<behavior_description>`

2. **Use appropriate fixtures:**
   - Leverage existing fixtures in `conftest.py`
   - Create new fixtures for reusable test data

3. **Mock external dependencies:**
   - Always mock Claude Code API calls
   - Mock file system operations when possible
   - Mock time-dependent logic for deterministic tests

4. **Test edge cases:**
   - Empty inputs
   - Malformed data
   - Network failures
   - Configuration errors

5. **Verify error handling:**
   - Test exception scenarios
   - Check error messages
   - Ensure graceful degradation

## Debugging Tests

**Run tests with debugging output:**
```bash
python -m pytest -s -v
```

**Run a single test with pdb:**
```bash
python -m pytest -s --pdb tests/test_orchestra.py::TestOrchestra::test_init
```

**Show print statements:**
```bash
python -m pytest -s
```

## Performance

The test suite is optimized for speed:
- Uses mocking to avoid I/O operations
- Temporary directories cleaned up automatically
- Parallel execution possible with pytest-xdist
- Typical full suite runtime: 10-30 seconds

Run performance profiling:
```bash
python -m pytest --durations=10
```