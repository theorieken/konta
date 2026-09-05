#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
KONTA_PHP="${KONTA_PHP:-php}"
"$KONTA_PHP" -r 'if (version_compare(PHP_VERSION, "8.3.0", "<")) { fwrite(STDERR, "Konta requires PHP 8.3 or newer. Set KONTA_PHP to that executable.\n"); exit(1); }'
if [ ! -f vendor/autoload.php ]; then "$KONTA_PHP" "$(command -v composer)" install --no-interaction --no-scripts; fi
mkdir -p storage/uploads storage/mail tmp logs
"$KONTA_PHP" bin/cake.php migrations migrate --no-lock
exec "$KONTA_PHP" -d upload_max_filesize=10M -d post_max_size=12M -d max_execution_time=120 -S "127.0.0.1:${KONTA_PORT:-8765}" -t webroot webroot/index.php
