# HMIS Reporting

Health Management Information System for district health reporting.

An **admin** uploads facilities, programs and reported values as CSV or Excel files.
A **viewer** picks a facility, a program and a reporting period on the dashboard and sees
exactly the values the admin uploaded for that combination — nothing is generated or
inferred by the system.

## Getting started

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo          # demo accounts + sample_data/*.csv
.venv/bin/python manage.py runserver
```

`seed_demo` creates `hmisadmin` (staff, can upload) and `hmisviewer` (dashboard only),
both with password `hmis12345`. For a clean install use `createsuperuser` instead.

| URL | Who | Purpose |
| --- | --- | --- |
| `/` | any logged-in user | dashboard with facility / program / period filters, CSV export |
| `/upload/` | staff only | upload facilities, programs or program data |
| `/admin/` | staff only | Django admin for manual edits |

Viewers are ordinary users; admins are users with the *staff* flag.

## Upload formats

Download a blank template for each data set from `/upload/`. Column names are
case-insensitive and spaces are treated as underscores.

**Facilities** — `code`, `name` required; `district`, `facility_type`, `is_active` optional.

**Programs** — `code`, `name` required; `description`, `is_active` optional.

**Program data** — `facility_code`, `program_code`, `indicator_code`, `indicator_name`,
`period_code`, `value` required; `indicator_unit`, `period_name`, `period_type`,
`period_start`, `period_end` optional (the period columns are required the first time a
`period_code` is seen, since the period is created from them).

Import rules:

- Facilities and programs are matched by `code`, so re-uploading a file corrects existing
  rows instead of duplicating them.
- A data row is keyed by facility + program + indicator + period: re-uploading a period
  overwrites those values and leaves everything else untouched.
- Data rows must reference a facility and program that already exist — an unknown code is
  reported as an error rather than silently creating a new facility.
- An upload is all-or-nothing. If any row fails validation the whole file is rejected, the
  errors are listed with their row numbers, and the database is unchanged. Every attempt is
  recorded in the upload history.

## Tests

```bash
.venv/bin/python manage.py test
```

## Settings

`DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (`0`/`1`) and `DJANGO_ALLOWED_HOSTS` (comma-separated)
are read from the environment. Set all three before deploying.
