<?php
declare(strict_types=1);
namespace App\Test;
use PHPUnit\Framework\TestCase;
use App\Service\{Store, Auth, Households, Records, CsvParser, ApiException, ApplePush, Delivery, Imports, Support};

final class FinanceApiTest extends TestCase
{
    private Store $store;
    protected function setUp(): void
    {
        $this->store = new Store();
        foreach (['households', 'users', 'outbox', 'rate_limits'] as $table) { $this->store->db->execute('DELETE FROM ' . $table); }
    }
    private function user(string $email = 'alex@example.test', bool $verified = true): array
    {
        $s = (new Auth($this->store))->register(['name' => 'Alex', 'email' => $email, 'password' => 'a-test-password-123']);
        if ($verified) { $this->store->db->update('users', ['verified' => true], ['id' => $s['user']['id']]); $s['user']['verified'] = true; }
        return $s;
    }
    private function household(array $user): array { return (new Households($this->store))->create($user['id'], 'Zuhause'); }
    private function categories(string $household): array { return array_values(array_filter($this->store->records($household), fn($r) => $r['kind'] === 'category')); }
    public function testPasswordsAndTokensAreNeverStoredInPlaintext(): void
    {
        $session = $this->user();
        $row = $this->store->row('SELECT * FROM users');
        self::assertTrue(password_verify('a-test-password-123', $row['password_hash']));
        self::assertNull($this->store->row('SELECT * FROM tokens WHERE hash = ?', [$session['token']]));
        self::assertSame($session['user']['id'], (new Auth($this->store))->authenticate('Bearer ' . $session['token'])['id']);
        $this->store->db->update('tokens', ['expires_at' => time() - 1], ['purpose' => 'session']);
        $this->expectException(ApiException::class); $this->expectExceptionCode(401);
        (new Auth($this->store))->authenticate('Bearer ' . $session['token']);
    }
    public function testRegistrationStartsWithOneHousehold(): void
    {
        $session = $this->user();
        $memberships = $this->store->rows('SELECT * FROM memberships WHERE user_id = ?', [$session['user']['id']]);
        self::assertCount(1, $memberships);
        self::assertSame('owner', $memberships[0]['role']);
        self::assertSame('Mein Haushalt', $this->store->row('SELECT name FROM households WHERE id = ?', [$memberships[0]['household_id']])['name']);
    }
    public function testEmailHTMLHasOutlookSafeButtonAndEscapesContent(): void
    {
        $html = Delivery::emailHTML(
            'Willkommen & los',
            "Hallo <Theo>\n\nDein Code: 123",
            'Konta öffnen',
            'konta://verify'
        );
        self::assertStringContainsString('role="presentation"', $html);
        self::assertStringContainsString('mso-padding-alt', $html);
        self::assertStringContainsString('href="konta://verify"', $html);
        self::assertStringContainsString('Hallo &lt;Theo&gt;', $html);
        self::assertStringNotContainsString('Hallo <Theo>', $html);
    }
    public function testCrossHouseholdAccountReferenceIsRejected(): void
    {
        $a = $this->user()['user']; $b = $this->user('sam@example.test')['user'];
        $ha = $this->household($a); $hb = $this->household($b); $r = new Records($this->store);
        $account = $r->save($hb['id'], $b['id'], 'account', Store::id(), ['name' => 'Private account']);
        $category = $this->store->records($ha['id'])[0];
        $this->expectException(ApiException::class); $this->expectExceptionCode(404);
        $r->save($ha['id'], $a['id'], 'transaction', Store::id(), ['name' => 'Attack', 'accountID' => $account['id'], 'categoryID' => $category['id']]);
    }
    public function testNonMembersCannotMutateRecords(): void
    {
        $a = $this->user()['user']; $b = $this->user('sam@example.test')['user']; $h = $this->household($a);
        $this->expectException(ApiException::class); $this->expectExceptionCode(403);
        (new Records($this->store))->save($h['id'], $b['id'], 'account', Store::id(), ['name' => 'Attack']);
    }
    public function testExistingUserGetsNotificationAndMustAcceptInvitation(): void
    {
        $owner = $this->user()['user']; $guest = $this->user('sam@example.test')['user']; $h = $this->household($owner);
        $service = new Households($this->store); $invite = $service->invite($h['id'], $owner, 'SAM@example.test');
        self::assertNotNull($this->store->row('SELECT * FROM notifications WHERE user_id = ?', [$guest['id']]));
        self::assertNull($this->store->row('SELECT * FROM memberships WHERE household_id = ? AND user_id = ?', [$h['id'], $guest['id']]));
        $service->respond($invite['id'], $guest, true);
        self::assertSame('member', $this->store->membership($h['id'], $guest['id'])['role']);
        $this->expectExceptionCode(409); $this->expectException(ApiException::class);
        $service->respond($invite['id'], $guest, true);
    }
    public function testNewEmailGetsInvitationMailAndDeduplicatesInvite(): void
    {
        $owner = $this->user()['user']; $h = $this->household($owner); $s = new Households($this->store);
        $first = $s->invite($h['id'], $owner, 'new@example.test'); $second = $s->invite($h['id'], $owner, 'new@example.test');
        self::assertSame($first['id'], $second['id']);
        self::assertCount(1, $this->store->rows('SELECT * FROM outbox WHERE recipient = ? AND channel = ?', ['new@example.test', 'email']));
        self::assertCount(0, $this->store->rows('SELECT * FROM notifications'));
    }
    public function testInvitationRequiresVerifiedRecipient(): void
    {
        $owner = $this->user()['user']; $guest = $this->user('sam@example.test', false)['user']; $h = $this->household($owner);
        $s = new Households($this->store); $i = $s->invite($h['id'], $owner, $guest['email']);
        $this->expectException(ApiException::class); $this->expectExceptionCode(403); $s->respond($i['id'], $guest, true);
    }
    public function testWrongRecipientCannotAccept(): void
    {
        $owner = $this->user()['user']; $guest = $this->user('sam@example.test')['user']; $h = $this->household($owner);
        $s = new Households($this->store); $i = $s->invite($h['id'], $owner, 'someone@example.test');
        $this->expectException(ApiException::class); $this->expectExceptionCode(404); $s->respond($i['id'], $guest, true);
    }
    public function testExpiredInvitationCannotBeAccepted(): void
    {
        $owner = $this->user()['user']; $guest = $this->user('sam@example.test')['user']; $h = $this->household($owner);
        $s = new Households($this->store); $i = $s->invite($h['id'], $owner, $guest['email']);
        $this->store->db->update('invitations', ['expires_at' => time() - 1], ['id' => $i['id']]);
        $this->expectException(ApiException::class); $this->expectExceptionCode(409); $s->respond($i['id'], $guest, true);
    }
    public function testOptimisticConcurrencyProtectsEdits(): void
    {
        $u = $this->user()['user']; $h = $this->household($u); $s = new Records($this->store); $id = Store::id();
        $r = $s->save($h['id'], $u['id'], 'account', $id, ['name' => 'Giro']);
        $s->save($h['id'], $u['id'], 'account', $id, array_replace($r, ['amount' => 123456]));
        $this->expectException(ApiException::class); $this->expectExceptionCode(409);
        $s->save($h['id'], $u['id'], 'account', $id, array_replace($r, ['amount' => 500]));
    }
    public function testAmountsRejectFloatInsteadOfRounding(): void
    {
        $u = $this->user()['user']; $h = $this->household($u);
        $this->expectException(ApiException::class); $this->expectExceptionCode(422);
        (new Records($this->store))->save($h['id'], $u['id'], 'account', Store::id(), ['name' => 'Giro', 'amount' => 0.1]);
    }
    public function testDeletingReferencedAccountIsRejected(): void
    {
        $u = $this->user()['user']; $h = $this->household($u); $s = new Records($this->store);
        $a = $s->save($h['id'], $u['id'], 'account', Store::id(), ['name' => 'Giro']); $category = $this->categories($h['id'])[0];
        $s->save($h['id'], $u['id'], 'transaction', Store::id(), ['name' => 'Miete', 'amount' => -10000, 'accountID' => $a['id'], 'categoryID' => $category['id']]);
        $this->expectException(ApiException::class); $this->expectExceptionCode(409); $s->delete($h['id'], $u['id'], $a['id'], 1);
    }
    public function testManualCategoryAndSinglePlanMatch(): void
    {
        $u = $this->user()['user']; $h = $this->household($u); $s = new Records($this->store);
        $a = $s->save($h['id'], $u['id'], 'account', Store::id(), ['name' => 'Giro']); $categories = $this->categories($h['id']);
        $base = ['name' => 'Miete', 'amount' => -10000, 'accountID' => $a['id'], 'categoryID' => $categories[0]['id']];
        $plan = $s->save($h['id'], $u['id'], 'transaction', Store::id(), $base + ['state' => 'planned']);
        $real = $s->save($h['id'], $u['id'], 'transaction', Store::id(), array_replace($base, ['categoryID' => $categories[1]['id']]));
        $key = 'transaction:' . $plan['id'] . ':' . $plan['date'];
        $real = $s->save($h['id'], $u['id'], 'transaction', $real['id'], array_replace($real, ['matchedPlanKey' => $key]));
        self::assertSame($categories[1]['id'], $real['categoryID']);
        $this->expectException(ApiException::class); $this->expectExceptionCode(409);
        $s->save($h['id'], $u['id'], 'transaction', Store::id(), $base + ['matchedPlanKey' => $key]);
    }
    public function testCsvHintsPreferPurposeAndKeepDatesOutOfMoney(): void
    {
        $rows = (new CsvParser())->parse("Kontoumsätze\nBuchungstag;Wertstellung;Buchungstext;Verwendungszweck;Betrag\n05.09.2026;06.09.2026;LASTSCHRIFT;Miete September;-1.234,56\n");
        self::assertSame(-123456, $rows[0]['amount']); self::assertSame('Miete September', $rows[0]['purpose']); self::assertSame('2026-09-05', $rows[0]['date']);
    }
    public function testCsvDebitCreditAndQuotedMultiline(): void
    {
        $rows = (new CsvParser())->parse("Datum;Soll;Haben;Verwendungszweck\n05.09.2026;123,45;;\"Text\nFortsetzung\"\n06.09.2026;;1.234,56;Gehalt\n");
        self::assertSame([-12345, 123456], array_column($rows, 'amount'));
        self::assertSame("Text\nFortsetzung", $rows[0]['purpose']);
        self::assertSame(-12345, CsvParser::cents('(123,45)'));
    }
    public function testBadCsvRejectsWholeFile(): void
    {
        $this->expectException(ApiException::class);
        (new CsvParser())->parse("Datum;Betrag\n31.02.2026;12,00\n");
    }
    public function testRateLimitIsEnforced(): void
    {
        $this->store->limit('test', 1); $this->expectException(ApiException::class); $this->expectExceptionCode(429); $this->store->limit('test', 1);
    }
    public function testSupportRequestIsValidatedAndQueued(): void
    {
        (new Support($this->store))->submit([
            'name' => "Alex\nBeispiel",
            'email' => 'alex@example.test',
            'topic' => 'daten',
            'message' => 'Beim CSV-Import erscheint eine verständliche Testmeldung.',
        ]);
        $mail = $this->store->row('SELECT * FROM outbox WHERE channel = ?', ['email']);
        self::assertNotNull($mail);
        self::assertSame('news@konta-finance.com', $mail['recipient']);
        $payload = json_decode($mail['payload'], true, 512, JSON_THROW_ON_ERROR);
        self::assertStringContainsString('Alex Beispiel', $payload['body']);
        self::assertStringNotContainsString("Alex\nBeispiel", $payload['body']);
    }
    public function testSupportHoneypotDoesNotQueueMail(): void
    {
        (new Support($this->store))->submit(['company' => 'Spam GmbH']);
        self::assertCount(0, $this->store->rows('SELECT * FROM outbox'));
    }
    public function testAppleSignatureIsJOSECompatible(): void
    {
        $key = openssl_pkey_new(['private_key_type' => OPENSSL_KEYTYPE_EC, 'curve_name' => 'prime256v1']);
        openssl_sign('test', $der, $key, OPENSSL_ALGO_SHA256);
        self::assertSame(64, strlen(ApplePush::rawSignature($der)));
    }
    public function testMatchedBookingSurvivesSourceDeletionButCannotBecomeAPlan(): void
    {
        $u = $this->user()['user']; $h = $this->household($u); $s = new Records($this->store);
        $a = $s->save($h['id'], $u['id'], 'account', Store::id(), ['name' => 'Giro']);
        $base = ['name' => 'Miete', 'amount' => -10000, 'accountID' => $a['id'], 'categoryID' => $this->categories($h['id'])[0]['id']];
        $plan = $s->save($h['id'], $u['id'], 'transaction', Store::id(), $base + ['state' => 'planned']);
        $real = $s->save($h['id'], $u['id'], 'transaction', Store::id(), $base + ['matchedPlanKey' => 'transaction:' . $plan['id'] . ':' . $plan['date']]);
        $s->delete($h['id'], $u['id'], $plan['id'], $plan['version']);
        $real = $s->save($h['id'], $u['id'], 'transaction', $real['id'], array_replace($real, ['notes' => 'Audit retained']));
        self::assertSame('Audit retained', $real['notes']);
        $this->store->db->delete('records', ['id' => $plan['id']]);
        $real = $s->save($h['id'], $u['id'], 'transaction', $real['id'], array_replace($real, ['notes' => 'After source purge']));
        self::assertSame('After source purge', $real['notes']);
        $this->expectException(ApiException::class); $this->expectExceptionCode(422);
        $s->save($h['id'], $u['id'], 'transaction', $real['id'], array_replace($real, ['state' => 'planned']));
    }
    public function testConfirmingSameAutomaticCategoryMakesItManual(): void
    {
        $u = $this->user()['user']; $h = $this->household($u); $s = new Records($this->store);
        $a = $s->save($h['id'], $u['id'], 'account', Store::id(), ['name' => 'Giro']);
        $r = $s->save($h['id'], $u['id'], 'transaction', Store::id(), ['name' => 'Import', 'accountID' => $a['id'], 'categoryID' => $this->categories($h['id'])[0]['id'], 'categorySource' => 'keyword', 'confidence' => 0.75], true);
        $r = $s->save($h['id'], $u['id'], 'transaction', $r['id'], array_replace($r, ['categorySource' => 'manual']));
        self::assertSame('manual', $r['categorySource']); self::assertNull($r['confidence']);
    }
}
