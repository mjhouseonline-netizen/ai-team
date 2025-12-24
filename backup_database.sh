#!/bin/bash
# Database Backup Script
# Run this before updating your site to backup all user data

# Create backups directory if it doesn't exist
mkdir -p backups

# Get current date for backup filename
DATE=$(date +%Y%m%d_%H%M%S)

# Backup all database files
echo "🔒 Backing up databases..."

if [ -f "ai_team.db" ]; then
    cp ai_team.db "backups/ai_team_${DATE}.db"
    echo "✅ Backed up: ai_team.db -> backups/ai_team_${DATE}.db"
fi

if [ -f "users.db" ]; then
    cp users.db "backups/users_${DATE}.db"
    echo "✅ Backed up: users.db -> backups/users_${DATE}.db"
fi

if [ -f "ai_team_platform.db" ]; then
    cp ai_team_platform.db "backups/ai_team_platform_${DATE}.db"
    echo "✅ Backed up: ai_team_platform.db -> backups/ai_team_platform_${DATE}.db"
fi

# Backup from /data if it exists
if [ -d "/data" ]; then
    if [ -f "/data/ai_team.db" ]; then
        cp /data/ai_team.db "backups/data_ai_team_${DATE}.db"
        echo "✅ Backed up: /data/ai_team.db -> backups/data_ai_team_${DATE}.db"
    fi
fi

echo ""
echo "✅ Backup complete! Files saved in ./backups/"
echo ""

# Keep only last 10 backups to save space
echo "🧹 Cleaning up old backups (keeping last 10)..."
ls -t backups/*.db 2>/dev/null | tail -n +11 | xargs -r rm
echo "✅ Cleanup complete!"
