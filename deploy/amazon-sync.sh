#!/bin/sh
set -eu
TOKEN="$(cat "$HOME/private/sync-endpoint-token.txt")"
curl -fsS -X POST -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/json" https://kitchenfindsfavorites.com/api-daily-sync.php
