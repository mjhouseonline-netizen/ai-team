# Deployment Guide - Keeping Your Data Safe

## ✅ Your Data is Safe!

Your client data (users, custom agents, chat history) is stored in SQLite database files that are **NOT** tracked by git. When you update your site, the database files remain untouched.

## Database Files Location

- **Primary DB**: `ai_team.db` (main application database)
- **Users DB**: `users.db` (legacy user data)
- **Platform DB**: `ai_team_platform.db` (legacy platform data)
- **Persistent**: `/data/ai_team.db` (if using persistent disk)

## Safe Update Process

### Method 1: Simple Update (Recommended)

```bash
# 1. Backup databases (optional but recommended)
./backup_database.sh

# 2. Pull latest changes
git pull origin main

# 3. Restart your application
# (exact command depends on your setup)
```

### Method 2: Full Safety Update

```bash
# 1. Create backup
./backup_database.sh

# 2. Check what files will be affected
git fetch origin
git diff origin/main

# 3. Pull updates (databases are ignored by git)
git pull origin main

# 4. Check if any database migrations are needed
# (we use automatic migrations, so this usually "just works")

# 5. Restart application
sudo systemctl restart your-app-name
# OR
pm2 restart your-app-name
# OR
docker-compose restart
```

## What Gets Updated vs What Stays

### Updated (Code Changes):
- ✅ Python files (.py)
- ✅ HTML templates
- ✅ CSS/JavaScript
- ✅ New features
- ✅ Bug fixes

### NOT Updated (Your Data):
- ❌ Database files (.db)
- ❌ Uploaded files
- ❌ Environment variables (.env)
- ❌ API keys
- ❌ User data

## Automatic Database Migrations

The app uses **automatic schema migrations**! When you update:

1. New tables are created automatically
2. New columns are added automatically
3. Existing data is preserved
4. No manual migration needed

Example from code:
```python
# Check and add missing columns
if 'emoji' not in columns:
    cursor.execute("ALTER TABLE custom_agents ADD COLUMN emoji TEXT DEFAULT '🤖'")
    conn.commit()
```

## Backup Strategy

### Manual Backup (Before Updates)

```bash
./backup_database.sh
```

This creates timestamped backups in `./backups/`:
- `ai_team_20241224_143000.db`
- `users_20241224_143000.db`
- etc.

### Automatic Backup (Recommended)

Set up a cron job:

```bash
# Edit crontab
crontab -e

# Add this line (daily backup at 2 AM)
0 2 * * * /path/to/ai-team/backup_database.sh

# Or hourly backups
0 * * * * /path/to/ai-team/backup_database.sh
```

### Production Backup (Best Practice)

For production, use:
1. **Database replication** (if using PostgreSQL/MySQL)
2. **Cloud backups** (AWS S3, Google Cloud Storage)
3. **Snapshot backups** (if using Docker volumes)

## Restore from Backup

If something goes wrong:

```bash
# Stop application
sudo systemctl stop your-app-name

# Restore database
cp backups/ai_team_YYYYMMDD_HHMMSS.db ai_team.db

# Start application
sudo systemctl start your-app-name
```

## Using Persistent Disk (Recommended for Production)

If you have a `/data` directory:

```bash
# The app automatically uses it!
# Check startup logs:
# "✅ Using persistent disk: /data/ai_team.db"
```

Benefits:
- Survives container restarts (Docker)
- Survives instance replacements (Cloud)
- Easy to backup and restore
- Better performance

## Database Size Monitoring

Check database size:

```bash
# Current size
du -sh *.db

# Watch growth over time
watch -n 60 'du -sh *.db'
```

## Migration Testing

Before deploying to production:

1. **Test locally first**:
```bash
# Backup production DB
./backup_database.sh

# Copy to local
scp user@server:/path/to/ai_team.db ./ai_team_test.db

# Test update locally
git pull origin main
python web_app_auth.py
```

2. **Verify migrations worked**:
```bash
# Check tables
sqlite3 ai_team.db ".tables"

# Check schema
sqlite3 ai_team.db ".schema custom_agents"
```

## Rollback Plan

If update causes issues:

```bash
# 1. Stop application
sudo systemctl stop your-app-name

# 2. Restore code
git reset --hard HEAD~1

# 3. Restore database (if needed)
cp backups/ai_team_LATEST.db ai_team.db

# 4. Start application
sudo systemctl start your-app-name
```

## Common Deployment Scenarios

### Scenario 1: Adding New Feature (No Schema Changes)
- ✅ Just `git pull` and restart
- ❌ No backup needed (but still good practice)

### Scenario 2: Adding New Table/Column
- ✅ Automatic migration handles it
- ✅ Backup recommended
- ✅ Pull and restart

### Scenario 3: Changing Existing Data Structure
- ⚠️ Rare, but needs careful migration
- ✅ Always backup first
- ✅ Test locally
- ✅ Review migration code

## Zero-Downtime Deployment (Advanced)

For production sites with users:

```bash
# 1. Backup
./backup_database.sh

# 2. Pull code (app still running)
git pull origin main

# 3. Reload app (no downtime)
sudo systemctl reload your-app-name
# OR
pm2 reload your-app-name
# OR (blue-green deployment)
docker-compose up -d --no-deps --build app
```

## Health Checks After Update

```bash
# 1. Check logs
tail -f /var/log/your-app.log

# 2. Test database connection
sqlite3 ai_team.db "SELECT COUNT(*) FROM users;"

# 3. Test API
curl http://localhost:5000/api/user-stats

# 4. Check disk space
df -h
```

## Summary

✅ **Your data is safe** - database files are git-ignored
✅ **Automatic migrations** - new columns/tables added automatically
✅ **Easy backups** - `./backup_database.sh` before updates
✅ **Simple updates** - `git pull` and restart
✅ **Rollback ready** - backups let you revert if needed

**Best Practice**: Always run `./backup_database.sh` before pulling updates!
