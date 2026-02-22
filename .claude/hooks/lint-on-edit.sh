#!/bin/bash
# PostToolUse hook: Auto-run ruff format + check after file edits
# Works for any Python project with ruff configured in pyproject.toml
#
# Receives JSON on stdin with tool_input.file_path
# Exit 0 = success (continue), Exit 2 = blocking error

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only process Python files
if [[ -z "$FILE_PATH" ]] || [[ "$FILE_PATH" != *.py ]]; then
    exit 0
fi

# Only process files that exist (might have been deleted)
if [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# Auto-format the file
ruff format "$FILE_PATH" 2>/dev/null

# Run lint check and report issues back to Claude
LINT_OUTPUT=$(ruff check "$FILE_PATH" 2>&1)
LINT_EXIT=$?

if [[ $LINT_EXIT -ne 0 ]]; then
    # Report lint issues as JSON so Claude sees them and can fix
    jq -n --arg ctx "Ruff lint issues found in $FILE_PATH:\n$LINT_OUTPUT\nPlease fix these issues." '{
        hookSpecificOutput: {
            hookEventName: "PostToolUse",
            additionalContext: $ctx
        }
    }'
fi

exit 0
