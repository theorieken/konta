<?php
declare(strict_types=1);
namespace App\Service;

final class CsvParser
{
    private const HINTS = [
        'date' => ['buchungstag', 'buchungsdatum', 'booking date', 'date', 'datum', 'wertstellung', 'valuta'],
        'amount' => ['umsatz', 'betrag', 'amount', 'buchungsbetrag', 'wert'],
        'debit' => ['soll', 'debit', 'belastung'], 'credit' => ['haben', 'credit', 'gutschrift'],
        'purpose' => ['verwendungszweck', 'purpose', 'beschreibung', 'description', 'buchungstext', 'text'],
        'counterparty' => ['beguenstigter zahlungspflichtiger', 'begünstigter / zahlungspflichtiger', 'zahlungsempfänger', 'zahlungspflichtiger', 'empfänger', 'auftraggeber', 'name', 'counterparty'],
        'external' => ['referenz', 'reference', 'transaktions id', 'transaction id'],
    ];
    public static function cents(string $input): int
    {
        $input = trim(str_replace(["\xc2\xa0", ' ', '€', 'EUR'], '', $input));
        $negative = str_starts_with($input, '(') && str_ends_with($input, ')');
        $input = trim($input, '()');
        if (str_contains($input, ',')) { $input = str_replace(',', '.', str_replace('.', '', $input)); }
        if (!preg_match('/^([+-]?)(\d{1,10})(?:\.(\d{1,2}))?$/', $input, $parts)) { throw new ApiException('Ungültiger Geldbetrag in der CSV-Datei.', 422); }
        $cents = (int)$parts[2] * 100 + (int)str_pad($parts[3] ?? '', 2, '0');
        if ($cents > 100000000000) { throw new ApiException('CSV-Betrag ist zu groß.', 422); }
        return ($negative || $parts[1] === '-') ? -$cents : $cents;
    }
    private static function normalize(string $value): string
    {
        return trim(preg_replace('/\s+/', ' ', mb_strtolower(str_replace(["\xef\xbb\xbf", '_', '-'], ['', ' ', ' '], $value))));
    }
    private static function columns(array $row): array
    {
        $result = [];
        $used = [];
        foreach (self::HINTS as $field => $hints) {
            $best = 0;
            foreach ($row as $index => $header) {
                if (isset($used[$index])) { continue; }
                $header = self::normalize((string)$header);
                if (in_array($field, ['amount', 'debit', 'credit'], true) && preg_match('/datum|date|wertstellung|valuta|buchungstag/', $header)) { continue; }
                foreach ($hints as $order => $hint) {
                    $score = $header === $hint ? 10000 : (str_starts_with($header, $hint) ? 6000 : (str_contains($header, $hint) ? 3000 : 0));
                    $score -= $order * 10;
                    if ($score > $best) { $best = $score; $result[$field] = $index; }
                }
            }
            if (isset($result[$field])) { $used[$result[$field]] = true; }
        }
        return $result;
    }
    public function parse(string $bytes): array
    {
        if (str_contains($bytes, "\0")) { throw new ApiException('Bitte eine CSV-Datei in UTF-8 oder Windows-1252 verwenden.', 422); }
        if (!mb_check_encoding($bytes, 'UTF-8')) { $bytes = mb_convert_encoding($bytes, 'UTF-8', 'Windows-1252'); }
        $best = null;
        foreach ([";", ",", "\t"] as $delimiter) {
            $stream = fopen('php://temp', 'r+'); fwrite($stream, $bytes); rewind($stream);
            for ($i = 0; $i < 30 && ($row = fgetcsv($stream, null, $delimiter, '"', '')) !== false; $i++) {
                $columns = self::columns($row);
                if (isset($columns['date']) && (isset($columns['amount']) || isset($columns['debit']) || isset($columns['credit']))) {
                    if (!$best || count($columns) > count($best['columns'])) { $best = ['delimiter' => $delimiter, 'offset' => ftell($stream), 'columns' => $columns, 'line' => $i + 1]; }
                    break;
                }
            }
            fclose($stream);
        }
        if (!$best) { throw new ApiException('Keine Spalten für Buchungsdatum und Betrag gefunden.', 422); }
        $stream = fopen('php://temp', 'r+'); fwrite($stream, $bytes); fseek($stream, $best['offset']);
        $result = [];
        $line = $best['line'];
        try {
            while (($row = fgetcsv($stream, null, $best['delimiter'], '"', '')) !== false) {
                $line++;
                if (count(array_filter($row, fn($v) => trim((string)$v) !== '')) === 0) { continue; }
                $get = fn(string $field): string => isset($best['columns'][$field]) ? trim((string)($row[$best['columns'][$field]] ?? '')) : '';
                $rawDate = $get('date'); $date = null;
                foreach (['!d.m.Y', '!Y-m-d', '!d.m.y', '!d/m/Y'] as $format) {
                    $candidate = \DateTimeImmutable::createFromFormat($format, $rawDate);
                    if ($candidate && $candidate->format(substr($format, 1)) === $rawDate) { $date = $candidate->format('Y-m-d'); break; }
                }
                if (!$date || !Records::date($date)) { throw new ApiException('Ungültiges Buchungsdatum in CSV-Zeile ' . $line . '.', 422); }
                $amount = isset($best['columns']['amount']) ? self::cents($get('amount')) : (abs(self::cents($get('credit') ?: '0')) - abs(self::cents($get('debit') ?: '0')));
                $result[] = ['date' => $date, 'amount' => $amount, 'purpose' => $get('purpose'), 'counterparty' => $get('counterparty'), 'external' => $get('external')];
                if (count($result) > 2000) { throw new ApiException('Bitte maximal 2.000 Buchungen pro Datei importieren.', 422); }
            }
        } finally { fclose($stream); }
        if (!$result) { throw new ApiException('Die CSV-Datei enthält keine Buchungen.', 422); }
        return $result;
    }
}
