<?php
declare(strict_types=1);
namespace App\Controller;
use App\Service\{Households, ApiException, Store};
final class SystemController extends AppController
{
    public function health() { $this->store->db->execute('SELECT 1'); return $this->json(['status' => 'ok', 'service' => 'Konta API']); }
    public function bootstrap() {
        $u = $this->user();
        $households = array_map($this->store->household(...), $this->store->rows('SELECT h.*, m.role FROM households h JOIN memberships m ON m.household_id = h.id WHERE m.user_id = ? ORDER BY h.name', [$u['id']]));
        $invites = $u['verified'] ? array_map((new Households($this->store))->invitation(...), $this->store->rows('SELECT i.*, h.name AS household_name FROM invitations i JOIN households h ON h.id = i.household_id WHERE i.email = ? AND i.status = ? AND i.expires_at > ?', [$u['email'], 'pending', time()])) : [];
        $notifications = array_map(fn($r) => array_merge(json_decode($r['payload'], true), ['id' => $r['id'], 'read' => (bool)$r['is_read']]), $this->store->rows('SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 100', [$u['id']]));
        return $this->json(['user' => $u, 'households' => $households, 'invitations' => $invites, 'notifications' => $notifications]);
    }
    public function device() {
        $u = $this->user(); $d = $this->data(); $token = $d['token'] ?? '';
        if (!is_string($token) || !preg_match('/^[a-f0-9]{64,256}$/', $token)) { throw new ApiException('Ungültiges Geräte-Token.', 422); }
        if ($this->request->is('delete')) { $this->store->db->delete('devices', ['token' => $token, 'user_id' => $u['id']]); return $this->json(); }
        if (!in_array($d['platform'] ?? '', ['ios', 'macos'], true) || !in_array($d['environment'] ?? '', ['development', 'production'], true)) { throw new ApiException('Ungültige Geräteplattform.', 422); }
        $this->store->db->transactional(function () use ($d, $token, $u) {
            $this->store->db->delete('devices', ['token' => $token]);
            $this->store->db->insert('devices', ['token' => $token, 'user_id' => $u['id'], 'platform' => $d['platform'], 'environment' => $d['environment']]);
        });
        return $this->json();
    }
    public function read(string $id) { $u = $this->user(); $this->store->db->update('notifications', ['is_read' => true], ['id' => $id, 'user_id' => $u['id']]); return $this->json(); }
}
