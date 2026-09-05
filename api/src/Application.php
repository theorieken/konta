<?php
declare(strict_types=1);
namespace App;
use Cake\Http\BaseApplication;
use Cake\Http\MiddlewareQueue;
use Cake\Http\Middleware\BodyParserMiddleware;
use Cake\Routing\Middleware\RoutingMiddleware;
use App\Middleware\ApiErrorMiddleware;
final class Application extends BaseApplication
{
    public function bootstrap(): void { parent::bootstrap(); $this->addPlugin('Migrations'); }
    public function middleware(MiddlewareQueue $queue): MiddlewareQueue
    {
        // Bearer credentials only: no cookie authentication or browser UI.
        return $queue->add(new ApiErrorMiddleware())->add(new RoutingMiddleware($this))->add(new BodyParserMiddleware());
    }
}
