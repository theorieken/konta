#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

KONTA_PHP="${KONTA_PHP:-php}"
KONTA_COMPOSER="${KONTA_COMPOSER:-composer}"

if [ ! -f .env ]; then
    printf '%s\n' "Missing api/.env. Copy .env.example once and add the production secrets." >&2
    exit 1
fi

"$KONTA_PHP" -r '
if (version_compare(PHP_VERSION, "8.3.0", "<")) {
    fwrite(STDERR, "Konta requires PHP 8.3 or newer.\n");
    exit(1);
}
$required = ["curl", "intl", "mbstring", "openssl", "pdo_mysql"];
$missing = array_values(array_filter($required, static fn(string $extension): bool => !extension_loaded($extension)));
if ($missing) {
    fwrite(STDERR, "Missing PHP extensions: " . implode(", ", $missing) . "\n");
    exit(1);
}
'

"$KONTA_COMPOSER" install --no-dev --no-interaction --no-scripts --optimize-autoloader
mkdir -p storage/uploads storage/mail tmp logs
chmod 700 storage storage/uploads storage/mail tmp logs
"$KONTA_PHP" bin/cake.php migrations migrate --no-lock
"$KONTA_PHP" bin/cake.php maintenance

printf '%s\n' "Konta API deployment completed."
