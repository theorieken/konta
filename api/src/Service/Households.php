<?php
declare(strict_types=1);
namespace App\Service;

final class Households
{
    public function __construct(private Store $store) {}
    public function create(string $user, string $name): array
    {
        if (trim($name) === '' || mb_strlen($name) > 100) { throw new ApiException('Bitte einen Haushaltsnamen eingeben (maximal 100 Zeichen).', 422); }
        return $this->store->db->transactional(function () use ($user, $name) {
            $id = Store::id();
            $this->store->db->insert('households', ['id' => $id, 'name' => trim($name), 'settings' => Store::json(['savingsGoal' => 0, 'goalDate' => null, 'horizon' => 24, 'aiEnabled' => false, 'aiModel' => getenv('OPENAI_MODEL') ?: 'gpt-4.1-mini']), 'version' => 1]);
            $this->store->db->insert('memberships', ['household_id' => $id, 'user_id' => $user, 'role' => 'owner']);
            foreach (json_decode(file_get_contents(CONFIG . 'categories.json'), true) as $category) {
                (new Records($this->store))->save($id, $user, 'category', Store::id(), $category);
            }
            return $this->store->householdFor($id, $user);
        });
    }
    public function update(string $id, string $user, array $data): array
    {
        $this->store->membership($id, $user, true);
        $current = $this->store->householdFor($id, $user);
        $new = array_replace($current, array_intersect_key($data, $current));
        if (!is_string($new['name']) || trim($new['name']) === '' || mb_strlen($new['name']) > 100 || !is_int($new['savingsGoal']) || $new['savingsGoal'] < 0 || $new['savingsGoal'] > 100000000000 || !is_int($new['horizon']) || $new['horizon'] < 1 || $new['horizon'] > 120 || !is_bool($new['aiEnabled']) || !is_string($new['aiModel']) || !preg_match('/^[a-zA-Z0-9._-]{1,80}$/', $new['aiModel']) || ($new['goalDate'] !== null && (!is_string($new['goalDate']) || !Records::date($new['goalDate'])))) { throw new ApiException('Bitte die Haushaltseinstellungen prüfen.', 422); }
        $version = $data['version'] ?? 0;
        if (!is_int($version) || $version !== $current['version']) { throw new ApiException('Die Einstellungen wurden inzwischen geändert.', 409); }
        $settings = array_intersect_key($new, array_flip(['savingsGoal', 'goalDate', 'horizon', 'aiEnabled', 'aiModel']));
        if ($this->store->db->update('households', ['name' => trim($new['name']), 'settings' => Store::json($settings), 'version' => $version + 1], ['id' => $id, 'version' => $version])->rowCount() !== 1) { throw new ApiException('Änderungskonflikt.', 409); }
        return $this->store->householdFor($id, $user);
    }
    public function invitation(array $row): array
    {
        return ['id' => $row['id'], 'householdID' => $row['household_id'], 'householdName' => $row['household_name'], 'email' => $row['email'], 'expiresAt' => gmdate('c', (int)$row['expires_at']), 'status' => $row['status'] === 'pending' && (int)$row['expires_at'] <= time() ? 'expired' : $row['status']];
    }
    public function invite(string $household, array $user, string $email): array
    {
        $this->store->membership($household, $user['id'], true);
        if (!$user['verified']) { throw new ApiException('Bitte zuerst deine E-Mail-Adresse bestätigen.', 403); }
        $email = Auth::email($email);
        return $this->store->db->transactional(function () use ($household, $user, $email) {
            $this->store->db->execute('UPDATE households SET version = version WHERE id = ?', [$household]);
            $existing = $this->store->row('SELECT * FROM users WHERE email = ?', [$email]);
            if ($existing && $this->store->row('SELECT * FROM memberships WHERE household_id = ? AND user_id = ?', [$household, $existing['id']])) { throw new ApiException('Diese Person gehört bereits zum Haushalt.', 409); }
            $pending = $this->store->row('SELECT i.*, h.name AS household_name FROM invitations i JOIN households h ON h.id = i.household_id WHERE i.household_id = ? AND i.email = ? AND i.status = ? AND i.expires_at > ?', [$household, $email, 'pending', time()]);
            if ($pending) { return $this->invitation($pending); }
            $id = Store::id();
            $this->store->db->insert('invitations', ['id' => $id, 'household_id' => $household, 'email' => $email, 'status' => 'pending', 'expires_at' => time() + 604800, 'created_at' => time()]);
            $name = $this->store->householdFor($household, $user['id'])['name'];
            $delivery = new Delivery($this->store);
            if ($existing) {
                $delivery->notify($existing['id'], ['title' => 'Einladung zu Konta', 'body' => 'Du wurdest zu einem Haushalt eingeladen. Öffne Konta, um die Einladung anzusehen.', 'householdID' => $household, 'invitationID' => $id]);
            }
            $instruction = $existing
                ? 'Öffne Konta und nimm die Einladung in den Einstellungen an.'
                : 'Erstelle zuerst ein Konta-Konto mit dieser E-Mail-Adresse und bestätige sie. Anschließend kannst du die Einladung in den Einstellungen annehmen.';
            $delivery->email(
                $email,
                'Gemeinsam planen mit Konta',
                $user['name'] . " lädt dich in den Haushalt „{$name}“ ein.\n\n{$instruction}\n\nDie Einladung ist sieben Tage gültig.",
                'Einladung in Konta öffnen',
                'konta://invitations'
            );
            return $this->invitation($this->store->row('SELECT i.*, h.name AS household_name FROM invitations i JOIN households h ON h.id = i.household_id WHERE i.id = ?', [$id]));
        });
    }
    public function respond(string $id, array $user, bool $accept): void
    {
        if (!$user['verified']) { throw new ApiException('Bitte zuerst deine E-Mail-Adresse bestätigen.', 403); }
        $this->store->db->transactional(function () use ($id, $user, $accept) {
            $invite = $this->store->row('SELECT * FROM invitations WHERE id = ? AND email = ?', [$id, $user['email']]);
            if (!$invite) { throw new ApiException('Einladung nicht gefunden.', 404); }
            $this->store->db->execute('UPDATE households SET version = version WHERE id = ?', [$invite['household_id']]);
            $changed = $this->store->db->execute('UPDATE invitations SET status = ? WHERE id = ? AND status = ? AND expires_at > ?', [$accept ? 'accepted' : 'declined', $id, 'pending', time()]);
            if ($changed->rowCount() !== 1) { throw new ApiException('Diese Einladung ist abgelaufen oder wurde bereits beantwortet.', 409); }
            if ($accept && !$this->store->row('SELECT * FROM memberships WHERE household_id = ? AND user_id = ?', [$invite['household_id'], $user['id']])) {
                $this->store->db->insert('memberships', ['household_id' => $invite['household_id'], 'user_id' => $user['id'], 'role' => 'member']);
            }
        });
    }
    public function removeMember(string $household, string $actor, string $member): void
    {
        $this->store->membership($household, $actor, $actor !== $member);
        $target = $this->store->membership($household, $member);
        if ($target['role'] === 'owner') { throw new ApiException('Übertrage zuerst die Haushaltsleitung.', 409); }
        $this->store->db->delete('memberships', ['household_id' => $household, 'user_id' => $member]);
    }
    public function transfer(string $household, string $actor, string $member): void
    {
        $this->store->db->transactional(function () use ($household, $actor, $member) {
            $this->store->db->execute('UPDATE households SET version = version WHERE id = ?', [$household]);
            $this->store->membership($household, $actor, true);
            $this->store->membership($household, $member);
            $this->store->db->update('memberships', ['role' => 'member'], ['household_id' => $household, 'user_id' => $actor]);
            $this->store->db->update('memberships', ['role' => 'owner'], ['household_id' => $household, 'user_id' => $member]);
        });
    }
}
