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

### `people` (Module 5)

```
people
├─ id                 PK
├─ company_id         FK → companies (cascade)
├─ external_id        provider-assigned id (for idempotent upsert)
├─ full_name (indexed) / title / department / location
├─ linkedin_url / profile_url
├─ email (indexed)    likely deliverable address (may be a public pattern)
├─ email_verified     bool — discovery never sets this; Module 7 verifies
├─ role               enum (recruiter | hiring_manager | executive | engineer | employee | unknown)
├─ email_source       enum (public | pattern | unknown)
├─ source             provenance (discovery provider id)
└─ created_at / updated_at
   unique (company_id, external_id)
```

### `email_verifications` (Module 7)

```
email_verifications
├─ id                 PK
├─ person_id          FK → people (cascade)
├─ email              not null (indexed)
├─ status             enum (valid | invalid | risky | unknown)
├─ syntax_ok / domain_ok / mx_found / is_disposable / is_role_account  bools
├─ confidence         float 0..1
├─ reason             human-readable verdict explanation
├─ verifier           which verifier produced the result
└─ created_at / updated_at
   unique (person_id, email)
```

A `valid` verdict sets `people.email_verified = true` — the deliverability gate
that downstream sending honors.

### `job_matches` (Module 8)

```
job_matches
├─ id                 PK
├─ profile_id         FK → user_profiles (cascade)
├─ job_listing_id     FK → job_listings (cascade)
├─ score              overall fit 0..1
├─ skill_score / title_score / location_score   component sub-scores 0..1
├─ matched_skills / missing_skills   comma-separated (lists in API)
├─ rationale          human-readable explanation
├─ matcher            which matcher produced the result
└─ created_at / updated_at
   unique (profile_id, job_listing_id)
```

### `cover_letters` (Module 9)

```
cover_letters
├─ id                 PK
├─ profile_id         FK → user_profiles (cascade)
├─ company_id         FK → companies (cascade)
├─ job_listing_id     FK → job_listings (set null) — optional, role-specific
├─ subject / body     the generated draft (body not null)
├─ tone               enum (professional | enthusiastic | concise)
├─ word_count         int
├─ generator          which generator produced the draft
└─ created_at / updated_at
```

Generated letters are drafts for review — never auto-sent.

### `email_templates` (Module 10)

```
email_templates
├─ id                 PK
├─ name               not null, unique (indexed)
├─ category           enum (outreach | referral | follow_up | thank_you | other)
├─ subject_template / body_template   text with {placeholder} slots (not null)
├─ description        optional
├─ is_builtin         seeded templates are read-only
└─ created_at / updated_at
   unique (name)
```

Four built-in templates are seeded on first use. Rendering substitutes
placeholders from a profile/company/person/job context — it never sends.

## Planned tables (future modules)

| Module | Tables (planned) |
| ------ | ---------------- |
| 13 Application Tracker | `applications`, `application_events` |
| 14/15 Outreach | `outreach_messages` (with `pending_review` state), `outreach_events` |

These attach to `user_profiles` and `companies` and follow the same conventions.
