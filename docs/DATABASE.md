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

### `companies` (Module 3)

```
companies
├─ id                    PK
├─ name                  not null, indexed
├─ website / domain (indexed) / career_page / linkedin_url
├─ industry (indexed) / location / remote_friendly / employee_count
├─ tech_stack            comma-separated text (list in API)
├─ hiring_platform       ATS slug (refined by Module 4)
├─ funding_stage         enum (bootstrapped … public | unknown)
├─ hiring_status         enum (hiring | not_hiring | unknown)
├─ source                provenance (discovery provider id)
└─ created_at / updated_at
   unique (name, website)
```

## Planned tables (future modules)

### `job_listings` (Module 4)

```
job_listings
├─ id                 PK
├─ company_id         FK → companies (cascade)
├─ external_id        ATS-assigned id (for idempotent upsert)
├─ title              not null
├─ location / department / employment_type / url / description / remote
└─ created_at / updated_at
   unique (company_id, external_id)
```

Module 4 also adds `companies.ats_platform` (normalized enum: greenhouse, lever,
ashby, workday, smartrecruiters, bamboohr, jobvite, oracle, sap_successfactors,
custom, unknown).

## Planned tables (future modules)

| Module | Tables (planned) |
| ------ | ---------------- |
| 5 People Discovery | `people` |
| 7 Email Verification | `email_verifications` |
| 10 Templates | `email_templates` |
| 13 Application Tracker | `applications`, `application_events` |
| 14/15 Outreach | `outreach_messages` (with `pending_review` state), `outreach_events` |

These attach to `user_profiles` and `companies` and follow the same conventions.
