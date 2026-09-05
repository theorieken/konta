<?php
declare(strict_types=1);
namespace App\Controller;
use App\Service\{Records, Imports, Classifier, Delivery, ApiException};
use Psr\Http\Message\UploadedFileInterface;
final class RecordsController extends AppController
{
    private function changed(string $household, string $user): void { $d = new Delivery($this->store); $d->changed($household, $user); $d->flush(); }
    public function save(string $household, string $kind, string $id) { $u = $this->user(); $r = (new Records($this->store))->save($household, $u['id'], $kind, $id, $this->data()); $this->changed($household, $u['id']); return $this->json($r); }
    public function delete(string $household, string $id) { $u = $this->user(); (new Records($this->store))->delete($household, $u['id'], $id, (int)($this->data()['version'] ?? 0)); $this->changed($household, $u['id']); return $this->json(); }
    public function upload(string $household) {
        $u = $this->user(); $this->store->limit('upload:' . $u['id'], 20, 3600); $file = $this->request->getData('file');
        if (!$file instanceof UploadedFileInterface) { throw new ApiException('Bitte eine CSV-Datei auswählen.', 422); }
        $r = (new Imports($this->store))->upload($household, $u['id'], (string)$this->request->getData('accountID'), $file); $this->changed($household, $u['id']); return $this->json($r, 201);
    }
    public function download(string $household, string $id) {
        $u = $this->user(); $this->store->membership($household, $u['id']);
        $file = $this->store->row('SELECT * FROM uploads WHERE id = ? AND household_id = ?', [$id, $household]);
        if (!$file) { throw new ApiException('Datei nicht gefunden.', 404); }
        return $this->response->withFile(ROOT . '/storage/uploads/' . $file['id'] . '.csv', ['download' => true, 'name' => $file['name']]);
    }
    public function classify(string $household) { $u = $this->user(); $this->store->limit('ai:' . $u['id'], 60, 3600); $ids = $this->data()['ids'] ?? []; if (!is_array($ids)) { throw new ApiException('Buchungs-IDs erwartet.', 422); } $r = (new Classifier($this->store))->classify($household, $u['id'], $ids); $this->changed($household, $u['id']); return $this->json($r); }
}
