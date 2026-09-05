<?php
declare(strict_types=1);
require __DIR__ . '/paths.php';
require CORE_PATH . 'config/bootstrap.php';
require CAKE . 'functions.php';
use Cake\Core\Configure;
use Cake\Core\Configure\Engine\PhpConfig;
use Cake\Datasource\ConnectionManager;
use Cake\Log\Log;
use Cake\Mailer\TransportFactory;
if (file_exists(ROOT . '/.env')) {
    (new \josegonzalez\Dotenv\Loader([ROOT . '/.env']))->parse()->putenv(false);
}
date_default_timezone_set('UTC');
mb_internal_encoding('UTF-8');
Configure::config('default', new PhpConfig());
Configure::load('app', 'default', false);
ConnectionManager::setConfig(Configure::consume('Datasources'));
TransportFactory::setConfig(Configure::consume('EmailTransport'));
Log::setConfig('default', ['className' => 'File', 'path' => LOGS, 'file' => 'error', 'levels' => ['error', 'warning']]);
