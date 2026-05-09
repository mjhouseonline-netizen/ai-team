# Low-Cost Single Deploy (Scalable Starter)

This app now supports a safer one-service deployment model with centralized storage paths.

## Goal

Keep costs low while avoiding data loss:
- One app service
- SQLite database
- Persistent mounted disk
- Daily backups

## Required Environment Variables

- `DATA_DIR`:
  Set this to your persistent disk mount path (example: `/data`).
- `DB_PATH` (optional):
  Defaults to `DATA_DIR/ai_team.db`.
- `UPLOAD_FOLDER` (optional):
  Defaults to `DATA_DIR/uploads`.
- `OUTPUT_FOLDER` (optional):
  Defaults to `DATA_DIR/outputs`.
- `BACKUP_ROOT` (optional):
  Defaults to `DATA_DIR/backups`.
- `MIGRATION_BACKUP_DIR` (optional):
  Defaults to `DATA_DIR/migration_backups`.

## What Happens on Startup

The app now:
1. Creates all storage directories.
2. Runs storage safety checks.
3. Prints warnings if production storage looks ephemeral or unwritable.

## Health and Operations Endpoints

- `GET /api/storage-health`:
  Shows current paths and write access.
- `POST /api/admin/run-backup`:
  Admin-only manual DB backup trigger.
  Example JSON body:
  `{"reason":"pre_deploy"}`

## Deployment Checklist

1. Mount persistent disk.
2. Set `DATA_DIR` to that mount path.
3. Deploy app.
4. Log in as admin and verify:
   - `/api/storage-health`
   - `writable: true` for key paths.
5. Run an initial backup with `/api/admin/run-backup`.

## Scaling Path

When traffic grows:
1. Move DB to managed Postgres.
2. Move uploads to object storage.
3. Add Redis for cache/rate limiting/queues.

This lets you start cheap today and migrate without rewriting product logic.
