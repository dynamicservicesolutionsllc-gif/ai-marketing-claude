#!/bin/bash
# Daily automation for Kitchen Finds & Favorites
# Runs on Hostinger via SSH cron: 0 5 * * * /home/username/public_html/daily-automation.sh
#
# Tasks:
# 1. Discover and stage 5 new products from Amazon
# 2. Fetch fresh product photos from Amazon
# 3. Rebuild the site
# 4. Log results

set -euo pipefail

# Configuration
SITE_DIR="$HOME/private"  # Your actual Hostinger setup
LOG_DIR="${SITE_DIR}/logs"
LOG_FILE="${LOG_DIR}/automation-$(date +%Y-%m-%d).log"
ERROR_LOG="${LOG_DIR}/automation-error.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Helper functions
log() {
    echo "[${TIMESTAMP}] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[${TIMESTAMP}] ERROR: $1" | tee -a "$LOG_FILE" "$ERROR_LOG"
}

# Start automation
log "=== Daily Automation Started ==="
cd "$SITE_DIR"

# Load environment variables from .env
if [ -f "${SITE_DIR}/.env" ]; then
    export $(cat "${SITE_DIR}/.env" | grep -v '^#' | xargs)
    log "Loaded environment variables"
else
    log_error ".env file not found at ${SITE_DIR}/.env"
    exit 1
fi

# Task 1: Discover new products
log "--- Task 1: Discovering new products ---"
if python3 discover_products.py >> "$LOG_FILE" 2>&1; then
    log "✓ Product discovery completed"
else
    log_error "Product discovery failed"
fi

# Task 2: Fetch Amazon photos
log "--- Task 2: Fetching Amazon product photos ---"
if python3 fetch_amazon_images.py >> "$LOG_FILE" 2>&1; then
    log "✓ Photo fetch completed"
else
    log_error "Photo fetch failed (continuing anyway)"
fi

# Task 3: Rebuild site
log "--- Task 3: Rebuilding site ---"
if python3 build.py >> "$LOG_FILE" 2>&1; then
    log "✓ Site rebuild completed"
else
    log_error "Site rebuild failed"
    exit 1
fi

# Task 4: Add TikTok pixel
log "--- Task 4: Adding TikTok pixel ---"
if python3 add_tiktok_pixel.py >> "$LOG_FILE" 2>&1; then
    log "✓ TikTok pixel added"
else
    log_error "TikTok pixel script failed (continuing anyway)"
fi

log "=== Daily Automation Completed Successfully ==="
echo "" >> "$LOG_FILE"

exit 0
