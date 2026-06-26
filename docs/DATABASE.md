# Database Schema

CareerPilot uses SQLAlchemy 2.0 (async). SQLite is the local/test default;
PostgreSQL is the production target. Schema changes are managed by Alembic
(migrations land alongside the modules that introduce them).

## Conventions

- Integer surrogate primary keys.
- `TimestampMixin` adds `created_at` / `updated_at` to aggregate roots.
- Child rows reference their parent with `ON DELETE CASCADE`.
- Enums are stored as strings (`native_enum=False`) for portability.

## Module 1 — User Profile

```
user_profiles
├─ id                    PK
├─ name                  not null
├─ email                 not null, unique, indexed
├─ phone
├─ resume_path
├─ github_url / portfolio_url / linkedin_url
├─ preferred_role
├─ preferred_location
├─ work_authorization    enum (citizen | permanent_resident | work_visa |
│                               student_visa | needs_sponsorship | other)
├─ preferred_companies   comma-separated text (list in API)
├─ preferred_salary_min / preferred_salary_max
├─ availability
├─ created_at / updated_at
│
├─< profile_skills        (profile_id, name) unique
│     ├─ name, proficiency, years
├─< profile_experiences
│     ├─ company, title, location, start_date, end_date, description, is_internship
├─< profile_educations
│     ├─ institution, degree, field_of_study, start_date, end_date, grade
├─< profile_projects            (added by Module 2)
│     ├─ name, description, tech_stack (csv), url
└─< profile_achievements        (added by Module 2)
      ├─ description
```

`< ` denotes a one-to-many relationship cascaded from `user_profiles`.

## Planned tables (future modules)

| Module | Tables (planned) |
| ------ | ---------------- |
| 3 Company Discovery | `companies` |
| 4 Career Page Detection | `company_ats` |
| 5 People Discovery | `people` |
| 7 Email Verification | `email_verifications` |
| 10 Templates | `email_templates` |
| 13 Application Tracker | `applications`, `application_events` |
| 14/15 Outreach | `outreach_messages` (with `pending_review` state), `outreach_events` |

These attach to `user_profiles` and `companies` and follow the same conventions.
