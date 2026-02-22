#!/bin/bash
# Stop hook: Verify tests pass before Claude finishes
# Generalizable — auto-detects test runner (pytest, npm test, go test, cargo test)
#
# Receives JSON on stdin with stop_hook_active and last_assistant_message
# Exit 0 with decision=block JSON = continue working
# Exit 0 with no output = allow stop

INPUT=$(cat)

# Prevent infinite loops: if a stop hook already triggered, let Claude stop
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
if [[ "$STOP_HOOK_ACTIVE" == "true" ]]; then
    exit 0
fi

# Auto-detect test runner and run tests
TEST_EXIT=0
TEST_OUTPUT=""

if [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -f "setup.cfg" ]]; then
    # Python project
    if [[ -d "tests" ]] || [[ -d "test" ]]; then
        TEST_OUTPUT=$(python -m pytest --tb=short -q 2>&1)
        TEST_EXIT=$?
    else
        # No test directory — skip
        exit 0
    fi
elif [[ -f "package.json" ]]; then
    # Node.js project
    if jq -e '.scripts.test' package.json >/dev/null 2>&1; then
        TEST_OUTPUT=$(npm test 2>&1)
        TEST_EXIT=$?
    else
        exit 0
    fi
elif [[ -f "go.mod" ]]; then
    TEST_OUTPUT=$(go test ./... 2>&1)
    TEST_EXIT=$?
elif [[ -f "Cargo.toml" ]]; then
    TEST_OUTPUT=$(cargo test 2>&1)
    TEST_EXIT=$?
else
    # No recognized project type — allow stop
    exit 0
fi

if [[ $TEST_EXIT -ne 0 ]]; then
    # Tests failed — tell Claude to keep working
    jq -n --arg reason "Tests are failing. Please fix before finishing:\n$TEST_OUTPUT" '{
        decision: "block",
        reason: $reason
    }'
else
    # Tests passed — allow Claude to stop
    exit 0
fi
