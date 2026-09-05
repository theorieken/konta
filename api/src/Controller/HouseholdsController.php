<?php
declare(strict_types=1);
namespace App\Controller;
use App\Service\{Households, Delivery, Imports, ApiException};
final class HouseholdsController extends AppController
{
    public function create() { $u = $this->user(); $this->store->limit('household:' . $u['id'], 20, 86400); return $this->json((new Households($this->store))->create($u['id'], (string)($this->data()['name'] ?? '')), 201); }
    public function update(string $household) { $u = $this->user(); $result = (new Households($this->store))->update($household, $u['id'], $this->data()); (new Delivery($this->store))->changed($household, $u['id']); return $this->json($result); }
    public function snapshot(string $household) {
        $u = $this->user(); $this->store->membership($household, $u['id']);
        return $this->json($this->store->db->transactional(function () use ($household, $u) {
            $members = $this->store->rows('SELECT u.id, u.name, u.email, m.role FROM memberships m JOIN users u ON u.id = m.user_id WHERE m.household_id = ? ORDER BY m.role DESC, u.name', [$household]);
            $invites = $this->store->membership($household, $u['id'])['role'] === 'owner' ? array_map((new Households($this->store))->invitation(...), $this->store->rows('SELECT i.*, h.name AS household_name FROM invitations i JOIN households h ON h.id = i.household_id WHERE i.household_id = ? AND i.status = ?', [$household, 'pending'])) : [];
            return ['household' => $this->store->householdFor($household, $u['id']), 'records' => $this->store->records($household), 'members' => $members, 'uploads' => array_map(Imports::serialize(...), $this->store->rows('SELECT * FROM uploads WHERE household_id = ? ORDER BY created_at DESC', [$household])), 'invitations' => $invites];
        }));
    }
    public function invitations(string $household) { $u = $this->user(); $this->store->limit('invite:' . $u['id'], 20, 86400); $r = (new Households($this->store))->invite($household, $u, (string)($this->data()['email'] ?? '')); (new Delivery($this->store))->flush(); return $this->json($r, 201); }
    public function respond(string $id) { $u = $this->user(); $accept = $this->data()['accept'] ?? null; if (!is_bool($accept)) { throw new ApiException('Bitte Einladung annehmen oder ablehnen.', 422); } (new Households($this->store))->respond($id, $u, $accept); return $this->json(); }
    public function revoke(string $household, string $id) { $u = $this->user(); $this->store->membership($household, $u['id'], true); $this->store->db->update('invitations', ['status' => 'revoked'], ['id' => $id, 'household_id' => $household, 'status' => 'pending']); return $this->json(); }
    public function removeMember(string $household, string $id) { $u = $this->user(); (new Households($this->store))->removeMember($household, $u['id'], $id); return $this->json(); }
    public function transfer(string $household) { $u = $this->user(); (new Households($this->store))->transfer($household, $u['id'], (string)($this->data()['userID'] ?? '')); return $this->json(); }
    public function delete(string $household) {
        $u = $this->user(); $this->store->membership($household, $u['id'], true);
        $name = $this->store->householdFor($household, $u['id'])['name'];
        if (($this->data()['confirmation'] ?? '') !== $name) { throw new ApiException('Bitte den Haushaltsnamen zur Bestätigung eingeben.', 422); }
        $uploads = $this->store->rows('SELECT id FROM uploads WHERE household_id = ?', [$household]);
        $this->store->db->delete('households', ['id' => $household]);
        foreach ($uploads as $upload) { $path = ROOT . '/storage/uploads/' . $upload['id'] . '.csv'; if (is_file($path)) { unlink($path); } }
        return $this->json();
    }
}
