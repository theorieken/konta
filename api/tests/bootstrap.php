<?php
declare(strict_types=1);
require dirname(__DIR__) . '/vendor/autoload.php';
require dirname(__DIR__) . '/config/bootstrap.php';
if (!str_contains((string)getenv('DB_DATABASE'), 'konta-test-')) { throw new RuntimeException('Tests require an isolated konta-test- database'); }
