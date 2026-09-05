#!/usr/bin/env sh
set -eu
mkdir -p storage/uploads storage/mail tmp logs
chown -R www-data:www-data storage tmp logs
su -s /bin/sh www-data -c 'php bin/cake.php migrations migrate --no-lock'
exec "$@"
