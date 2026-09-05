<?php
declare(strict_types=1);
namespace App\Middleware;
use Cake\Http\Response;
use Cake\Log\Log;
use Psr\Http\Message\ResponseInterface;
use Psr\Http\Message\ServerRequestInterface;
use Psr\Http\Server\MiddlewareInterface;
use Psr\Http\Server\RequestHandlerInterface;
use App\Service\ApiException;
final class ApiErrorMiddleware implements MiddlewareInterface
{
    public function process(ServerRequestInterface $request, RequestHandlerInterface $handler): ResponseInterface
    {
        try { $response = $handler->handle($request); }
        catch (\Throwable $error) {
            $status = $error instanceof ApiException ? $error->getCode() : (in_array($error->getCode(), [400, 404, 405], true) ? $error->getCode() : 500);
            if ($status === 500) { Log::error($error::class . ': ' . $error->getMessage()); }
            $response = (new Response())->withStatus($status)->withType('application/json')->withStringBody(json_encode([
                'detail' => $status === 500 ? 'Der Server konnte die Anfrage nicht verarbeiten.' : $error->getMessage(),
            ], JSON_THROW_ON_ERROR));
        }
        return $response->withHeader('Cache-Control', 'no-store')->withHeader('X-Content-Type-Options', 'nosniff');
    }
}
