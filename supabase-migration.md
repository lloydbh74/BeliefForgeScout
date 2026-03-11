# Supabase Migration

## Goal
Migrate Scout from local SQLite to Supabase, replacing `sqlite3` with `supabase-py`, including a one-time data migration script and automated 24-hour brief archiving using Supabase `pg_cron`.

## Tasks
- [ ] Task 1: Check existing Supabase projects or create one depending on User preference → Verify: `SUPABASE_URL` and `SUPABASE_KEY` are saved in .env.
- [ ] Task 2: Apply Database Schema & RPCs via SQL → Verify: Tables (`scout_processed_posts`, `scout_briefings`, `scout_engagements`) are created and RPCs work.
- [ ] Task 3: Setup `pg_cron` for `archive_stale_briefings()` → Verify: Scheduled runs appear in Supabase Postgres logs.
- [ ] Task 4: Write Migration Script (`scripts/migrate_to_supabase.py`) → Verify: Run script locally to push existing SQLite rows into Postgres without duplicate errors.
- [ ] Task 5: Refactor `core/db.py` to use `supabase-py` instead of SQLite → Verify: Methods execute against Postgres instance without exceptions.
- [ ] Task 6: Audit Python Dependencies → Verify: `supabase` library is in `requirements.txt` and installed.
- [ ] Task 7: Run tests and `checklist.py` → Verify: Python scripts pass tests and Scout web UI loads successfully with Supabase active.

## Done When
- [ ] New Supabase DB holds `scout.db` data.
- [ ] The web UI reads from Supabase directly instead of `scout.db`.
- [ ] `archive_stale_briefings` runs automatically without human intervention.
