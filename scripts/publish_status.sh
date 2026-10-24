#!/usr/bin/env bash
# Publish status/status.json to the 'status' branch on GitHub, where the project
# website reads it. Uses git plumbing (hash-object, mktree, commit-tree), so the
# code checkout, its branch and its index are never touched.
set -euo pipefail
cd "$(dirname "$0")/.."

FILE=status/status.json
BRANCH=status

if [ ! -f "$FILE" ]; then
    echo "No $FILE, nothing to publish"
    exit 0
fi

# Latest published commit, if the branch exists yet
git fetch -q origin "$BRANCH" 2>/dev/null || true
parent=$(git rev-parse -q --verify "refs/remotes/origin/$BRANCH" || true)

# Build a one-file tree: status.json at the root of the branch
blob=$(git hash-object -w "$FILE")
tree=$(printf '100644 blob %s\tstatus.json\n' "$blob" | git mktree)

if [ -n "$parent" ] && [ "$(git rev-parse "$parent^{tree}")" = "$tree" ]; then
    echo "Status unchanged, nothing to publish"
    exit 0
fi

if [ -n "$parent" ]; then
    commit=$(git commit-tree "$tree" -p "$parent" -m "Pipeline status $(date -Is)")
else
    commit=$(git commit-tree "$tree" -m "Pipeline status $(date -Is)")
fi
git push -q origin "$commit:refs/heads/$BRANCH"
echo "Published status to branch '$BRANCH' ($commit)"
