<?php
declare(strict_types=1);
namespace App\Controller;
use App\Service\{Auth, ApiException, Delivery};
final class AuthController extends AppController
{
    public function register() { $this->throttle('register', 5); $result = (new Auth($this->store))->register($this->data()); (new Delivery($this->store))->flush(); return $this->json($result, 201); }
    public function login() { $this->throttle('login'); return $this->json((new Auth($this->store))->login($this->data())); }
    public function forgot() { $this->throttle('forgot', 5); (new Auth($this->store))->emailToken(Auth::email($this->data()['email'] ?? null), 'reset'); (new Delivery($this->store))->flush(); return $this->json(); }
    public function reset() { $this->throttle('reset'); $d = $this->data(); (new Auth($this->store))->redeem((string)($d['code'] ?? ''), 'reset', Auth::password($d['password'] ?? null)); return $this->json(); }
    public function verify() { $this->throttle('verify'); (new Auth($this->store))->redeem((string)($this->data()['code'] ?? ''), 'verify'); return $this->json(); }
    public function resend() { $u = $this->user(); $this->store->limit('resend:' . $u['id'], 3); (new Auth($this->store))->emailToken($u['email'], 'verify'); (new Delivery($this->store))->flush(); return $this->json(); }
    public function logout() {
        $u = $this->user(); $token = substr($this->request->getHeaderLine('Authorization'), 7);
        $this->store->db->delete('tokens', ['hash' => hash('sha256', $token)]);
        if (is_string($this->data()['deviceToken'] ?? null)) { $this->store->db->delete('devices', ['token' => $this->data()['deviceToken'], 'user_id' => $u['id']]); }
        return $this->json();
    }
    public function profile() {
        $u = $this->user(); $name = $this->data()['name'] ?? '';
        if (!is_string($name) || trim($name) === '' || mb_strlen($name) > 100) { throw new ApiException('Bitte einen gültigen Namen eingeben.', 422); }
        $this->store->db->update('users', ['name' => trim($name)], ['id' => $u['id']]);
        return $this->json(Auth::user($this->store->row('SELECT * FROM users WHERE id = ?', [$u['id']])));
    }
    public function deleteAccount() {
        $u = $this->user(); $row = $this->store->row('SELECT * FROM users WHERE id = ?', [$u['id']]);
        if (!password_verify((string)($this->data()['password'] ?? ''), $row['password_hash'])) { throw new ApiException('Bitte das aktuelle Passwort eingeben.', 403); }
        $this->store->db->transactional(function () use ($u) {
            if ($this->store->row('SELECT * FROM memberships WHERE user_id = ? AND role = ?', [$u['id'], 'owner'])) { throw new ApiException('Bitte deine Haushalte zuerst löschen oder die Leitung übertragen.', 409); }
            $this->store->db->delete('invitations', ['email' => $u['email']]);
            $this->store->db->delete('outbox', ['recipient IN' => [$u['id'], $u['email']]]);
            $this->store->db->delete('users', ['id' => $u['id']]);
        });
        return $this->json();
    }
}
