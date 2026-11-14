#!/bin/bash
# Preflight check + launcher for Claude Code on Hugging Face Inference Providers.
# Usage: ./hf-claude.sh [--check-only] [--no-probe] [-- claude args...]
#   --check-only  run checks, don't launch claude
#   --no-probe    skip the live request to each model (no network, no cost)

set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; FAILED=1; }

FAILED=0
CHECK_ONLY=0
PROBE=1
while [ $# -gt 0 ]; do
    case "$1" in
        --check-only) CHECK_ONLY=1; shift ;;
        --no-probe)   PROBE=0; shift ;;
        --)           shift; break ;;
        *)            break ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Hugging Face preflight"

# Load .env without overriding variables already set in the shell
if [ -f "$SCRIPT_DIR/.env" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in ''|\#*) continue ;; esac
        key="${line%%=*}"
        [ -n "${!key+x}" ] && continue
        eval "export $line"
    done < "$SCRIPT_DIR/.env"
    ok "Loaded $SCRIPT_DIR/.env"
else
    warn "No .env found; using shell environment (cp .env.example .env to create one)"
fi

# Token
TOKEN="${ANTHROPIC_AUTH_TOKEN:-${HF_TOKEN:-}}"
if [ -z "$TOKEN" ] || [ "$TOKEN" = "hf_your_token_here" ]; then
    fail "No HF token: set HF_TOKEN (or ANTHROPIC_AUTH_TOKEN) in .env"
else
    export ANTHROPIC_AUTH_TOKEN="$TOKEN"
    case "$TOKEN" in
        hf_*) ok "HF token set (hf_…${TOKEN: -4})" ;;
        *)    warn "Token doesn't start with hf_; check it's a Hugging Face token" ;;
    esac
fi

# Base URL
export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-https://router.huggingface.co}"
if [ "$ANTHROPIC_BASE_URL" = "https://router.huggingface.co" ]; then
    ok "Base URL: $ANTHROPIC_BASE_URL"
else
    warn "Base URL is $ANTHROPIC_BASE_URL (expected https://router.huggingface.co)"
fi

# Auth conflict
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    warn "ANTHROPIC_API_KEY is set; unsetting it for this launch to avoid an auth conflict"
    unset ANTHROPIC_API_KEY
fi

# Model slots
MODELS=()
for var in ANTHROPIC_DEFAULT_OPUS_MODEL ANTHROPIC_DEFAULT_SONNET_MODEL \
           ANTHROPIC_DEFAULT_HAIKU_MODEL CLAUDE_CODE_SUBAGENT_MODEL; do
    val="${!var:-}"
    if [ -z "$val" ]; then
        fail "$var is not set"
    else
        ok "$var = $val"
        case " ${MODELS[*]-} " in *" $val "*) ;; *) MODELS+=("$val") ;; esac
    fi
done

# claude CLI
if command -v claude >/dev/null 2>&1; then
    ok "claude CLI found ($(claude --version 2>/dev/null | head -1))"
else
    fail "claude CLI not on PATH: curl -fsSL https://claude.ai/install.sh | bash"
fi

# Live probe: 1-token request per distinct model
if [ "$PROBE" -eq 1 ] && [ "$FAILED" -eq 0 ]; then
    echo "Probing models (1-token request each)…"
    for model in "${MODELS[@]}"; do
        body=$(curl -sS -m 60 -w '\n%{http_code}' -X POST "$ANTHROPIC_BASE_URL/v1/messages" \
            -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
            -H "content-type: application/json" \
            -H "anthropic-version: 2023-06-01" \
            ${ANTHROPIC_CUSTOM_HEADERS:+-H "$ANTHROPIC_CUSTOM_HEADERS"} \
            -d "{\"model\":\"$model\",\"max_tokens\":1,\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}" 2>&1)
        code="${body##*$'\n'}"
        detail="$(printf '%s' "${body%$'\n'*}" | head -c 200)"
        case "$code" in
            200)     ok "$model responds" ;;
            401|403) fail "$model: token rejected ($code). Check token permissions / billing org" ;;
            400|404|422) fail "$model: not available ($code): $detail" ;;
            000)     fail "$model: could not reach $ANTHROPIC_BASE_URL: $detail" ;;
            *)       fail "$model: HTTP $code: $detail" ;;
        esac
    done
fi

echo ""
if [ "$FAILED" -ne 0 ]; then
    echo -e "${RED}Preflight failed.${NC} Fix the items above and re-run."
    exit 1
fi
echo -e "${GREEN}Preflight passed.${NC}"
[ "$CHECK_ONLY" -eq 1 ] && exit 0
exec claude "$@"
