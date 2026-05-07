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
