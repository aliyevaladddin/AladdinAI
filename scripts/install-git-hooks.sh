#!/bin/sh
# Install repo git hooks (run once per clone):
#   scripts/install-git-hooks.sh
set -e
HOOKS="$(git rev-parse --git-path hooks)"
cp "$(dirname "$0")/hooks/pre-commit" "$HOOKS/pre-commit"
chmod +x "$HOOKS/pre-commit"
echo "✓ pre-commit hook installed — direct commits to 'main' are now blocked"
