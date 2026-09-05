<?php
declare(strict_types=1);
namespace App\Service;

final class Records
{
    public const KINDS = ['account', 'category', 'transaction', 'contract', 'loan', 'job'];
    public function __construct(private Store $store) {}
    public static function defaults(string $kind): array
    {
        return ['name' => '', 'notes' => '', 'tags' => [], 'amount' => 0, 'date' => gmdate('Y-m-d'),
            'accountID' => null, 'categoryID' => null, 'state' => 'reality', 'direction' => 'expense',
            'recurrence' => 'monthly', 'intervalCount' => 1, 'dayOfMonth' => 1, 'endDate' => null,
            'active' => true, 'includeInNetWorth' => true, 'accountType' => 'checking', 'bank' => '', 'iban' => '',
            'counterparty' => '', 'principal' => 0, 'interestBasisPoints' => 0, 'cancellationDays' => 0,
            'keywords' => [], 'budget' => 0, 'categorySource' => 'manual', 'confidence' => null,
            'needsReview' => false, 'matchedPlanKey' => null, 'importHash' => null];
    }
    public static function date(string $value): bool
    {
        $date = \DateTimeImmutable::createFromFormat('!Y-m-d', $value);
        return $date && $date->format('Y-m-d') === $value && $value >= '1900-01-01' && $value <= '2199-12-31';
    }
    public function save(string $household, string $user, string $kind, string $id, array $input, bool $import = false): array
    {
        if (!in_array($kind, self::KINDS, true) || !preg_match('/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/', $id)) { throw new ApiException('Ungültiger Eintrag.', 422); }
        return $this->store->db->transactional(function () use ($household, $user, $kind, $id, $input, $import) {
            $this->store->membership($household, $user);
            // Serialize household mutations so relationship validation cannot race deletion.
            $this->store->db->execute('UPDATE households SET version = version WHERE id = ?', [$household]);
            $this->store->membership($household, $user);
            $old = $this->store->row('SELECT * FROM records WHERE id = ?', [$id]);
            if ($old && ($old['household_id'] !== $household || $old['kind'] !== $kind || $old['deleted_at'] !== null)) { throw new ApiException('Eintrag nicht gefunden.', 404); }
            $version = $input['version'] ?? 0;
            if (!is_int($version) || $version !== ($old ? (int)$old['version'] : 0)) { throw new ApiException('Dieser Eintrag wurde inzwischen geändert. Bitte neu laden.', 409); }
            $previous = $old ? $this->store->decodeRecord($old) : null;
            $payload = array_replace(self::defaults($kind), array_intersect_key($input, self::defaults($kind)));
            foreach (['name' => 255, 'notes' => 10000, 'bank' => 255, 'iban' => 34, 'counterparty' => 255] as $field => $max) {
                if (!is_string($payload[$field]) || mb_strlen($payload[$field]) > $max) { throw new ApiException('Ungültiges Textfeld: ' . $field, 422); }
                $payload[$field] = trim($payload[$field]);
            }
            if ($payload['name'] === '') { throw new ApiException('Bitte einen Namen eingeben.', 422); }
            foreach (['amount', 'principal', 'budget'] as $field) {
                if (!is_int($payload[$field]) || abs($payload[$field]) > 100000000000) { throw new ApiException('Beträge müssen ganze Cent sein (maximal 1 Mrd. Euro).', 422); }
            }
            foreach (['intervalCount' => [1, 60], 'dayOfMonth' => [1, 31], 'interestBasisPoints' => [0, 10000], 'cancellationDays' => [0, 3650]] as $field => [$min, $max]) {
                if (!is_int($payload[$field]) || $payload[$field] < $min || $payload[$field] > $max) { throw new ApiException('Ungültiger Wert: ' . $field, 422); }
            }
            foreach (['active', 'includeInNetWorth', 'needsReview'] as $field) {
                if (!is_bool($payload[$field])) { throw new ApiException('Ungültiger Schalter: ' . $field, 422); }
            }
            foreach (['tags', 'keywords'] as $field) {
                if (!is_array($payload[$field]) || !array_is_list($payload[$field]) || count($payload[$field]) > 30) { throw new ApiException('Zu viele Stichwörter.', 422); }
                foreach ($payload[$field] as $word) {
                    if (!is_string($word) || mb_strlen($word) > 80) { throw new ApiException('Ungültiges Stichwort.', 422); }
                }
                $payload[$field] = array_values(array_unique(array_filter(array_map('trim', $payload[$field]))));
            }
            foreach (['state' => ['reality', 'planned'], 'direction' => ['income', 'expense', 'both'],
                'recurrence' => ['once', 'weekly', 'biweekly', 'monthly', 'quarterly', 'semiannual', 'yearly'],
                'accountType' => ['checking', 'savings', 'credit', 'cash', 'investment']] as $field => $allowed) {
                if (!in_array($payload[$field], $allowed, true)) { throw new ApiException('Ungültige Auswahl: ' . $field, 422); }
            }
            if (!is_string($payload['date']) || !self::date($payload['date']) || ($payload['endDate'] !== null && (!is_string($payload['endDate']) || !self::date($payload['endDate']) || $payload['endDate'] < $payload['date']))) { throw new ApiException('Bitte gültige Datumswerte eingeben.', 422); }
            if (in_array($kind, ['transaction', 'contract', 'loan', 'job'], true)) {
                foreach (['accountID' => 'account', 'categoryID' => 'category'] as $field => $target) {
                    if (!is_string($payload[$field])) { throw new ApiException('Bitte Konto und Kategorie auswählen.', 422); }
                    $this->store->record($household, $payload[$field], $target);
                }
            } else { $payload['accountID'] = $payload['categoryID'] = null; }
            if (in_array($kind, ['contract', 'loan', 'job'], true) && $payload['amount'] <= 0) { throw new ApiException('Die regelmäßige Rate muss positiv sein.', 422); }
            if ($kind === 'job') { $payload['direction'] = 'income'; }
            if ($kind === 'loan') {
                $payload['direction'] = 'expense';
                if ($payload['principal'] <= 0) { throw new ApiException('Bitte die Restschuld bei Kreditbeginn eingeben.', 422); }
            }
            if ($payload['principal'] < 0 || $payload['budget'] < 0) { throw new ApiException('Kreditsumme und Budget dürfen nicht negativ sein.', 422); }
            if (!$import) {
                $payload['importHash'] = $previous['importHash'] ?? null;
                $categoryChanged = !$previous || $previous['categoryID'] !== $payload['categoryID'] || (($input['categorySource'] ?? '') === 'manual' && $previous['categorySource'] !== 'manual');
                $payload['categorySource'] = $categoryChanged ? 'manual' : ($previous['categorySource'] ?? 'manual');
                $payload['confidence'] = $categoryChanged ? null : ($previous['confidence'] ?? null);
            }
            if ($payload['matchedPlanKey'] !== null) {
                if ($kind !== 'transaction' || $payload['state'] !== 'reality' || !is_string($payload['matchedPlanKey']) || !preg_match('/^(transaction|contract|loan|job):([a-f0-9-]{36}):(\d{4}-\d{2}-\d{2})$/', $payload['matchedPlanKey'], $match) || !self::date($match[3])) { throw new ApiException('Ungültiger Planabgleich.', 422); }
                $sourceRow = $this->store->row('SELECT * FROM records WHERE id = ? AND household_id = ? AND kind = ?', [$match[2], $household, $match[1]]);
                $retainedLink = ($previous['matchedPlanKey'] ?? null) === $payload['matchedPlanKey'];
                if ((!$sourceRow || $sourceRow['deleted_at'] !== null) && !$retainedLink) { throw new ApiException('Planquelle nicht gefunden.', 404); }
                // Purging an old source must not make its existing booking uneditable.
                $source = $sourceRow ? $this->store->decodeRecord($sourceRow) : [
                    'id' => $match[2], 'kind' => $match[1], 'state' => 'planned', 'date' => $match[3],
                    'accountID' => $previous['accountID'], 'categoryID' => $previous['categoryID'],
                ];
                if ($source['accountID'] !== $payload['accountID'] || $source['id'] === $id || ($source['kind'] === 'transaction' && ($source['state'] !== 'planned' || $source['date'] !== $match[3]))) { throw new ApiException('Der Plan gehört nicht zu diesem Konto.', 422); }
                $duplicate = $this->store->row('SELECT id FROM records WHERE household_id = ? AND matched_plan_key = ? AND id <> ?', [$household, $payload['matchedPlanKey'], $id]);
                if ($duplicate) { throw new ApiException('Dieser Plan wurde bereits abgeglichen.', 409); }
                if ($payload['categorySource'] !== 'manual') { $payload['categoryID'] = $source['categoryID']; $payload['categorySource'] = 'plan'; $payload['confidence'] = null; }
            }
            $values = ['payload' => Store::json($payload), 'version' => $version + 1, 'updated_at' => time(), 'matched_plan_key' => $payload['matchedPlanKey']];
            if ($old) {
                $changed = $this->store->db->update('records', $values, ['id' => $id, 'household_id' => $household, 'version' => $version]);
                if ($changed->rowCount() !== 1) { throw new ApiException('Änderungskonflikt. Bitte neu laden.', 409); }
            } else {
                $this->store->db->insert('records', array_merge($values, ['id' => $id, 'household_id' => $household, 'kind' => $kind, 'created_at' => time(), 'created_by' => $user, 'import_hash' => $payload['importHash']]));
            }
            return $this->store->record($household, $id);
        });
    }
    public function delete(string $household, string $user, string $id, int $version): void
    {
        $this->store->db->transactional(function () use ($household, $user, $id, $version) {
            $this->store->membership($household, $user);
            $this->store->db->execute('UPDATE households SET version = version WHERE id = ?', [$household]);
            $record = $this->store->record($household, $id);
            foreach ($this->store->records($household) as $other) {
                if ($other['accountID'] === $id || $other['categoryID'] === $id) { throw new ApiException('Dieser Eintrag wird noch verwendet. Bitte zuerst die Verknüpfungen ändern.', 409); }
            }
            if ($version !== $record['version']) { throw new ApiException('Änderungskonflikt. Bitte neu laden.', 409); }
            $this->store->db->update('records', ['deleted_at' => time(), 'matched_plan_key' => null, 'version' => $version + 1], ['id' => $id]);
        });
    }
}
