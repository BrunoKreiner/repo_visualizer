#!/bin/bash
# PreToolUse hook: Block dangerous shell commands
# Generalizable to any repo — prevents common destructive operations
#
# Receives JSON on stdin with tool_input.command
# Exit 0 = allow, Exit 2 = block

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Block rm -rf on important directories
if echo "$COMMAND" | grep -qE 'rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|--force\s+)*(\/|~|\$HOME|\.git|src|tests|\.claude)'; then
    echo "Blocked: destructive rm on protected path. Use trash or be more specific." >&2
    exit 2
fi

# Block force push
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*(-f|--force)'; then
    echo "Blocked: force push is not allowed. Use --force-with-lease if needed." >&2
    exit 2
fi

# Block push to main/master without explicit intent
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*\b(main|master)\b'; then
    echo "Blocked: direct push to main/master. Use a feature branch." >&2
    exit 2
fi

# Block git reset --hard
if echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard'; then
    echo "Blocked: git reset --hard can lose work. Use git stash or be specific." >&2
    exit 2
fi

# Block dropping database tables
if echo "$COMMAND" | grep -qiE '(DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE)'; then
    echo "Blocked: destructive database operation." >&2
    exit 2
fi

exit 0
