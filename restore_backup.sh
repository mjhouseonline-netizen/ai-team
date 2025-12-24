#!/bin/bash
# Restore Backup Script
# Use this to restore your data from a previous backup

echo "🔄 BACKUP RESTORE UTILITY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if backups directory exists
if [ ! -d "backups" ]; then
    echo "❌ Error: No backups directory found!"
    echo "   Please ensure you have run backup_database.sh first"
    exit 1
fi

# List available backups
echo "📋 Available database backups:"
echo ""
ls -lht backups/*.db 2>/dev/null | head -10 | awk '{print "   " $9 " (" $6 " " $7 " " $8 ")"}'

echo ""
echo "📋 Available agent icon backups:"
echo ""
ls -dt backups/agent_icons_* 2>/dev/null | head -10 | while read dir; do
    count=$(find "$dir" -type f 2>/dev/null | wc -l)
    timestamp=$(basename "$dir" | sed 's/agent_icons_//')
    echo "   $dir ($count files)"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Prompt for backup selection
read -p "Enter backup timestamp (format: YYYYMMDD_HHMMSS) or 'latest' for most recent: " BACKUP_TIME

if [ "$BACKUP_TIME" = "latest" ]; then
    # Find most recent backup
    LATEST_DB=$(ls -t backups/*.db 2>/dev/null | head -1)
    if [ -n "$LATEST_DB" ]; then
        BACKUP_TIME=$(basename "$LATEST_DB" | sed 's/.*_\([0-9]*_[0-9]*\)\.db/\1/')
        echo "🔍 Using latest backup: $BACKUP_TIME"
    else
        echo "❌ No backups found!"
        exit 1
    fi
fi

echo ""
echo "⚠️  WARNING: This will overwrite current data!"
echo ""
read -p "Are you sure you want to restore from backup $BACKUP_TIME? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Restore cancelled"
    exit 0
fi

echo ""
echo "🔄 Starting restore process..."
echo ""

# ============================================
# RESTORE DATABASE
# ============================================
echo "💾 Restoring database..."

if [ -f "backups/ai_team_${BACKUP_TIME}.db" ]; then
    # Create safety backup of current database
    if [ -f "ai_team.db" ]; then
        cp ai_team.db "ai_team.db.pre-restore.backup"
        echo "🔒 Created safety backup: ai_team.db.pre-restore.backup"
    fi

    # Restore database
    cp "backups/ai_team_${BACKUP_TIME}.db" ai_team.db
    echo "✅ Restored database: backups/ai_team_${BACKUP_TIME}.db -> ai_team.db"
else
    echo "⚠️  Database backup not found for timestamp: $BACKUP_TIME"
fi

echo ""

# ============================================
# RESTORE CUSTOM AGENT ICONS
# ============================================
echo "🎨 Restoring custom agent icons..."

if [ -d "backups/agent_icons_${BACKUP_TIME}" ]; then
    # Create directory if it doesn't exist
    mkdir -p static/uploads/agent_icons

    # Create safety backup of current icons
    if [ -d "static/uploads/agent_icons" ] && [ "$(ls -A static/uploads/agent_icons 2>/dev/null)" ]; then
        SAFETY_BACKUP="backups/agent_icons_pre-restore_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$SAFETY_BACKUP"
        cp -r static/uploads/agent_icons/* "$SAFETY_BACKUP/" 2>/dev/null
        echo "🔒 Created safety backup: $SAFETY_BACKUP"
    fi

    # Restore icons
    cp -r backups/agent_icons_${BACKUP_TIME}/* static/uploads/agent_icons/ 2>/dev/null

    icon_count=$(find static/uploads/agent_icons -type f 2>/dev/null | wc -l)
    echo "✅ Restored ${icon_count} custom agent icons"
else
    echo "ℹ️  No agent icons backup found for timestamp: $BACKUP_TIME"
fi

echo ""

# ============================================
# RESTORE ALL UPLOADS
# ============================================
echo "📁 Restoring all uploaded files..."

if [ -d "backups/uploads_${BACKUP_TIME}" ]; then
    # Create directory if it doesn't exist
    mkdir -p static/uploads

    # Restore all uploads
    cp -r backups/uploads_${BACKUP_TIME}/* static/uploads/ 2>/dev/null

    total_files=$(find static/uploads -type f 2>/dev/null | wc -l)
    echo "✅ Restored ${total_files} uploaded files"
else
    echo "ℹ️  No uploads backup found for timestamp: $BACKUP_TIME"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ RESTORE COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Restored from: backups/*_${BACKUP_TIME}.*"
echo "🔒 Safety backups created with 'pre-restore' prefix"
echo ""
echo "💡 Next steps:"
echo "   1. Restart your application"
echo "   2. Verify custom agents are showing correctly"
echo "   3. Check that custom agent icons display properly"
echo ""
echo "⚠️  If anything went wrong, safety backups are in ./backups/"
echo ""
