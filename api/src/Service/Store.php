<?php
declare(strict_types=1);
namespace App\Service;
use Cake\Database\Connection;
use Cake\Datasource\ConnectionManager;
use Cake\Utility\Text;
final class Store
{
    public Connection $db;
    public function __construct() { $this->db = ConnectionManager::get('default'); }
    public static function id(): string { return strtolower(Text::uuid()); }
    public static function json(mixed $value): string { return json_encode($value, JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE); }
    public function rows(string $sql, array $args = []): array { return $this->db->execute($sql, $args)->fetchAll('assoc'); }
    public function row(string $sql, array $args = []): ?array { return $this->rows($sql, $args)[0] ?? null; }
    public function membership(string $household, string $user, bool $owner = false): array
    {
        $member = $this->row('SELECT * FROM memberships WHERE household_id = ? AND user_id = ?', [$household, $user]);
        if (!$member || ($owner && $member['role'] !== 'owner')) { throw new ApiException('Kein Zugriff auf diesen Haushalt.', 403); }
        return $member;
    }
    public function record(string $household, string $id, ?string $kind = null): array
    {
        $row = $this->row('SELECT * FROM records WHERE id = ? AND household_id = ? AND deleted_at IS NULL', [$id, $household]);
        if (!$row || ($kind && $row['kind'] !== $kind)) { throw new ApiException('Eintrag nicht gefunden.', 404); }
        return $this->decodeRecord($row);
    }
    public function decodeRecord(array $row): array
    {
        return array_merge(json_decode($row['payload'], true, 512, JSON_THROW_ON_ERROR), [
            'id' => $row['id'], 'kind' => $row['kind'], 'version' => (int)$row['version'],
            'createdAt' => gmdate('c', (int)$row['created_at']), 'updatedAt' => gmdate('c', (int)$row['updated_at']),
        ]);
    }
    public function records(string $household): array
    {
        return array_map($this->decodeRecord(...), $this->rows('SELECT * FROM records WHERE household_id = ? AND deleted_at IS NULL ORDER BY created_at, id', [$household]));
    }
    public function household(array $row): array
    {
        return array_merge(json_decode($row['settings'], true), ['id' => $row['id'], 'name' => $row['name'], 'role' => $row['role'] ?? 'member', 'version' => (int)$row['version']]);
    }
    public function householdFor(string $id, string $user): array
    {
        $member = $this->membership($id, $user);
        return $this->household(array_merge($this->row('SELECT * FROM households WHERE id = ?', [$id]), $member));
    }
    public function limit(string $key, int $max = 10, int $window = 900): void
    {
        $id = hash('sha256', $key . ':' . intdiv(time(), $window));
        try { $this->db->insert('rate_limits', ['id' => $id, 'attempts' => 0, 'expires_at' => time() + $window]); }
        catch (\Cake\Database\Exception\QueryException $e) { if (!$this->row('SELECT id FROM rate_limits WHERE id = ?', [$id])) { throw $e; } }
        $this->db->execute('UPDATE rate_limits SET attempts = attempts + 1 WHERE id = ?', [$id]);
        if ((int)$this->row('SELECT attempts FROM rate_limits WHERE id = ?', [$id])['attempts'] > $max) { throw new ApiException('Zu viele Anfragen. Bitte später erneut versuchen.', 429); }
    }
}
