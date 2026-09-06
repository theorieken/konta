<?php
declare(strict_types=1);
namespace App\Service;

final class Auth
{
    public function __construct(private Store $store) {}
    public static function email(mixed $email): string
    {
        if (!is_string($email) || !filter_var(trim($email), FILTER_VALIDATE_EMAIL) || strlen($email) > 254) { throw new ApiException('Bitte eine gültige E-Mail-Adresse eingeben.', 422); }
        return mb_strtolower(trim($email));
    }
    public static function password(mixed $password): string
    {
        // PASSWORD_DEFAULT may use bcrypt, whose input limit is 72 bytes.
        if (!is_string($password) || mb_strlen($password) < 12 || strlen($password) > 72) { throw new ApiException('Bitte ein Passwort mit mindestens 12 Zeichen verwenden. Lange Passwörter dürfen höchstens 72 UTF-8-Bytes enthalten.', 422); }
        return $password;
    }
    public static function user(array $row): array
    {
        return ['id' => $row['id'], 'name' => $row['name'], 'email' => $row['email'], 'verified' => (bool)$row['verified']];
    }
    public function token(string $user, string $purpose = 'session'): string
    {
        $token = bin2hex(random_bytes(32));
        $this->store->db->insert('tokens', ['hash' => hash('sha256', $token), 'user_id' => $user, 'purpose' => $purpose, 'expires_at' => time() + ($purpose === 'session' ? 2592000 : 3600)]);
        return $token;
    }
    public function authenticate(string $header): array
    {
        if (!preg_match('/^Bearer ([a-f0-9]{64})$/', $header, $match)) { throw new ApiException('Bitte anmelden.', 401); }
        $row = $this->store->row('SELECT u.* FROM users u JOIN tokens t ON t.user_id = u.id WHERE t.hash = ? AND t.purpose = ? AND t.expires_at > ?', [hash('sha256', $match[1]), 'session', time()]);
        if (!$row) { throw new ApiException('Die Sitzung ist abgelaufen. Bitte erneut anmelden.', 401); }
        return self::user($row);
    }
    public function register(array $data): array
    {
        $email = self::email($data['email'] ?? null);
        $password = self::password($data['password'] ?? null);
        $name = trim(is_string($data['name'] ?? null) ? $data['name'] : '');
        if ($name === '' || mb_strlen($name) > 100) { throw new ApiException('Bitte einen Namen eingeben (maximal 100 Zeichen).', 422); }
        if ($this->store->row('SELECT id FROM users WHERE email = ?', [$email])) { throw new ApiException('Registrierung nicht möglich. Bitte anmelden oder Passwort zurücksetzen.', 409); }
        return $this->store->db->transactional(function () use ($email, $password, $name) {
            $id = Store::id();
            $this->store->db->insert('users', ['id' => $id, 'name' => $name, 'email' => $email, 'password_hash' => password_hash($password, PASSWORD_DEFAULT), 'verified' => false, 'created_at' => time()]);
            (new Households($this->store))->create($id, 'Mein Haushalt');
            $this->emailToken($email, 'verify');
            return ['token' => $this->token($id), 'user' => self::user($this->store->row('SELECT * FROM users WHERE id = ?', [$id]))];
        });
    }
    public function login(array $data): array
    {
        $email = self::email($data['email'] ?? null);
        $row = $this->store->row('SELECT * FROM users WHERE email = ?', [$email]);
        // Always run a password verification to reduce account enumeration by timing.
        $valid = password_verify(is_string($data['password'] ?? null) ? $data['password'] : '', $row['password_hash'] ?? '$2y$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2uheWG/igi.');
        if (!$row || !$valid) { throw new ApiException('E-Mail oder Passwort ist falsch.', 401); }
        return ['token' => $this->token($row['id']), 'user' => self::user($row)];
    }
    public function emailToken(string $email, string $purpose): void
    {
        $row = $this->store->row('SELECT * FROM users WHERE email = ?', [$email]);
        if (!$row || ($purpose === 'verify' && $row['verified'])) { return; }
        $token = $this->token($row['id'], $purpose);
        $title = $purpose === 'verify' ? 'E-Mail-Adresse bestätigen' : 'Passwort zurücksetzen';
        $intro = $purpose === 'verify'
            ? "Hallo {$row['name']},\n\nschön, dass du bei Konta bist. Bestätige jetzt deine E-Mail-Adresse."
            : "Hallo {$row['name']},\n\ndu möchtest dein Konta-Passwort zurücksetzen.";
        $body = "{$intro}\n\nDein persönlicher Code (eine Stunde gültig):\n{$token}\n\nÖffne Konta über den Button und gib den Code dort ein. Du hast nichts angefordert? Dann kannst du diese E-Mail ignorieren.";
        (new Delivery($this->store))->email($email, $title, $body, 'Konta öffnen', $purpose === 'verify' ? 'konta://verify' : 'konta://reset');
    }
    public function redeem(string $token, string $purpose, ?string $password = null): void
    {
        $this->store->db->transactional(function () use ($token, $purpose, $password) {
            $hash = hash('sha256', $token);
            $row = $this->store->row('SELECT * FROM tokens WHERE hash = ? AND purpose = ? AND expires_at > ?', [$hash, $purpose, time()]);
            if (!$row) { throw new ApiException('Der Code ist ungültig oder abgelaufen.', 422); }
            if ($this->store->db->delete('tokens', ['hash' => $hash])->rowCount() !== 1) { throw new ApiException('Der Code wurde bereits verwendet.', 409); }
            $fields = $purpose === 'verify' ? ['verified' => true] : ['password_hash' => password_hash(self::password($password), PASSWORD_DEFAULT)];
            $this->store->db->update('users', $fields, ['id' => $row['user_id']]);
            if ($purpose === 'reset') {
                $this->store->db->delete('tokens', ['user_id' => $row['user_id']]);
                $this->store->db->delete('devices', ['user_id' => $row['user_id']]);
            }
        });
    }
}
