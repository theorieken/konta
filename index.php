<?php
declare(strict_types=1);

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);

if ($path === '/') {
    header('Content-Type: text/html; charset=UTF-8');
    readfile(__DIR__ . '/api/webroot/site/index.html');
    exit;
}

if ($path === '/site/icon.png') {
    header('Content-Type: image/png');
    header('Cache-Control: public, max-age=86400');
    readfile(__DIR__ . '/api/webroot/site/icon.png');
    exit;
}

require __DIR__ . '/api/webroot/index.php';
