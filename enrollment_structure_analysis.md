# Enrollment Structure Analysis

This document analyzes the structural issues in `enrollment_starter.py` and explains why each issue can hurt scalability or maintainability.

| Issue | Affected code | Why it hurts scalability / maintainability |
|---|---|---|
| Global state and config are mixed with logic | `DB_PATH`, `SNAPSHOT_PATH`, `CURRENT_STUDENT`, `AVAILABLE_COURSE_KEYS`, `SAMPLE_ENROLLMENTS`, status constants | Global state makes behavior implicit and hard to reuse. It prevents easy testing, multi-user operation, and reuse of the functions in another context because they depend on module-level values. |
| Persistence and service logic are intermingled | `get_course_by_key`, `get_student_enrollments`, `get_student_enrollment_history`, `get_student_course_record`, `enroll_with_key`, `soft_unenroll_student`, `get_all_enrollment_records` | These functions execute SQL and also make business decisions or represent service operations. That coupling means changing the DB layer or adding a new service layer will require touching many functions, instead of swapping in a cleaner API. |
| Business validation/decisions inside database methods | `enroll_with_key` validates email/key and performs an upsert with status logic; `get_student_summary` computes aggregates from raw records | Service-level rules are embedded in persistence code. This makes the DB layer responsible for domain rules, which is brittle for future business changes and hard to refactor into a proper service/domain layer. |
| Side-effectful top-level runner mixed with app logic | `main()` seeds data, prints output, and writes snapshots using `CURRENT_STUDENT` | A runner function that bootstraps sample data and exports JSON is okay for demos, but when mixed in the same module it encourages a module to have both application startup flow and reusable service functions. This can create surprising side effects when importing or extending the module. |
| Export and snapshot logic coupled to current state | `export_database_snapshot()` writes JSON using `CURRENT_STUDENT`, `get_available_course_keys()`, and `get_all_enrollment_records()` | Snapshot generation is both a persistence/export concern and uses service data. This coupling makes it harder to change export format or separate data retrieval from serialization. |
| Database connection management is too low-level and scattered | `connect()` is a simple helper; every function opens its own connection | The lack of a connection/transaction abstraction means scaling to a multi-request app or switching databases will require rewriting every database-access function. There is no clear separation of DB config from DB usage. |

### Notes on layer mixing

- `enroll_with_key` is a clear example where the function both:
  - looks up a course by key (service/business concern)
  - performs an insert/update in SQL with status handling (persistence concern)
- `get_student_summary` also shows mixing: it uses a data access helper and then applies a domain aggregate rule, which is a service-level calculation.
- The file has no distinct boundary between:
  - database layer (`connect`, `create_tables`, `seed_sample_data`, SQL queries)
  - service/domain layer (`get_course_by_key`, `enroll_with_key`, `get_student_summary`)
  - application runner/output (`main`, `print()` calls, `export_database_snapshot()`)

### Summary

The structural problem is not just individual functions: the whole module blends configuration, database persistence, business validation, domain aggregation, and example runner logic in one place. That design pattern will make the code harder to extend, test, and scale as the app grows.

## Refactor Plan

### Goal
Move the code from a single procedural module into a layered backend design where:
- SQLite remains focused on row-level queries and updates only
- business meaning lives in a service layer
- configuration and runtime state are separated from behavior
- the module becomes easier to extend, test, and maintain

### Proposed Architecture

#### 1. Config / Constants Layer
Purpose:
- keep file paths, status constants, sample data, and environment values separate
- avoid global state spread throughout logic

What belongs here:
- `DB_PATH`
- `SNAPSHOT_PATH`
- `STATUS_ENROLLED`, `STATUS_UNENROLLED`
- `AVAILABLE_COURSE_KEYS`
- `CURRENT_STUDENT` or test/demo user data

Why:
- keeps configuration declarative
- makes the rest of the backend easier to reuse and unit test

#### 2. Database Layer
Purpose:
- encapsulate SQLite connection handling
- expose row-based CRUD operations only
- avoid service/business decisions here

What belongs here:
- `connect()` / connection factory
- table creation and seeding methods
- repository-style functions or a `Repository` class for:
  - reading courses by key
  - fetching enrollment rows
  - inserting/updating enrollments
  - updating status
  - querying all enrollment records

What must not happen here:
- enrollment-key validation
- dashboard composition
- summary counting
- any domain decision beyond “this row exists / this row changed”

Why:
- keeps persistence concerns isolated
- makes it possible to swap DB implementation or test via mocks
- avoids mixing SQL with domain rules

#### 3. Service Layer
Purpose:
- coordinate domain rules
- keep business meaning here
- handle validation, dashboard semantics, summary counting

What belongs here:
- `EnrollmentService` or `EnrollmentManager`
- methods such as:
  - `enroll_with_key(user_id, email, enrollment_key)`
  - `get_dashboard_for_student(user_id)`
  - `get_student_enrollment_history(user_id)`
  - `get_student_summary(user_id)`
  - `soft_unenroll_student(user_id, course_id)`
- validation logic:
  - email sanity check
  - enrollment key format and existence
  - activation/reactivation semantics
- dashboard semantics:
  - available enrollment keys
  - currently enrolled classes
  - history and summary counts
- summary counting:
  - compute totals from raw enrollment rows
  - separate “counting” from database row retrieval

Why:
- preserves domain behavior in one place
- allows the DB layer to remain simple and stable
- improves readability and maintainability
- makes unit testing business behavior straightforward

#### 4. Application / Runner Layer
Purpose:
- keep sample/demo startup and Streamlit UI integration separate from backend logic

What belongs here:
- `main()` or runner code that:
  - bootstraps DB
  - seeds sample data
  - calls service methods for demonstration
  - triggers snapshot export
- Streamlit UI that:
  - calls service layer methods
  - does not contain core business rules

Why:
- prevents side-effectful startup code from contaminating core backend modules
- keeps the backend reusable in other contexts

### Refactor Strategy

1. Extract configuration
- move constants and path definitions into a dedicated section or module
- avoid hard-coded runtime state inside logic functions

2. Build a minimal DB repository
- create a SQLite-focused repository abstraction
- keep methods simple: query rows, insert rows, update rows

3. Create a service class
- move enrollment-key validation, dashboard composition, and summary calculation here
- have it depend on the repository, not on raw SQL calls

4. Separate the runner
- keep `main()` as a top-level script only
- ensure import of the backend module does not immediately seed or print

5. Preserve row query style
- when returning database results, keep them as dict/row records
- avoid stuffing business rules into SQL beyond necessary joins

6. Add clarity around layer boundaries
- database layer: “what data is stored”
- service layer: “what enrollment means”
- runner/UI layer: “how we use it”

### Why this plan helps

- Reduces coupling between persistence and business behavior
- Makes validation and domain rules easier to update
- Makes it easier to add multiple students, dashboards, or UI front ends
- Avoids the problem of “one module does everything”
- Enables better unit tests for service logic and repository behavior

### Next implementation prompt

When you approve the plan, use this prompt:

> Refactor `enrollment_starter.py` into a layered backend design without changing behavior. Create a configuration/constants section, a SQLite-focused database repository, and a service class that contains business meaning such as enrollment-key validation, dashboard composition, and summary counting. Keep the database layer limited to row queries, inserts, and updates. Keep the service layer responsible for enrollment rules, active enrollment dashboard semantics, and summary calculations. Preserve the existing demo runner as a separate application entry point and avoid moving domain logic into the persistence layer.
