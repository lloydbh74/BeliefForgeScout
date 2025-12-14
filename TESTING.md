# Testing Guide

Quick reference for running tests on the Social Reply Bot.

## Setup

### Install Test Dependencies

```bash
# Install test requirements
pip install -r requirements-test.txt

# Or install everything
pip install -r requirements.txt -r requirements-test.txt
```

### Environment Setup

Tests use mocked APIs by default and don't require real API keys. However, if you want to run integration tests with real APIs:

```bash
# Copy environment template
cp .env.example .env.test

# Edit .env.test with test API keys (optional)
# Most tests will use mocks and don't need this
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Critical tests (voice validation, budget enforcement)
pytest -m critical

# Run a specific test file
pytest tests/unit/test_voice_validator.py

# Run a specific test class
pytest tests/unit/test_voice_validator.py::TestVoiceValidatorExclamationMarks

# Run a specific test
pytest tests/unit/test_voice_validator.py::TestVoiceValidatorExclamationMarks::test_single_exclamation_mark
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term

# View HTML report
# Open htmlcov/index.html in browser
```

### Run with Verbose Output

```bash
# Show detailed output
pytest -v

# Show even more detail (test output, print statements)
pytest -vv -s
```

### Parallel Execution (Faster)

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Run on 4 cores
pytest -n 4
```

## Test Organization

```
tests/
├── unit/                      # Unit tests (fast, isolated)
│   ├── test_voice_validator.py    # Voice validation (CRITICAL)
│   ├── test_openrouter_client.py  # OpenRouter API client
│   ├── test_reply_generator.py    # Reply generation
│   └── test_telegram_bot.py       # Telegram bot
├── integration/               # Integration tests (slower)
│   ├── test_reply_pipeline.py     # End-to-end pipeline
│   └── test_database_ops.py       # Database operations
├── fixtures/                  # Shared test fixtures
├── data/                     # Test data files
└── conftest.py               # Pytest configuration
```

## Test Markers

Tests are marked with categories for selective execution:

```bash
# Critical tests (voice validation, budget)
pytest -m critical

# Integration tests
pytest -m integration

# Slow tests
pytest -m slow

# Tests requiring real API access
pytest -m requires_api
```

## Current Test Status

### Implemented

- Voice Validator Unit Tests (100+ test cases)
  - Character limit validation
  - Exclamation mark detection
  - British English spelling
  - Corporate jargon detection
  - Salesy language detection
  - Emoji and hashtag counting
  - Scoring algorithm
  - Improvement suggestions
  - Parametrized test coverage

### TODO

- OpenRouter Client Unit Tests
- Reply Generator Unit Tests
- Telegram Bot Unit Tests
- Database Integration Tests
- Pipeline Integration Tests

## Example Test Run

```bash
$ pytest tests/unit/test_voice_validator.py -v

================================ test session starts ================================
collected 45 items

tests/unit/test_voice_validator.py::TestVoiceValidatorCharacterLimits::test_reply_under_preferred_max PASSED
tests/unit/test_voice_validator.py::TestVoiceValidatorCharacterLimits::test_reply_between_preferred_and_absolute PASSED
tests/unit/test_voice_validator.py::TestVoiceValidatorExclamationMarks::test_no_exclamation_marks PASSED
tests/unit/test_voice_validator.py::TestVoiceValidatorExclamationMarks::test_single_exclamation_mark PASSED
...

================================ 45 passed in 2.34s =================================
```

## Debugging Failed Tests

### Show Print Statements

```bash
pytest -s
```

### Show Local Variables on Failure

```bash
pytest -l
```

### Drop into Debugger on Failure

```bash
pytest --pdb
```

### Run Only Failed Tests from Last Run

```bash
# First run
pytest

# Rerun only failed tests
pytest --lf

# Rerun failed tests first, then others
pytest --ff
```

## Writing New Tests

### File Naming

- Unit tests: `test_<module_name>.py`
- Integration tests: `test_<feature>_integration.py`
- Test classes: `Test<ClassName><Feature>`
- Test functions: `test_<what>_<when>_<expected>`

### Example Test Structure

```python
import pytest
from src.module import Component

class TestComponentFeature:
    """Test specific feature of Component"""

    def test_feature_success_case(self):
        """Test feature works in success case"""
        component = Component()
        result = component.do_something()
        assert result is True

    def test_feature_handles_error(self):
        """Test feature handles errors gracefully"""
        component = Component()
        with pytest.raises(ValueError):
            component.do_something(invalid_input)
```

### Using Fixtures

```python
def test_with_fixture(sample_tweet_imposter_syndrome):
    """Test using predefined fixture"""
    tweet = sample_tweet_imposter_syndrome
    assert tweet['commercial_signals']['priority'] == 'critical'
```

### Mocking External Dependencies

```python
from unittest.mock import MagicMock, patch

def test_with_mock():
    """Test with mocked dependency"""
    with patch('src.module.ExternalAPI') as mock_api:
        mock_api.return_value.fetch.return_value = "mocked response"

        component = Component()
        result = component.use_api()

        assert result == "mocked response"
        mock_api.return_value.fetch.assert_called_once()
```

## Continuous Integration

Tests should be run automatically on every commit. Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run tests
        run: pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### Import Errors

Make sure you're running pytest from the project root:

```bash
cd "c:\Users\lloyd\Documents\Social Reply"
pytest
```

### Database Errors

Tests use in-memory SQLite by default. If you see database errors, check that SQLAlchemy is installed:

```bash
pip install sqlalchemy
```

### Async Test Errors

Make sure pytest-asyncio is installed:

```bash
pip install pytest-asyncio
```

### Mock Errors

If mocks aren't working, check that pytest-mock and httpx-mock are installed:

```bash
pip install pytest-mock httpx-mock
```

## Test Coverage Goals

- Voice Validator: 95%+ (CRITICAL)
- OpenRouter Client: 85%+
- Reply Generator: 80%+
- Telegram Bot: 75%+
- Integration: Critical paths covered

## Best Practices

1. Run tests before committing code
2. Write tests for new features
3. Update tests when changing code
4. Keep tests fast (use mocks)
5. Make tests independent (no shared state)
6. Use descriptive test names
7. One assertion per test when possible
8. Test both success and failure cases

## Getting Help

- Review TEST_STRATEGY.md for comprehensive testing strategy
- Check conftest.py for available fixtures
- Look at existing tests for examples
- Run `pytest --fixtures` to see all available fixtures
- Run `pytest --markers` to see all available markers
