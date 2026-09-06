<?php
declare(strict_types=1);
namespace App\Service;

final class Support
{
    private const TOPICS = [
        'allgemein' => 'Allgemeine Frage',
        'konto' => 'Konto und Anmeldung',
        'daten' => 'Daten, Import und Synchronisierung',
        'datenschutz' => 'Datenschutz und Löschung',
        'feedback' => 'Feedback und Idee',
    ];

    public function __construct(private Store $store) {}

    public function submit(array $data): void
    {
        // A filled hidden field marks an automated submission. Return success so bots
        // cannot use the response to tune their payloads.
        if (trim((string)($data['company'] ?? '')) !== '') { return; }

        $name = preg_replace('/[\r\n]+/', ' ', trim((string)($data['name'] ?? ''))) ?? '';
        $email = Auth::email($data['email'] ?? null);
        $topic = $data['topic'] ?? null;
        $message = trim((string)($data['message'] ?? ''));
        if (mb_strlen($name) < 2 || mb_strlen($name) > 100) {
            throw new ApiException('Bitte gib deinen Namen ein (2 bis 100 Zeichen).', 422);
        }
        if (!is_string($topic) || !isset(self::TOPICS[$topic])) {
            throw new ApiException('Bitte wähle ein Thema aus.', 422);
        }
        if (mb_strlen($message) < 20 || mb_strlen($message) > 4000) {
            throw new ApiException('Deine Nachricht muss zwischen 20 und 4.000 Zeichen lang sein.', 422);
        }

        $body = "Neue Support-Anfrage über konta-finance.com\n\n"
            . "Name: {$name}\nE-Mail: {$email}\nThema: " . self::TOPICS[$topic]
            . "\n\nNachricht:\n{$message}\n";
        $recipient = Auth::email(getenv('SUPPORT_EMAIL') ?: 'news@konta-finance.com');
        (new Delivery($this->store))->email($recipient, 'Konta Support: ' . self::TOPICS[$topic], $body);
    }
}
