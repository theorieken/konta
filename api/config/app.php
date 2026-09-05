<?php
declare(strict_types=1);
use Cake\Database\Driver\Sqlite;
use Cake\Database\Driver\Mysql;
$mysql = getenv('DB_DRIVER') === 'mysql';
return [
    'debug' => false,
    'App' => ['namespace' => 'App', 'encoding' => 'UTF-8', 'defaultLocale' => 'de_DE', 'defaultTimezone' => 'UTC', 'fullBaseUrl' => getenv('APP_URL') ?: 'http://localhost:8765', 'paths' => ['plugins' => [ROOT . '/plugins/'], 'templates' => [ROOT . '/templates/'], 'locales' => [RESOURCES . 'locales/']]],
    'Datasources' => ['default' => [
        'className' => 'Cake\Database\Connection', 'driver' => $mysql ? Mysql::class : Sqlite::class,
        'host' => getenv('DB_HOST') ?: 'localhost', 'username' => getenv('DB_USERNAME') ?: 'konta',
        'password' => getenv('DB_PASSWORD') ?: '', 'database' => getenv('DB_DATABASE') ?: ($mysql ? 'konta' : ROOT . '/storage/konta.sqlite'),
        'encoding' => 'utf8mb4', 'timezone' => 'UTC', 'cacheMetadata' => false,
        'init' => $mysql ? [] : ['PRAGMA foreign_keys = ON', 'PRAGMA busy_timeout = 5000', 'PRAGMA journal_mode = WAL'],
    ]],
    'EmailTransport' => ['default' => [
        'className' => 'Smtp', 'host' => getenv('SMTP_HOST') ?: 'localhost', 'port' => (int)(getenv('SMTP_PORT') ?: 587),
        'username' => getenv('SMTP_USERNAME') ?: null, 'password' => getenv('SMTP_PASSWORD') ?: null,
        'tls' => getenv('SMTP_TLS') !== 'false', 'timeout' => 15,
    ]],
];
