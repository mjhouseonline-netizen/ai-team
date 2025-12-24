#!/bin/bash
# Database and Custom Agent Backup Script
# Run this before updating your site to backup all user data
# This protects:
# - All database files (user accounts, custom agents, chat history)
# - Custom agent icon images
# - All uploaded files

# Create backups directory if it doesn't exist
mkdir -p backups

# Get current date for backup filename
DATE=$(date +%Y%m%d_%H%M%S)

echo "🔒 Starting backup process..."
echo "📅 Backup timestamp: ${DATE}"
echo ""

# ============================================
# BACKUP DATABASES
# ============================================
echo "💾 Backing up databases..."

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

# ============================================
# BACKUP CUSTOM AGENT ICONS
# ============================================
echo "🎨 Backing up custom agent icons..."

if [ -d "static/uploads/agent_icons" ]; then
    # Count files
    file_count=$(find static/uploads/agent_icons -type f 2>/dev/null | wc -l)

    if [ "$file_count" -gt 0 ]; then
        # Create backup directory for this timestamp
        mkdir -p "backups/agent_icons_${DATE}"

        # Copy all agent icons
        cp -r static/uploads/agent_icons/* "backups/agent_icons_${DATE}/" 2>/dev/null

        echo "✅ Backed up ${file_count} custom agent icons -> backups/agent_icons_${DATE}/"
    else
        echo "ℹ️  No custom agent icons to backup"
    fi
else
    echo "ℹ️  No agent_icons directory found (no custom icons uploaded yet)"
fi

echo ""

# ============================================
# BACKUP ALL UPLOADED FILES
# ============================================
echo "📁 Backing up all uploaded files..."

if [ -d "static/uploads" ]; then
    # Create backup of entire uploads directory
    mkdir -p "backups/uploads_${DATE}"

    # Copy recursively, preserving structure
    cp -r static/uploads/* "backups/uploads_${DATE}/" 2>/dev/null

    # Count total files
    total_files=$(find "backups/uploads_${DATE}" -type f 2>/dev/null | wc -l)

    if [ "$total_files" -gt 0 ]; then
        echo "✅ Backed up ${total_files} total uploaded files -> backups/uploads_${DATE}/"
    else
        echo "ℹ️  No uploaded files to backup"
    fi
else
    echo "ℹ️  No uploads directory found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ BACKUP COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Backup location: ./backups/"
echo "🗂️  Backup includes:"
echo "   • Database files (*.db)"
echo "   • Custom agent icons"
echo "   • All uploaded files"
echo ""

# ============================================
# CLEANUP OLD BACKUPS
# ============================================
echo "🧹 Cleaning up old backups (keeping last 10)..."

# Clean old database backups
ls -t backups/*.db 2>/dev/null | tail -n +11 | xargs -r rm

# Clean old icon backups (keep last 10 directories)
ls -td backups/agent_icons_* 2>/dev/null | tail -n +11 | xargs -r rm -rf

# Clean old upload backups (keep last 10 directories)
ls -td backups/uploads_* 2>/dev/null | tail -n +11 | xargs -r rm -rf

echo "✅ Cleanup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 All data is safely backed up!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 TIP: Keep these backups safe before updating your site"
echo ""
