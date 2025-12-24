# Deployment Guide - Keeping Your Data Safe

## ✅ Your Data is Safe!

Your client data (users, custom agents, chat history) is stored in SQLite database files that are **NOT** tracked by git. When you update your site, the database files remain untouched.

## Database Files Location

- **Primary DB**: `ai_team.db` (main application database)
- **Users DB**: `users.db` (legacy user data)
- **Platform DB**: `ai_team_platform.db` (legacy platform data)
- **Persistent**: `/data/ai_team.db` (if using persistent disk)

## Custom Agent Data Protection

Your custom agents are protected in TWO locations:

### 1. Custom Agent Definitions (Database)
- **Location**: `ai_team.db` → `custom_agents` table
- **Contains**: Agent names, instructions, personalities, emoji
- **Protection**: Git-ignored, auto-backed up
- **Migration**: Auto-adds new columns (like `icon_image`)

### 2. Custom Agent Icons (Files)
- **Location**: `static/uploads/agent_icons/`
- **Contains**: Uploaded custom agent icon images
- **Protection**: Git-ignored, backed up by `./backup_database.sh`
- **Fallback**: Emoji used if image missing

⚠️ **CRITICAL**: Both the database AND the icon images must be backed up to fully preserve custom agents!

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

**Database Backups:**
- `ai_team_20241224_143000.db` (all user data, custom agents)
- `users_20241224_143000.db` (legacy user data)
- etc.

**Custom Agent Icon Backups:**
- `agent_icons_20241224_143000/` (all uploaded agent icons)

**All Uploaded Files:**
- `uploads_20241224_143000/` (all user uploads)

The script automatically backs up:
✅ All databases
✅ Custom agent icon images
✅ All uploaded files
✅ Keeps last 10 backups of each

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

If something goes wrong, use the restore script:

### Automatic Restore (Recommended)

```bash
# Stop application first
sudo systemctl stop your-app-name

# Run restore script (interactive)
./restore_backup.sh

# The script will:
# 1. Show available backups
# 2. Let you choose which backup to restore
# 3. Create safety backups before restoring
# 4. Restore database AND custom agent icons
# 5. Restore all uploaded files

# Start application
sudo systemctl start your-app-name
```

### Manual Restore

```bash
# Stop application
sudo systemctl stop your-app-name

# Restore database
cp backups/ai_team_YYYYMMDD_HHMMSS.db ai_team.db

# Restore custom agent icons
cp -r backups/agent_icons_YYYYMMDD_HHMMSS/* static/uploads/agent_icons/

# Restore all uploads (optional)
cp -r backups/uploads_YYYYMMDD_HHMMSS/* static/uploads/

# Start application
sudo systemctl start your-app-name
```

⚠️ **IMPORTANT**: Always restore BOTH the database AND the agent_icons directory to preserve custom agents completely!

## Custom Agent Safety Checklist

Before ANY update, verify your custom agents are protected:

### ✅ Pre-Update Checklist

```bash
# 1. Run backup script
./backup_database.sh

# 2. Verify database backup exists
ls -lh backups/ai_team_*.db | tail -1

# 3. Verify icon backups exist (if you have custom agents with images)
ls -lh backups/agent_icons_* | tail -1

# 4. Check current custom agents
sqlite3 ai_team.db "SELECT name, icon_image FROM custom_agents;"

# 5. Count custom agent icons
ls -1 static/uploads/agent_icons/ 2>/dev/null | wc -l
```

### ✅ Post-Update Verification

```bash
# 1. Check database still exists
ls -lh ai_team.db

# 2. Check custom agents table
sqlite3 ai_team.db "SELECT COUNT(*) FROM custom_agents;"

# 3. Check icon_image column exists
sqlite3 ai_team.db ".schema custom_agents" | grep icon_image

# 4. Check agent icons directory
ls -lh static/uploads/agent_icons/

# 5. Test in browser - custom agents should display with their icons
```

### 🚨 What to Do If Custom Agents Are Missing

If custom agents don't show up after an update:

```bash
# 1. Check if database was accidentally overwritten
ls -lh ai_team.db

# 2. Check if icon directory exists
ls static/uploads/agent_icons/

# 3. Restore from backup immediately
./restore_backup.sh

# 4. Select 'latest' or the timestamp before the update
```

### 💾 What Gets Backed Up Automatically

When you run `./backup_database.sh`:

1. **✅ Custom Agent Definitions** (database)
   - Agent names
   - Instructions/personalities
   - Emoji fallbacks
   - Share codes
   - Folder organization

2. **✅ Custom Agent Icons** (files)
   - All uploaded PNG/JPG/GIF/WebP images
   - Full directory structure preserved
   - Stored in `backups/agent_icons_TIMESTAMP/`

3. **✅ All User Uploads** (files)
   - Chat attachments
   - Any other uploaded files
   - Stored in `backups/uploads_TIMESTAMP/`

### 📊 Custom Agent Storage Locations

```
ai-team/
├── ai_team.db                          # Contains custom_agents table
├── static/
│   └── uploads/
│       └── agent_icons/                # Custom agent icon images
│           ├── abc123xyz.png           # User 1's agent icon
│           ├── def456uvw.jpg           # User 2's agent icon
│           └── ...
└── backups/
    ├── ai_team_20241224_120000.db      # Database backup
    ├── agent_icons_20241224_120000/    # Icons backup
    │   ├── abc123xyz.png
    │   └── def456uvw.jpg
    └── uploads_20241224_120000/        # Full uploads backup
```

### 🔐 Protection Guarantees

✅ **Git Protection**: `static/uploads/` is in `.gitignore` - never committed
✅ **Backup Script**: Automatically backs up both database AND icons
✅ **Restore Script**: Restores both database AND icons together
✅ **Migration Safety**: Database schema auto-migrates, preserves all data
✅ **Fallback System**: If icon missing, emoji is used automatically

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
✅ **Custom agents protected** - both database AND icon images backed up
✅ **Automatic migrations** - new columns/tables added automatically
✅ **Easy backups** - `./backup_database.sh` before updates
✅ **Easy restore** - `./restore_backup.sh` if anything goes wrong
✅ **Simple updates** - `git pull` and restart
✅ **Rollback ready** - backups let you revert if needed
✅ **Dual protection** - database + file backups for custom agents

**Best Practice**: Always run `./backup_database.sh` before pulling updates!

## Quick Reference

### Before Updating
```bash
./backup_database.sh  # Backs up database + custom agent icons + all uploads
git pull origin main
# Restart your app
```

### If Something Goes Wrong
```bash
./restore_backup.sh   # Interactive restore of database + icons + uploads
# Choose backup timestamp or 'latest'
# Restart your app
```

### Custom Agent Safety
- **Database**: `ai_team.db` → `custom_agents` table (auto-backed up)
- **Icons**: `static/uploads/agent_icons/` → image files (auto-backed up)
- **Both** protected by `.gitignore` - never committed to git
- **Both** restored together by `./restore_backup.sh`
