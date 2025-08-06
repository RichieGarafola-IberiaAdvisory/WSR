# Test Suite Documentation: Logic and Significance

## **Overview**

This test suite validates the full functionality of the WSR (Weekly
Status Reports) application. It covers: 
- **Database integrity and schema**
- **Helper utilities**
- **Form submission workflows (normal, edge cases, negative scenarios)**
- **Validation functions**
- **Page loading stability**
- **Custom queries**

All tests are built with **pytest** and integrated with **GitHub
Actions** for CI/CD, ensuring that every code change is automatically
tested before deployment to maintain stability and reliability.

This documentation is structured to support
future developers with full clarity on the **purpose**, **logic**, and
**significance** of each test module.

------------------------------------------------------------------------

## **Database Tests -- `tests/test_db.py`**

-   **Purpose:** Verify database connectivity, schema, and table
    retrieval utilities.
-   **Tests:**
    -   `test_get_engine_returns_engine` → Ensures valid SQLAlchemy engine
        creation is returned.
    -   `test_get_metadata_returns_metadata` → Confirms schema
        reflection, ensures metadata has a tables attribute.
    -   `test_get_table_known` → Checks essential tables exist with
        expected columns.
    -   `test_get_table_unknown_raises` → Verifies proper error handling
        for invalid tables.
-   **Risk Mitigated:** Broken database connections, missing or misnamed
    tables.

-   **Significance:** These are foundational tests---they ensure that any function
depending on the database can safely rely on valid connections and an
accurate schema. If these fail, nearly all downstream functionality will
break.


------------------------------------------------------------------------

## **Helper Function Tests -- `tests/test_helpers.py`**

-   **Purpose:** Validate utility functions for normalization, ID
    generation, data cleaning, and helper DB interactions.
-   **Tests:**
    -   `normalize_text`→ Standardizes string formatting (title case,
    whitespace removal).
    -   `generate_employee_key`→ Creates deterministic, SHA-256--based
    unique identifiers for employees.
    -   `generate_public_id`→ Formats public-facing IDs from names and
    numeric suffixes.
    -   `clean_dataframe_dates_hours`→ Converts date strings and numeric
    inputs into clean, type-safe formats.
    -   `get_or_create_employee` / `get_or_create_workstream`→ Lookup or
    insert database records in a controlled manner.

-   **Risk Mitigated:** Data corruption or inconsistent transformations
    affecting reporting.

-   **Significance:** These functions are used throughout the application. Errors here
would silently corrupt data, introduce duplicates, or cause form
submissions to fail unexpectedly. Ensuring consistency here reduces bugs
system-wide.

------------------------------------------------------------------------

## **Form Submission Tests**

### `tests/test_form_submission.py`

-   **Purpose:** Test the main weekly report submission pipeline. Validates
  the full report submission workflow from form input to database insertion.
-   **Tests:**
    -   `test_cleaning_and_insertion_pipeline`→ Verifies that form data is
        cleaned and employees are correctly matched or created.
    -   `test_successful_form_submission`→ Tests the standard success
        path---clean data, employee creation, and data insertion.
    -   `test_bad_data_rejected`→ Ensures that submissions with invalid
        inputs do not proceed to insertion.
    -   `test_empty_required_fields`→ Fails if critical fields like name,
        vendor, or labor category are blank.
    -   `test_duplicate_submission`→ Ensures the same form submission
        doesn't create duplicate entries.
    -   `test_max_length_fields`→ Verifies that long strings (e.g., names)
        do not cause insertion failures.
    -   `test_invalid_date_format`→ Rejects invalid date inputs.
-   **Risk Mitigated:** Prevents bad or duplicate data entries that
    could compromise reports.
    
-   **Significance:** This module tests the core user interaction: entering
  and submitting reports. It's essential to prevent dirty, duplicate, or partial
data from reaching the database. Without this, dashboards and reports could
be severely compromised.


### `tests/test_form_submission_edge_cases.py`

-   **Purpose:** Tests data entry edge cases around accomplishment field validation.
-   **Tests:**
    -   `test_validate_accomplishments_with_extra_entries`→ Validates that
    exactly 5 accomplishments are accepted.
    -   `test_validate_accomplishments_with_missing_entries`→ Rejects
    submissions with fewer than 5 accomplishments.

-   **Risk Mitigated:** Ensures consistent validation rules and prevents
    incomplete submissions.

-   **Significance:** These tests ensure that performance reviews and weekly output tracking
are consistently measured. Submissions missing accomplishments could
weaken client-facing metrics.

### `tests/test_form_submission_negative.py`

-   **Purpose:** Tests invalid or minimal data scenarios (negative scenarios).
-   **Tests:**
    -   `test_missing_required_fields_blocks_submission`→ Prevents empty
    submissions from proceeding.
-   `test_partial_required_fields_allows_submission`→ Ensures forms
    missing critical fields are rejected.
    
-   **Risk Mitigated:** Stops incomplete or incorrect data from entering
    the database.

-   **Significance:** These tests enforce strict submission rules, ensuring accountability and
report completeness. Preventing invalid entries at this level avoids
downstream cleanup or auditing issues.

------------------------------------------------------------------------

## **Validation Function Tests -- `tests/test_validation_functions.py`**

-   **Purpose:** Ensures accomplishment validation flags scenarios where users attempt to
bypass the 5-accomplishment rule across rows.
-   **Tests:**
    -   `test_exceeding_accomplishments_flagged`→ Ensures more than 5 tasks,
    even across multiple rows, are caught and flagged.

-   **Risk Mitigated:** Over-reporting or invalid accomplishment counts.

-   **Significance:** Without this safeguard, users could split their accomplishments across
multiple rows to appear more productive---compromising analytics and
fairness.
  
------------------------------------------------------------------------

## **Page Smoke Tests -- `tests/test_page_smoke.py`**
-   **Purpose:** Validates that every Streamlit page: - Can load without exceptions - Has
required DB schema - Returns valid SQL/DF data
-   **Tests:**
    -   Automatically loads all files in `pages/`
    -   Mocks DB and query results to prevent live dependency
    -   Confirms page renders without error

-   **Risk Mitigated:** Navigation failures or runtime crashes in
    production.

-   **Significance:** Prevents last-minute production failures during navigation. These smoke
tests act as an early warning system for broken imports, DB schema
drift, or dependency mismatches.

------------------------------------------------------------------------

## **Query Tests -- `tests/test_queries.py`**
-   **Purpose:** Validates raw SQL queries used in dashboard reports or metrics.
-   Verifies that custom SQL queries:
-   **Tests:**
    -   `test_weekly_reports_query_compiles`→ Ensures the
    `weekly_reports_with_employees` query is syntactically valid and
    contains a `SELECT` clause.

-   **Risk Mitigated:** Prevents dashboard/reporting failures due to
    broken SQL statements.

-   **Significance:** A single typo or broken query could bring down your **entire reporting
interface**. This test ensures the foundation of analytics remains
intact.

------------------------------------------------------------------------

## **Fixtures and Mocks -- `conftest.py`**
-   **Purpose:** Provides global fixtures to mock: - Database tables and metadata -
Helper methods - SQLAlchemy `execute` calls.
  
-   **Significance:** Allows test isolation from live databases, enabling fast, safe,
repeatable unit tests.

------------------------------------------------------------------------

## **Test Coverage Goals**

  --------------------------------------------------------------------------
  Test File                        Purpose                      Coverage
                                                                Goal
  -------------------------------- ---------------------------- ------------
  `test_db.py`                     DB schema & connectivity     95%

  `test_helpers.py`                Utility logic                100%

  `test_form_submission*.py`       Form workflows & edge cases  90%

  `test_validation_functions.py`   Accomplishment validation    100%

  `test_page_smoke.py`             Page stability               100%

  `test_queries.py`                Custom query validity        100%
  --------------------------------------------------------------------------

------------------------------------------------------------------------

## **Continuous Integration**

-   All tests automatically run on every push via GitHub Actions.
-   **Failing tests block deployment** to protect production integrity.
-   Passing tests confirm the system is stable and ready for release.

## Summary

This test suite is the **quality gate** of the WSR application. Future
developers can use this documentation to:

-   Understand which parts of the system are being tested
-   Modify or extend coverage safely
-   Rebuild trust in the system after changes

Each test reflects a deliberate design decision to guard against
specific risks---**from data corruption to usability failures**.

---

# Maintain it. Expand it. Trust it.


