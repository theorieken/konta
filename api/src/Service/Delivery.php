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
    public function email(string $email, string $subject, string $body): void { $this->enqueue('email', $email, compact('subject', 'body')); }
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
                    if (getenv('MAIL_TRANSPORT') === 'smtp') {
                        (new Mailer())->setTransport('default')->setFrom(getenv('MAIL_FROM') ?: 'konta@localhost')->setTo($row['recipient'])->setSubject($payload['subject'])->deliver($payload['body']);
                    } else {
                        $directory = ROOT . '/storage/mail';
                        if (!is_dir($directory)) { mkdir($directory, 0700, true); }
                        $path = $directory . '/' . $row['id'] . '.eml';
                        if (file_put_contents($path, "To: {$row['recipient']}\nSubject: {$payload['subject']}\nContent-Type: text/plain; charset=UTF-8\n\n{$payload['body']}") === false) { throw new \RuntimeException('Mail storage unavailable'); }
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
}
