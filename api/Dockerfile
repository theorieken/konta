FROM composer:2 AS composer
FROM php:8.4-apache
RUN apt-get update && apt-get install -y --no-install-recommends libicu-dev libonig-dev libsqlite3-dev libcurl4-openssl-dev unzip \
    && docker-php-ext-install intl mbstring pdo_mysql pdo_sqlite curl \
    && a2enmod rewrite headers \
    && rm -rf /var/lib/apt/lists/*
COPY --from=composer /usr/bin/composer /usr/local/bin/composer
WORKDIR /var/www/konta
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-scripts --no-interaction --prefer-dist --no-autoloader
COPY . .
RUN composer dump-autoload --no-dev --classmap-authoritative \
    && mkdir -p storage/uploads storage/mail tmp logs \
    && chown -R www-data:www-data storage tmp logs
COPY docker/apache.conf /etc/apache2/sites-available/000-default.conf
COPY docker/php.ini /usr/local/etc/php/conf.d/konta.ini
COPY docker/entrypoint.sh /usr/local/bin/konta-entrypoint
ENTRYPOINT ["konta-entrypoint"]
CMD ["apache2-foreground"]
