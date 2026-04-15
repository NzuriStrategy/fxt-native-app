# Test suite for the FXT Lead Intelligence Pipeline.
#
# Structure (to be populated as logic is implemented):
#
#   tests/
#   ├── unit/
#   │   ├── test_signals.py     — signal detector unit tests (synthetic ParsedDocument inputs)
#   │   ├── test_scoring.py     — scorer unit tests (deterministic, no I/O)
#   │   └── test_config.py      — settings validation tests
#   ├── integration/
#   │   ├── test_storage.py     — repository tests against a test Postgres instance
#   │   └── test_pipeline.py    — end-to-end smoke test with mocked external calls
#   └── fixtures/
#       └── factory.py          — test data builders (Company, Page, Signal, etc.)
#
# Run with:
#   poetry run pytest
#   poetry run pytest --cov --cov-report=term-missing
