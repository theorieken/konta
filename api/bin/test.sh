#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
KONTA_PHP="${KONTA_PHP:-php}"
KONTA_TEST_DB="$(mktemp -t konta-test-XXXXXX)"
trap 'rm -f "$KONTA_TEST_DB"' EXIT
export DB_DRIVER=sqlite DB_DATABASE="$KONTA_TEST_DB" MAIL_TRANSPORT=file
"$KONTA_PHP" bin/cake.php migrations migrate --no-lock
"$KONTA_PHP" vendor/bin/phpunit
