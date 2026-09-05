<?php
declare(strict_types=1);
namespace App\Controller;
use Cake\Controller\Controller;
use Cake\Http\Response;
use App\Service\{Store, Auth, ApiException};
class AppController extends Controller
{
    protected Store $store;
    public function initialize(): void { parent::initialize(); $this->autoRender = false; $this->store = new Store(); }
    protected function json(mixed $value = ['ok' => true], int $status = 200): Response { return $this->response->withStatus($status)->withType('application/json')->withStringBody(Store::json($value)); }
    protected function user(): array { return (new Auth($this->store))->authenticate($this->request->getHeaderLine('Authorization')); }
    protected function data(): array { $data = $this->request->getData(); if (!is_array($data)) { throw new ApiException('JSON-Objekt erwartet.', 400); } return $data; }
    protected function throttle(string $scope, int $max = 10, int $window = 900): void { $this->store->limit($scope . ':' . $this->request->clientIp(), $max, $window); }
}
