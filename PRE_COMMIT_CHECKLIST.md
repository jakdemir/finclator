# Pre-Commit Checklist - MUST READ BEFORE `git push`

**⚠️ CRITICAL: Review this before pushing to GitHub!**

---

## ✅ Files That MUST BE IGNORED (Already in .gitignore)

### 🔐 Sensitive Data
- [ ] `.env` - Contains API keys (X_API_BEARER_TOKEN, ALPHAVANTAGE_API_KEY, HUGGINGFACE_API_KEY)
- [ ] `.env.local` - Local overrides
- [ ] `.env.*.local` - Environment-specific configs
- [ ] Any backup `.sql` files with production data

### 💾 Cache & Build Artifacts
- [ ] `.cache/` - API response cache (may contain sensitive data)
- [ ] `__pycache__/` - Python bytecode
- [ ] `.venv/` or `venv/` - Virtual environment
- [ ] `.pytest_cache/` - Test cache
- [ ] `.mypy_cache/` - Type checker cache
- [ ] `.ruff_cache/` - Linter cache

### 🗄️ Database Files
- [ ] `*.db` - SQLite databases
- [ ] `*.sqlite` or `*.sqlite3` - Database files
- [ ] `backup*.sql` - Database backups
- [ ] `*.dump` - Database dumps

### 📝 Logs & Temp Files
- [ ] `*.log` - Log files
- [ ] `logs/` - Log directory
- [ ] `*.tmp` - Temporary files
- [ ] `*.bak` - Backup files

---

## ✅ Verification Commands

Run these before committing:

### 1. Check Git Status
```bash
git status --ignored
```
**Look for**: `.env`, `.cache/`, `.venv/` should appear under "Ignored files"

### 2. Search for Hardcoded Secrets
```bash
# Search for potential API keys in code
grep -r "sk-" src/ scripts/ || echo "✅ No OpenAI-style keys"
grep -r "Bearer [A-Za-z0-9]" src/ scripts/ || echo "✅ No bearer tokens"
grep -r "ALPHAVANTAGE_API_KEY.*=" src/ scripts/ || echo "✅ No hardcoded Alpha Vantage keys"
```

### 3. Check .env is Ignored
```bash
git check-ignore .env
```
**Expected output**: `.env` (confirms it's ignored)

### 4. Verify No Large Files
```bash
find . -type f -size +10M | grep -v ".venv" | grep -v ".cache" | head -10
```
**Expected**: No large files (except maybe in ignored directories)

---

## ✅ Files That SHOULD BE COMMITTED

### 📦 Core Application
- [x] `src/` - All source code
- [x] `scripts/` - Utility scripts
- [x] `migrations/` - Alembic migrations
- [x] `data/` - Seed data (finance_schools.json, influencers.json)

### ⚙️ Configuration
- [x] `pyproject.toml` - Python dependencies
- [x] `alembic.ini` - Migration config (no secrets)
- [x] `render.yaml` - Deployment config (no secrets)
- [x] `.gitignore` - Git ignore rules
- [x] `.env.example` - Template for environment variables (NO ACTUAL KEYS)

### 📚 Documentation
- [x] `README.md` - Project overview
- [x] `SETUP.md` - Setup guide
- [x] `docs/` - All documentation
- [x] `PRE_DEPLOYMENT_VALIDATION.md` - Validation report
- [x] `DEPLOYMENT_READY.txt` - Deployment summary
- [x] `TEST_RESULTS.md` - Test reports
- [x] `Q3_2024_TEST_RESULTS.md` - Historical test
- [x] `X_API_INTEGRATION.md` - Integration details

### 📋 Project Management
- [x] `specs/` - Specifications
- [x] `.specify/` - Specify configuration

---

## ⚠️ CRITICAL: Check for Accidental Secrets

### Before Every Commit, Run:
```bash
# 1. Check for .env content in staged files
git diff --cached | grep -i "api_key\|bearer\|secret\|password" && echo "⚠️  WARNING: Potential secret detected!" || echo "✅ No secrets in staged files"

# 2. Verify .env is not staged
git diff --cached --name-only | grep "\.env$" && echo "❌ STOP! .env is staged!" || echo "✅ .env not staged"

# 3. Check for actual API key patterns
git diff --cached | grep -E "[A-Z0-9]{32,}" && echo "⚠️  Long alphanumeric string detected - verify it's not a key" || echo "✅ No suspicious patterns"
```

---

## 🔒 What Your .env Should Look Like

**File: `.env` (NEVER commit this!)**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/finclator

# External API Keys - KEEP SECRET!
X_API_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAyour-actual-token-here
ALPHAVANTAGE_API_KEY=YOUR_ACTUAL_KEY
HUGGINGFACE_API_KEY=hf_YourActualKey

# Optional
LOG_LEVEL=INFO
```

**File: `.env.example` (Safe to commit)**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://localhost/finclator

# External API Keys
X_API_BEARER_TOKEN=your_x_api_bearer_token_here
ALPHAVANTAGE_API_KEY=your_alphavantage_key_here
HUGGINGFACE_API_KEY=your_huggingface_key_here

# Optional
LOG_LEVEL=INFO
```

---

## 🚨 Emergency: Accidentally Committed a Secret?

### If you committed but didn't push:
```bash
# Remove the file from the last commit
git rm --cached .env
git commit --amend -m "Remove .env"
```

### If you already pushed:
1. **Immediately rotate all API keys** in the exposed file
2. Remove from git history:
```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```
3. Force push (⚠️ dangerous!):
```bash
git push origin --force --all
```
4. Tell all collaborators to rebase/clone fresh

**Better approach**: Use [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) or contact GitHub support

---

## ✅ Final Pre-Push Checklist

Before `git push`, confirm:

- [ ] `.env` is NOT in `git status` output
- [ ] `.cache/` is NOT in `git status` output  
- [ ] `.venv/` is NOT in `git status` output
- [ ] No API keys visible in `git diff`
- [ ] No database files (.db, .sqlite) in `git status`
- [ ] All secrets are in environment variables, not code
- [ ] `.env.example` exists and has no real keys
- [ ] `git check-ignore .env` confirms it's ignored
- [ ] Ran validation script: `python scripts/validate_mvp.py` ✅
- [ ] All tests passed: `./scripts/test_all_endpoints.sh` ✅

---

## 🎯 Quick Pre-Commit Script

Create this as `scripts/pre_commit_check.sh`:

```bash
#!/bin/bash
echo "🔍 Pre-Commit Security Check"
echo "======================================"

# Check if .env is being committed
if git diff --cached --name-only | grep -q "\.env$"; then
    echo "❌ ERROR: .env file is staged for commit!"
    echo "   Run: git reset HEAD .env"
    exit 1
fi

# Check for potential secrets in staged changes
if git diff --cached | grep -iE "(api_key|bearer|secret|password).*=.*[A-Za-z0-9]{20,}"; then
    echo "⚠️  WARNING: Potential secret detected in staged changes!"
    echo "   Review your changes carefully"
    read -p "   Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if .cache is being committed
if git diff --cached --name-only | grep -q "\.cache/"; then
    echo "⚠️  WARNING: .cache directory is being committed"
    exit 1
fi

echo "✅ Security check passed"
echo "======================================"
```

Make it executable:
```bash
chmod +x scripts/pre_commit_check.sh
```

Run before every commit:
```bash
./scripts/pre_commit_check.sh && git commit -m "Your message"
```

---

## 📋 Summary

**NEVER commit:**
- ❌ `.env` or any file with actual API keys
- ❌ `.cache/` directory (may contain cached API responses)
- ❌ `.venv/` or any virtual environment
- ❌ Database files (*.db, *.sqlite)
- ❌ Log files (*.log)
- ❌ Any file with actual secrets or credentials

**ALWAYS commit:**
- ✅ All source code (`src/`, `scripts/`, `migrations/`)
- ✅ Configuration templates (`.env.example`, `render.yaml`)
- ✅ Documentation (`docs/`, `README.md`, etc.)
- ✅ Dependency lists (`pyproject.toml`)
- ✅ `.gitignore` file itself

---

**When in doubt, run:**
```bash
git status --ignored
```

If you see sensitive files outside the "Ignored files" section, **DON'T COMMIT!**

---

**Last updated**: 2025-11-15  
**Status**: Ready for safe deployment ✅

