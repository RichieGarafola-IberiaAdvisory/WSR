
# Test Suite Documentation: Logic and Significance

## Overview
This test suite validates the core components of the WSR (Weekly Status Reports) application. It ensures:

-    **Database integrity**
-    **Helper utility reliability**
-    **Form submission correctness**
-    **Page load stability**
-    **Query functionality**

The tests are structured using pytest and integrated with GitHub Actions for continuous integration (CI). This ensures every code change is automatically tested before deployment, minimizing risk and maintaining system stability.
---

## `tests/test_db.py`

### Purpose
Verifies the database connection, schema reflection, and CRUD utility methods in `utils/db.py`.

### Tests

#### `test_get_engine_returns_engine`
- **Logic:** Calls `get_engine()` and asserts that a SQLAlchemy engine object is returned.
- **Significance:** Ensures the application can successfully initiate a database connection—fundamental for all downstream operations.

#### `test_get_metadata_returns_metadata`
- **Logic:** Calls `get_metadata()` and checks for the presence of `tables` attribute in the returned metadata object.
- **Significance:** Confirms that the database schema is accessible and properly reflected, enabling dynamic table access and preventing runtime schema issues.

#### `test_get_table_known`
- **Logic:** Fetches a known table (e.g., `"employees"`) using `get_table(name)` and checks if expected columns exist.
- **Significance:** Ensures that essential tables are present in the database and contain expected schema, preventing runtime errors in dependent logic.

#### `test_get_table_unknown_raises`
- **Logic:** Attempts to fetch a non-existent table and expects a `KeyError`.
- **Significance:** Validates error handling for invalid table access, helping to catch and log issues early during development.

---
## `tests/test_form_submission.py`

### Purpose
Ensures weekly report submissions and accomplishments are handled correctly and consistently.

### Tests 
-    Employee creation via get_or_create_employee
-    Workstream creation via get_or_create_workstream
-    Weekly report insertion with auditing fields (CreatedAt, EnteredBy)
-    Hours tracking logic and data accuracy
-    Prevention of duplicate entries using unique keys

### Significance
Form submissions are the primary data entry point of the system. These tests:

-    Validate data integrity during input
-    Confirm auditing fields are correctly populated
-    Ensure duplicates are prevented (using SHA-256 hash keys) 

---

## `tests/test_helpers.py`

### Purpose
Validates utility functions in utils/helpers.py to ensure consistent data cleaning and key generation.

### Tests
**Data normalization:** Whitespace trimming, title case conversion.
**Date cleaning:** Parsing and coercing date formats.
**Numeric cleaning:** Ensuring numeric fields are correctly converted.
**Key generation:** Unique employee and public IDs.
**Monday calculation:** Correctly identifying the most recent Monday for reporting periods.

### Significance
Helper functions are used across multiple modules. Testing them:

    - Ensures centralized logic behaves consistently
    - Prevents silent data corruption or transformation errors
    - Reduces redundancy in debugging other parts of the app

---

## `tests/test_page_smoke.py`

### Purpose
Conducts smoke tests to ensure all Streamlit pages load without fatal errors or missing dependencies.

### Tests
    - Dynamically imports every page in pages/*.py
    - Mocks database responses to avoid live DB dependency
    - Checks that each page can render successfully without crashing

### Significance
    - Guarantees application stability during navigation
    - Detects import or schema-related issues early
    - Provides fast feedback for CI/CD pipelines

---

## `tests/test_queries.py`

### Purpose
To test any custom SQL or ORM queries implemented in a `queries.py` utility or report generator module.

### Tests
Basic test confirms that at least one query runs and returns a plausible result set.

### Significance
Prevents silent failures in dashboard widgets or PDF reporting tools that depend on these queries. Ensures correctness of business logic tied to metrics, charts, or insights.

---

## CI/CD Integration

All tests are run automatically on each push to the main branch via GitHub Actions:
- **Failing a test = Block deployment.**
- **Passing tests = Signals readiness for merging or deploying changes.**

This minimizes risk and ensures every code change respects previously working logic.

---

## Summary

| Test File              | Primary Target               | Risk Mitigated                           |
|------------------------|------------------------------|-------------------------------------------|
| `test_db.py`           | DB schema + connection       | Missing tables, bad connection strings    |
| `test_helpers.py`      | Utility logic                | Silent data corruption or transform bugs  |
| `test_queries.py`      | Report queries               | Broken metrics, failed insights generation|

## Test Coverage Goals

    - Database: 95% coverage
    - Helpers: 100% coverage
    - Form Submission: 90% coverage
    - Page Smoke Tests: 100% coverage
    - Queries: 100% syntax coverage
