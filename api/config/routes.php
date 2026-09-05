<?php
declare(strict_types=1);
use Cake\Routing\RouteBuilder;
return function (RouteBuilder $routes): void {
    $routes->connect('/health', ['controller' => 'System', 'action' => 'health'])->setMethods(['GET']);
    $routes->scope('/v1', function (RouteBuilder $r): void {
        foreach (['register', 'login', 'forgot', 'reset', 'verify', 'resend', 'logout'] as $action) {
            $r->connect('/auth/' . $action, ['controller' => 'Auth', 'action' => $action])->setMethods(['POST']);
        }
        $r->connect('/me', ['controller' => 'Auth', 'action' => 'profile'])->setMethods(['PATCH']);
        $r->connect('/me', ['controller' => 'Auth', 'action' => 'deleteAccount'])->setMethods(['DELETE']);
        $r->connect('/bootstrap', ['controller' => 'System', 'action' => 'bootstrap'])->setMethods(['GET']);
        $r->connect('/devices', ['controller' => 'System', 'action' => 'device'])->setMethods(['POST', 'DELETE']);
        $r->connect('/notifications/{id}', ['controller' => 'System', 'action' => 'read'])->setPass(['id'])->setMethods(['POST']);
        $r->connect('/invitations/{id}', ['controller' => 'Households', 'action' => 'respond'])->setPass(['id'])->setMethods(['POST']);
        $r->connect('/households', ['controller' => 'Households', 'action' => 'create'])->setMethods(['POST']);
        $r->connect('/households/{household}', ['controller' => 'Households', 'action' => 'update'])->setPass(['household'])->setMethods(['PATCH']);
        $r->connect('/households/{household}', ['controller' => 'Households', 'action' => 'delete'])->setPass(['household'])->setMethods(['DELETE']);
        foreach (['snapshot' => ['GET'], 'invitations' => ['POST'], 'transfer' => ['POST']] as $action => $methods) {
            $r->connect('/households/{household}/' . $action, ['controller' => 'Households', 'action' => $action])->setPass(['household'])->setMethods($methods);
        }
        $r->connect('/households/{household}/members/{id}', ['controller' => 'Households', 'action' => 'removeMember'])->setPass(['household', 'id'])->setMethods(['DELETE']);
        $r->connect('/households/{household}/invitations/{id}', ['controller' => 'Households', 'action' => 'revoke'])->setPass(['household', 'id'])->setMethods(['DELETE']);
        $r->connect('/households/{household}/records/{kind}/{id}', ['controller' => 'Records', 'action' => 'save'])->setPass(['household', 'kind', 'id'])->setMethods(['PUT']);
        $r->connect('/households/{household}/records/{id}', ['controller' => 'Records', 'action' => 'delete'])->setPass(['household', 'id'])->setMethods(['DELETE']);
        $r->connect('/households/{household}/uploads', ['controller' => 'Records', 'action' => 'upload'])->setPass(['household'])->setMethods(['POST']);
        $r->connect('/households/{household}/uploads/{id}', ['controller' => 'Records', 'action' => 'download'])->setPass(['household', 'id'])->setMethods(['GET']);
        $r->connect('/households/{household}/classify', ['controller' => 'Records', 'action' => 'classify'])->setPass(['household'])->setMethods(['POST']);
    });
};
