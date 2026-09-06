#!/usr/bin/env python3
"""Exercise the real CakePHP HTTP boundary against an isolated SQLite database."""
import json, os, pathlib, socket, subprocess, sys, tempfile, time, urllib.request, urllib.error, uuid, re
root = pathlib.Path(__file__).resolve().parents[1]
php = os.environ.get('KONTA_PHP', 'php')
existing_mail = set((root/'storage/mail').glob('*.eml'))

def request(path, method='GET', data=None, token=None, raw=None, content_type='application/json', expected=200):
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    headers = {'Content-Type': content_type, 'Accept': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response: status, body = response.status, response.read()
    except urllib.error.HTTPError as error: status, body = error.code, error.read()
    assert status == expected, (method, path, status, body.decode()[:500])
    return json.loads(body)

with tempfile.TemporaryDirectory(prefix='konta-test-http-') as temp:
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0)); port = reserve.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    env = dict(os.environ, DB_DRIVER='sqlite', DB_DATABASE=temp+'/konta-test-http.sqlite', MAIL_TRANSPORT='file', OPENAI_API_KEY='', APNS_KEY_PATH='')
    subprocess.run([php, 'bin/cake.php', 'migrations', 'migrate', '--no-lock'], cwd=root, env=env, check=True, stdout=subprocess.DEVNULL)
    log = open(temp+'/server.log', 'w+')
    server = subprocess.Popen([php, '-S', f'127.0.0.1:{port}', '-t', 'webroot', 'webroot/index.php'], cwd=root, env=env, stdout=log, stderr=log)
    try:
        for _ in range(40):
            try: request('/health'); break
            except urllib.error.URLError: time.sleep(.1)
        request('/v1/bootstrap', expected=401)
        suffix = uuid.uuid4().hex[:8]
        support_email = f'native-smoke-support-{suffix}@example.test'
        request('/v1/support/contact', 'POST', {'name':'Alex Beispiel', 'email':support_email, 'topic':'daten', 'message':'Mein CSV-Import zeigt eine synthetische Testmeldung.'}, expected=202)
        request('/v1/support/contact', 'POST', {'name':'A', 'email':'invalid', 'topic':'other', 'message':'kurz'}, expected=422)
        assert any(support_email in path.read_text() for path in (root/'storage/mail').glob('*.eml') if path not in existing_mail)
        email = f'native-smoke-owner-{suffix}@example.test'
        owner = request('/v1/auth/register', 'POST', {'name':'Alex', 'email':email,'password':'test-password-12345'}, expected=201)
        token = owner['token']
        assert 'password' not in owner['user']
        initial = request('/v1/bootstrap', token=token)
        assert len(initial['households']) == 1 and initial['households'][0]['name'] == 'Mein Haushalt'
        initial_household_id = initial['households'][0]['id']
        request('/v1/auth/login', 'POST', {'email':email, 'password':'incorrect'}, expected=401)
        request('/v1/auth/login', 'POST', {'email':email, 'password':'test-password-12345'})
        household = request('/v1/households', 'POST', {'name':'Vertragstest'}, token, expected=201)
        h = household['id']
        snap = request(f'/v1/households/{h}/snapshot', token=token)
        assert len(snap['records']) == 23
        cat = snap['records'][0]['id']
        account_id = str(uuid.uuid4())
        account = request(f'/v1/households/{h}/records/account/{account_id}', 'PUT', {'name':'Testkonto', 'amount':123456, 'date':'2026-09-01'}, token)
        transaction = {'name':'Testausgabe', 'amount':-12345, 'date':'2026-09-05', 'accountID':account_id, 'categoryID':cat}
        booking_id = str(uuid.uuid4())
        saved = request(f'/v1/households/{h}/records/transaction/{booking_id}', 'PUT', transaction, token)
        assert saved['amount'] == -12345 and saved['version'] == 1
        request(f'/v1/households/{h}/records/transaction/{booking_id}', 'PUT', transaction, token, expected=409)
        stranger = request('/v1/auth/register', 'POST', {'name':'Sam','email':f'native-smoke-guest-{suffix}@example.test','password':'test-password-67890'}, expected=201)
        request(f'/v1/households/{h}/snapshot', token=stranger['token'], expected=403)
        request(f'/v1/households/{h}/records/account/{account_id}', 'PUT', account, stranger['token'], expected=403)
        request(f'/v1/households/{h}/invitations', 'POST', {'email':stranger['user']['email']}, token, expected=403)
        def verify(address, session):
            for path in (root/'storage/mail').glob('*.eml'):
                if path in existing_mail: continue
                contents = path.read_text()
                if f'To: {address}\n' in contents:
                    assert 'Content-Type: multipart/alternative' in contents
                    assert 'Content-Type: text/plain' in contents
                    assert 'Content-Type: text/html' in contents
                    assert 'mso-padding-alt:' in contents
                    code = re.search(r'\b[a-f0-9]{64}\b', contents).group()
                    request('/v1/auth/verify', 'POST', {'code':code})
                    request('/v1/auth/verify', 'POST', {'code':code}, expected=422)
                    return
            raise AssertionError('Verification email missing')
        verify(email, token); verify(stranger['user']['email'], stranger['token'])
        invitation = request(f'/v1/households/{h}/invitations', 'POST', {'email':stranger['user']['email']}, token, expected=201)
        inbox = request('/v1/bootstrap', token=stranger['token'])
        assert inbox['invitations'][0]['id'] == invitation['id'] and inbox['notifications']
        request('/v1/invitations/'+invitation['id'], 'POST', {'accept':True}, stranger['token'])
        request(f'/v1/households/{h}/snapshot', token=stranger['token'])
        request(f'/v1/households/{h}', 'PATCH', household, stranger['token'], expected=403)
        boundary = 'KontaTestBoundary'
        csv = 'Buchungstag;Wertstellung;Buchungstext;Verwendungszweck;Betrag\n04.09.2026;05.09.2026;LASTSCHRIFT;Miete;-1.234,56\n'
        multipart = (f'--{boundary}\r\nContent-Disposition: form-data; name="accountID"\r\n\r\n{account_id}\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.csv"\r\nContent-Type: text/csv\r\n\r\n{csv}\r\n--{boundary}--\r\n').encode()
        for imported, duplicates in [(1,0),(0,1)]:
            upload = request(f'/v1/households/{h}/uploads', 'POST', token=token, raw=multipart, content_type='multipart/form-data; boundary='+boundary, expected=201)
            assert upload['imported'] == imported and upload['duplicates'] == duplicates
        snapshot = request(f'/v1/households/{h}/snapshot', token=token)
        assert sum(r['amount'] for r in snapshot['records'] if r['kind']=='transaction') == -135801
        fixture = root.parent/'ios/KontaKit/Tests/KontaKitTests/Fixtures/snapshot.json'
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n')
        request(f'/v1/households/{h}/records/{account_id}', 'DELETE', {'version':1}, token, expected=409)
        request(f'/v1/households/{h}/members/'+stranger['user']['id'], 'DELETE', {}, token)
        request(f'/v1/households/{h}/snapshot', token=stranger['token'], expected=403)
        request(f'/v1/households/{h}', 'DELETE', {'confirmation':'Vertragstest'}, token)
        request(f'/v1/households/{initial_household_id}', 'DELETE', {'confirmation':'Mein Haushalt'}, token)
        request('/v1/me', 'DELETE', {'password':'test-password-12345'}, token)
        request('/v1/bootstrap', token=token, expected=401)
        print('HTTP smoke passed: support, auth, email verification, isolation, roles, invitations, CSV deduplication, conflicts, deletion, and Swift snapshot fixture.')
    except Exception:
        log.flush(); log.seek(0); print(log.read()[-3000:], file=sys.stderr); raise
    finally:
        server.terminate(); server.wait(timeout=5); log.close()
        for path in set((root/'storage/mail').glob('*.eml')) - existing_mail:
            if 'native-smoke-' in path.read_text(): path.unlink()
