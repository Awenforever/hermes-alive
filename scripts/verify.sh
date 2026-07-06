#!/bin/bash
# Hermes Alive health check
set -e

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_DIR="${HOOK_DIR:-/opt/data/hooks/hermes-alive}"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }

echo "Hermes Alive Health Check"
echo "========================"
echo ""

# 1. Check hook files deployed
echo "Hook deployment:"
[ -f "$HOOK_DIR/HOOK.yaml" ] && pass "HOOK.yaml" || fail "HOOK.yaml missing"
[ -f "$HOOK_DIR/handler.py" ] && pass "handler.py" || fail "handler.py missing"
[ -f "$HOOK_DIR/proactive_watcher.py" ] && pass "proactive_watcher.py" || fail "proactive_watcher.py missing"
[ -f "$HOOK_DIR/discovery.py" ] && pass "discovery.py" || fail "discovery.py missing"
[ -f "$HOOK_DIR/voice_engine.py" ] && pass "voice_engine.py" || fail "voice_engine.py missing"
echo ""

# 2. Check gateway loaded the hook
echo "Gateway integration:"
if command -v docker &>/dev/null; then
    if docker logs hermes-hermes-1 2>&1 | grep -q "Loaded hook.*hermes-alive"; then
        pass "Hook loaded by gateway"
    else
        fail "Hook NOT loaded — gateway restart needed?"
    fi
else
    echo "  docker not available — skipping gateway check"
fi
echo ""

# 3. Check env vars
echo "Environment:"
vars=(
    HERMES_PROACTIVE_PLATFORM_ENABLED
    HERMES_PROACTIVE_WEIXIN_CHAT_ID
    VOICE_ENABLED
    HERMES_PROACTIVE_LLM_ENABLED
    HERMES_DREAM_ENABLED
    PLAYWRIGHT_BROWSERS_PATH
)
for v in "${vars[@]}"; do
    if grep -q "^${v}=" /opt/data/.env 2>/dev/null; then
        val=$(grep "^${v}=" /opt/data/.env | cut -d= -f2)
        pass "$v=$val"
    else
        fail "$v not set"
    fi
done
echo ""

# 4. Check Python deps
echo "Python dependencies:"
for mod in playwright yaml aiohttp; do
    if /opt/hermes/.venv/bin/python3 -c "import $mod" 2>/dev/null; then
        pass "$mod"
    else
        fail "$mod — run: uv pip install $mod --python /opt/hermes/.venv/bin/python3"
    fi
done
echo ""

# 5. Check Chromium
echo "Playwright browser:"
if [ -d "/opt/data/.playwright-browsers/chromium-"* ]; then
    du -sh /opt/data/.playwright-browsers/ | while read size dir; do
        pass "Chromium installed ($size)"
    done
else
    fail "Chromium not installed"
fi
echo ""

# 6. Check watcher running
echo "Runtime:"
if command -v docker &>/dev/null; then
    if docker logs hermes-hermes-1 2>&1 | grep -q "watcher started"; then
        pass "Watcher started"
    else
        fail "Watcher may not have started yet"
    fi
else
    echo "  docker not available — skipping runtime check"
fi

echo ""
echo "Done."
