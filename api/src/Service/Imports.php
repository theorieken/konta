<?php
declare(strict_types=1);
namespace App\Service;
use Psr\Http\Message\UploadedFileInterface;

final class Imports
{
    public function __construct(private Store $store) {}
    public static function category(array $row, array $categories): array
    {
        $text = mb_strtolower($row['purpose'] . ' ' . $row['counterparty']);
        foreach ($categories as $category) {
            if ($category['direction'] !== 'both' && $category['direction'] !== ($row['amount'] >= 0 ? 'income' : 'expense')) { continue; }
            foreach ($category['keywords'] as $keyword) {
                if ($keyword !== '' && mb_stripos($text, $keyword) !== false) { return [$category['id'], 0.75]; }
            }
        }
        $fallback = array_values(array_filter($categories, fn($c) => $c['name'] === 'Sonstiges'))[0] ?? $categories[0] ?? null;
        if (!$fallback) { throw new ApiException('Bitte zuerst eine Kategorie anlegen.', 422); }
        return [$fallback['id'], 0.0];
    }
    public function upload(string $household, string $user, string $account, UploadedFileInterface $file): array
    {
        $this->store->membership($household, $user);
        $this->store->record($household, $account, 'account');
        if ($file->getError() !== UPLOAD_ERR_OK || !$file->getSize() || $file->getSize() > 10 * 1024 * 1024 || strtolower(pathinfo($file->getClientFilename() ?? '', PATHINFO_EXTENSION)) !== 'csv') { throw new ApiException('Bitte eine CSV-Datei bis 10 MB auswählen.', 422); }
        $rows = (new CsvParser())->parse((string)$file->getStream());
        $categories = array_values(array_filter($this->store->records($household), fn($r) => $r['kind'] === 'category'));
        $id = Store::id();
        $directory = ROOT . '/storage/uploads';
        if (!is_dir($directory)) { mkdir($directory, 0700, true); }
        $path = $directory . '/' . $id . '.csv';
        $file->moveTo($path); chmod($path, 0600);
        try {
            return $this->store->db->transactional(function () use ($household, $user, $account, $rows, $categories, $id, $file) {
                $this->store->db->execute('UPDATE households SET version = version WHERE id = ?', [$household]);
                $imported = 0; $duplicates = 0;
                foreach ($rows as $row) {
                    $hash = hash('sha256', Store::json([$account, $row['date'], $row['amount'], $row['counterparty'], $row['purpose'], $row['external']]));
                    if ($this->store->row('SELECT id FROM records WHERE household_id = ? AND import_hash = ?', [$household, $hash])) { $duplicates++; continue; }
                    [$category, $confidence] = self::category($row, $categories);
                    (new Records($this->store))->save($household, $user, 'transaction', Store::id(), [
                        'name' => mb_substr($row['purpose'] ?: ($row['counterparty'] ?: 'Buchung'), 0, 255), 'notes' => mb_substr($row['purpose'], 0, 10000),
                        'date' => $row['date'], 'amount' => $row['amount'], 'counterparty' => mb_substr($row['counterparty'], 0, 255), 'accountID' => $account,
                        'categoryID' => $category, 'categorySource' => 'keyword', 'confidence' => $confidence, 'needsReview' => $confidence < 0.6, 'importHash' => $hash,
                    ], true);
                    $imported++;
                }
                $upload = ['id' => $id, 'household_id' => $household, 'name' => mb_substr(basename($file->getClientFilename() ?? 'Umsätze.csv'), 0, 255), 'status' => 'completed', 'imported' => $imported, 'duplicates' => $duplicates, 'created_at' => time()];
                $this->store->db->insert('uploads', $upload);
                return self::serialize($upload);
            });
        } catch (\Throwable $error) { unlink($path); throw $error; }
    }
    public static function serialize(array $row): array
    {
        return ['id' => $row['id'], 'name' => $row['name'], 'status' => $row['status'], 'imported' => (int)$row['imported'], 'duplicates' => (int)$row['duplicates'], 'createdAt' => gmdate('c', (int)$row['created_at'])];
    }
}
