<?php
declare(strict_types=1);

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);

const PUBLIC_PAGES = [
    '/' => 'index.html',
    '/datenschutz' => 'datenschutz.html',
    '/impressum' => 'impressum.html',
    '/support' => 'support.html',
];

const PUBLIC_ASSETS = [
    '/site/app-preview.webp' => ['app-preview.webp', 'image/webp; charset=binary'],
    '/site/icon.png' => ['icon.png', 'image/png; charset=binary'],
    '/site/site.css' => ['site.css', 'text/css; charset=UTF-8'],
    '/site/support.js' => ['support.js', 'text/javascript; charset=UTF-8'],
];

if (isset(PUBLIC_PAGES[$path])) {
    header('Content-Type: text/html; charset=UTF-8');
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: no-referrer');
    header("Content-Security-Policy: default-src 'self'; connect-src 'self'; form-action 'self'; img-src 'self'; script-src 'self'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'");
    readfile(__DIR__ . '/api/webroot/site/' . PUBLIC_PAGES[$path]);
    exit;
}

if (isset(PUBLIC_ASSETS[$path])) {
    [$file, $type] = PUBLIC_ASSETS[$path];
    header('Content-Type: ' . $type);
    header('Cache-Control: public, max-age=86400');
    header('X-Content-Type-Options: nosniff');
    readfile(__DIR__ . '/api/webroot/site/' . $file);
    exit;
}

require __DIR__ . '/api/webroot/index.php';
