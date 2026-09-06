<?php
declare(strict_types=1);
namespace App\Service;
use Cake\Mailer\Mailer;
use Cake\Log\Log;

final class Delivery
{
    public function __construct(private Store $store) {}
    private function enqueue(string $channel, string $recipient, array $payload): void
    {
        $this->store->db->insert('outbox', ['id' => Store::id(), 'channel' => $channel, 'recipient' => $recipient, 'payload' => Store::json($payload), 'attempts' => 0, 'available_at' => time(), 'locked_until' => 0]);
    }
    public function email(string $email, string $subject, string $body, ?string $actionLabel = null, ?string $actionURL = null): void
    {
        $html = self::emailHTML($subject, $body, $actionLabel, $actionURL);
        if ($actionLabel !== null && $actionURL !== null) {
            $body .= "\n\n{$actionLabel}: {$actionURL}";
        }
        $this->enqueue('email', $email, compact('subject', 'body', 'html'));
    }
    public function notify(string $user, array $payload): void
    {
        $this->store->db->insert('notifications', ['id' => Store::id(), 'user_id' => $user, 'payload' => Store::json($payload), 'is_read' => false, 'created_at' => time()]);
        $this->enqueue('push', $user, $payload);
    }
    public function changed(string $household, string $actor): void
    {
        foreach ($this->store->rows('SELECT user_id FROM memberships WHERE household_id = ?', [$household]) as $member) {
            // Include the actor: their other devices need the same invalidation.
            $this->enqueue('push', $member['user_id'], ['householdID' => $household, 'silent' => true]);
        }
    }
    public function flush(int $limit = 20): int
    {
        $sent = 0;
        $rows = $this->store->rows('SELECT * FROM outbox WHERE sent_at IS NULL AND attempts < 12 AND available_at <= ? AND locked_until < ? ORDER BY available_at LIMIT ' . min(100, max(1, $limit)), [time(), time()]);
        foreach ($rows as $row) {
            if ($this->store->db->execute('UPDATE outbox SET locked_until = ? WHERE id = ? AND locked_until < ? AND sent_at IS NULL', [time() + 120, $row['id'], time()])->rowCount() !== 1) { continue; }
            try {
                $payload = json_decode($row['payload'], true, 512, JSON_THROW_ON_ERROR);
                if ($row['channel'] === 'email') {
                    $from = getenv('MAIL_FROM') ?: 'konta@localhost';
                    $fromName = getenv('MAIL_FROM_NAME') ?: 'Konta';
                    $mailer = (new Mailer())
                        ->setFrom([$from => $fromName])
                        ->setTo($row['recipient'])
                        ->setSubject($payload['subject'])
                        ->setEmailFormat('both');
                    $mailer->getMessage()
                        ->setHeaders(['Auto-Submitted' => 'auto-generated'])
                        ->setBody([
                            'text' => $payload['body'],
                            'html' => $payload['html'] ?? self::emailHTML($payload['subject'], $payload['body']),
                        ]);
                    if (getenv('MAIL_TRANSPORT') === 'smtp') {
                        $mailer->setTransport('default')->getTransport()->send($mailer->getMessage());
                    } else {
                        $directory = ROOT . '/storage/mail';
                        if (!is_dir($directory)) { mkdir($directory, 0700, true); }
                        $path = $directory . '/' . $row['id'] . '.eml';
                        $message = $mailer->getMessage();
                        $eml = $message->getHeadersString(
                            ['from', 'sender', 'replyTo', 'readReceipt', 'returnPath', 'to', 'cc', 'subject'],
                            "\r\n",
                        ) . "\r\n\r\n" . $message->getBodyString("\r\n");
                        if (file_put_contents($path, $eml) === false) { throw new \RuntimeException('Mail storage unavailable'); }
                        chmod($path, 0600);
                    }
                } else {
                    foreach ($this->store->rows('SELECT * FROM devices WHERE user_id = ?', [$row['recipient']]) as $device) { (new ApplePush())->send($device, $payload); }
                }
                $this->store->db->update('outbox', ['sent_at' => time(), 'locked_until' => 0, 'payload' => '{}'], ['id' => $row['id']]);
                $sent++;
            } catch (\Throwable $error) {
                Log::warning('Delivery failed for outbox ' . $row['id'] . ' (' . $error::class . ')');
                $attempts = (int)$row['attempts'] + 1;
                $this->store->db->update('outbox', ['attempts' => $attempts, 'available_at' => time() + min(86400, 30 * (2 ** $attempts)), 'locked_until' => 0], ['id' => $row['id']]);
            }
        }
        return $sent;
    }

    public static function emailHTML(string $subject, string $body, ?string $actionLabel = null, ?string $actionURL = null): string
    {
        $escape = static fn(string $value): string => htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
        $paragraphs = '';
        foreach (preg_split('/\R{2,}/', trim($body)) ?: [] as $paragraph) {
            $paragraphs .= '<p style="margin:0 0 18px;color:#344054;font-family:-apple-system,BlinkMacSystemFont,&quot;Segoe UI&quot;,Arial,sans-serif;font-size:16px;line-height:1.55;overflow-wrap:anywhere;">'
                . nl2br($escape($paragraph), false) . '</p>';
        }
        $button = '';
        if ($actionLabel !== null && $actionURL !== null) {
            $button = '<table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin:8px 0 26px;"><tr>'
                . '<td align="center" bgcolor="#066BF2" style="border-radius:12px;mso-padding-alt:14px 24px;">'
                . '<a href="' . $escape($actionURL) . '" style="background:#066BF2;border:1px solid #066BF2;border-radius:12px;color:#ffffff;display:inline-block;font-family:-apple-system,BlinkMacSystemFont,&quot;Segoe UI&quot;,Arial,sans-serif;font-size:16px;font-weight:600;line-height:20px;padding:13px 24px;text-decoration:none;">'
                . $escape($actionLabel) . '</a></td></tr></table>';
        }
        return '<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            . '<meta name="color-scheme" content="light dark"><meta name="supported-color-schemes" content="light dark"></head>'
            . '<body style="margin:0;padding:0;background:#f5f7fb;"><div style="display:none;max-height:0;overflow:hidden;">'
            . $escape($subject) . '</div><table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" style="background:#f5f7fb;">'
            . '<tr><td align="center" style="padding:32px 16px;"><table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border:1px solid #e7eaf0;border-radius:20px;">'
            . '<tr><td style="padding:38px 38px 12px;"><div style="color:#066BF2;font-family:-apple-system,BlinkMacSystemFont,&quot;Segoe UI&quot;,Arial,sans-serif;font-size:18px;font-weight:700;letter-spacing:-.2px;">Konta</div>'
            . '<h1 style="margin:22px 0 18px;color:#101828;font-family:-apple-system,BlinkMacSystemFont,&quot;Segoe UI&quot;,Arial,sans-serif;font-size:30px;line-height:1.2;letter-spacing:-.6px;">'
            . $escape($subject) . '</h1>' . $paragraphs . $button . '</td></tr>'
            . '<tr><td style="padding:22px 38px 34px;border-top:1px solid #eef0f4;color:#667085;font-family:-apple-system,BlinkMacSystemFont,&quot;Segoe UI&quot;,Arial,sans-serif;font-size:13px;line-height:1.5;">'
            . 'Diese Nachricht wurde automatisch von Konta gesendet.<br><a href="https://konta-finance.com/support" style="color:#066BF2;text-decoration:none;">Hilfe &amp; Support</a>'
            . '</td></tr></table></td></tr></table></body></html>';
    }
}
