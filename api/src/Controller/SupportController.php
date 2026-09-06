<?php
declare(strict_types=1);
namespace App\Controller;

use App\Service\{Delivery, Support};

final class SupportController extends AppController
{
    public function contact()
    {
        $this->throttle('support-contact', 5, 3600);
        (new Support($this->store))->submit($this->data());
        (new Delivery($this->store))->flush();

        if (!$this->request->accepts('application/json')) {
            return $this->response->withStatus(303)->withHeader('Location', '/support?gesendet=1');
        }
        return $this->json(['ok' => true], 202);
    }
}
