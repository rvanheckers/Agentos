#!/bin/bash
# Git push helper - uses GITHUB_TOKEN from .env
# Usage: ./scripts/git-push.sh [commit message]

# Load .env
if [ -f .env ]; then
    export $(grep -E '^GITHUB_TOKEN=|^GITHUB_USER=|^GITHUB_REPO=' .env | xargs)
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN not found in .env"
    exit 1
fi

# Extract repo path from GITHUB_REPO
REPO_PATH=$(echo "$GITHUB_REPO" | sed 's|https://github.com/||')

# Set remote URL with token
git remote set-url origin "https://${GITHUB_TOKEN}@github.com/${REPO_PATH}"

# If commit message provided, commit first
if [ -n "$1" ]; then
    git add -A
    git commit -m "$1

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
fi

# Push
git push -u origin main

echo "✅ Push complete!"
