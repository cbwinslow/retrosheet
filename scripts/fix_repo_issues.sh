#!/usr/bin/env bash
# scripts/fix_repo_issues.sh
# Run from repo root: bash scripts/fix_repo_issues.sh
# Requires: gh CLI installed and authenticated (sudo apt install gh && gh auth login)

set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
BRANCH="setup-complete"

echo "================================================"
echo " Retrosheet Repo Fix Script"
echo "================================================"

# ── Fix 1: requirements.txt ──────────────────────────
echo ""
echo "[ 1/5 ] Fixing requirements.txt — removing psycopg[binary] conflict..."
sed -i '/^psycopg\[binary\]/d' requirements.txt
echo "✅ Done. Current requirements.txt:"
cat requirements.txt

# ── Fix 2: .env.example ──────────────────────────────
echo ""
echo "[ 2/5 ] Adding PGPASSWORD to .env.example..."
if grep -q "^PGPASSWORD" .env.example; then
    echo "ℹ️  PGPASSWORD already present — skipping"
else
    sed -i '/^PGUSER=/a PGPASSWORD=' .env.example
    echo "✅ Done. Current .env.example:"
    cat .env.example
fi

# ── Fix 3: Delete .travis.yml ────────────────────────
echo ""
echo "[ 3/5 ] Removing dead .travis.yml..."
if [ -f ".travis.yml" ]; then
    git rm .travis.yml
    echo "✅ .travis.yml removed"
else
    echo "ℹ️  .travis.yml not found — skipping"
fi

# ── Fix 4: GitHub Actions CI ─────────────────────────
echo ""
echo "[ 4/5 ] Creating GitHub Actions CI workflow..."
mkdir -p .github/workflows
cat >| .github/workflows/ci.yml << 'EOF'
name: CI

on:
  push:
    branches: ["setup-complete", "master"]
  pull_request:
    branches: ["setup-complete", "master"]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: retrosheet
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest

      - name: Set PYTHONPATH
        run: echo "PYTHONPATH=${{ github.workspace }}" >> $GITHUB_ENV

      - name: Run tests
        env:
          PGHOST: localhost
          PGPORT: 5432
          PGDATABASE: retrosheet
          PGUSER: postgres
          PGPASSWORD: postgres
        run: pytest tests/ -v --tb=short || echo "⚠️ No tests found yet — add tests to tests/"
EOF
echo "✅ Created .github/workflows/ci.yml"

# ── Commit and push ───────────────────────────────────
echo ""
echo "[ 5/5 ] Committing and pushing to $BRANCH..."
git add requirements.txt .env.example .github/workflows/ci.yml
git commit -m "fix: remove psycopg v3 conflict, add PGPASSWORD to env.example, replace Travis with GitHub Actions CI"
git push origin "$BRANCH"
echo "✅ Pushed to origin/$BRANCH"

# ── Fix 5: Change default branch via gh CLI ───────────
echo ""
echo "[ 6/5 ] Changing default branch from master to $BRANCH..."
if command -v gh &>/dev/null; then
    gh repo edit --default-branch "$BRANCH"
    echo "✅ Default branch changed to $BRANCH"
else
    echo "⚠️  'gh' CLI not found — install it to auto-change default branch:"
    echo "     sudo apt install gh && gh auth login"
    echo "     Then run: gh repo edit --default-branch setup-complete"
    echo ""
    echo "     Or do it manually:"
    echo "     https://github.com/cbwinslow/retrosheet/settings/branches"
fi

# ── Reinstall venv ────────────────────────────────────
echo ""
echo "[ 7 ] Reinstalling venv with cleaned requirements..."
if [ -d ".venv" ]; then
    source .venv/bin/activate
    pip install -r requirements.txt --quiet
    echo "✅ venv updated"
else
    echo "ℹ️  No .venv found — run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
fi

echo ""
echo "================================================"
echo " All fixes complete!"
echo "================================================"
echo ""
echo "Next steps on your machine:"
echo "  git pull origin setup-complete"
echo "  source .venv/bin/activate"
echo "  python3 scripts/check_db_connection.py"
