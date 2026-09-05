<?php
declare(strict_types=1);
namespace App\Service;

final class ApplePush
{
    private static function b64(string $value): string { return rtrim(strtr(base64_encode($value), '+/', '-_'), '='); }
    public static function rawSignature(string $der): string
    {
        $offset = 2;
        if (ord($der[1]) & 0x80) { $offset += ord($der[1]) & 0x7f; }
        $parts = [];
        for ($i = 0; $i < 2; $i++) {
            if (ord($der[$offset++]) !== 2) { throw new \RuntimeException('Invalid ECDSA signature'); }
            $length = ord($der[$offset++]);
            $parts[] = str_pad(ltrim(substr($der, $offset, $length), "\0"), 32, "\0", STR_PAD_LEFT);
            $offset += $length;
        }
        return implode('', $parts);
    }
    public function send(array $device, array $payload): void
    {
        $keyPath = getenv('APNS_KEY_PATH');
        $topic = getenv('APNS_TOPIC');
        if (!$keyPath || !$topic || !getenv('APNS_TEAM_ID') || !getenv('APNS_KEY_ID')) { throw new \RuntimeException('APNs is not configured'); }
        $input = self::b64(Store::json(['alg' => 'ES256', 'kid' => getenv('APNS_KEY_ID')])) . '.' . self::b64(Store::json(['iss' => getenv('APNS_TEAM_ID'), 'iat' => time()]));
        $key = openssl_pkey_get_private(file_get_contents($keyPath));
        if (!$key || !openssl_sign($input, $signature, $key, OPENSSL_ALGO_SHA256)) { throw new \RuntimeException('APNs signing failed'); }
        $jwt = $input . '.' . self::b64(self::rawSignature($signature));
        $silent = $payload['silent'] ?? false;
        $aps = $silent ? ['content-available' => 1] : ['alert' => ['title' => $payload['title'], 'body' => $payload['body']], 'sound' => 'default', 'category' => 'HOUSEHOLD_INVITATION'];
        $host = $device['environment'] === 'development' ? 'api.sandbox.push.apple.com' : 'api.push.apple.com';
        $curl = curl_init('https://' . $host . '/3/device/' . $device['token']);
        curl_setopt_array($curl, [CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 15, CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_2_0,
            CURLOPT_HTTPHEADER => ['authorization: bearer ' . $jwt, 'apns-topic: ' . $topic, 'apns-push-type: ' . ($silent ? 'background' : 'alert'), 'apns-priority: ' . ($silent ? '5' : '10'), 'apns-expiration: ' . (time() + 3600)],
            CURLOPT_POSTFIELDS => Store::json(['aps' => $aps] + $payload)]);
        $response = curl_exec($curl);
        $status = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
        $reason = is_string($response) ? (json_decode($response, true)['reason'] ?? '') : '';
        if ($status === 410 || ($status === 400 && $reason === 'BadDeviceToken')) {
            (new Store())->db->delete('devices', ['token' => $device['token']]);
            return;
        }
        if ($status !== 200) { throw new \RuntimeException('APNs delivery failed: ' . $status); }
    }
}
