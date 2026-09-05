# Konta

**Dein Geld. Ein guter Plan.** Native Finanzplanung für iPhone, iPad und Mac, mit einer kleinen CakePHP-API. Oberfläche auf Deutsch, Euro-Beträge centgenau, mehrere Haushalte mit Einladungen und klaren Zugriffsgrenzen.

## Drei Ordner

- **`ios/`** — SwiftUI-App für iOS/iPadOS 26, native schwebende Liquid-Glass-Tabbar; enthält das lokale Swift-Paket `KontaKit` für beide Apps.
- **`macos/`** — eigenständige SwiftUI-App für macOS 26 mit Seitenleiste, Fenstern, Menübefehlen und Systemeinstellungen. Kein Catalyst, kein WebView.
- **`api/`** — CakePHP 5.4, PHP ab 8.3, SQLite oder MySQL/MariaDB, JSON-API, Dateispeicher und E-Mail/APNs-Zustellung.

Die Xcode-Projekte sind enthalten. `project.yml` ist jeweils die Quelle für eine erneute Generierung mit XcodeGen. Beide Apps verwenden dieselbe Bundle-ID für einen gemeinsamen App-Store-Eintrag mit iOS- und macOS-Plattform.

## Lokal starten

```sh
# PHP 8.3+ mit intl, mbstring, PDO SQLite/MySQL, curl, openssl, SimpleXML
cd api
composer install --no-interaction --no-scripts
bash bin/serve.sh
```

Die API läuft unter `http://localhost:8765`, der Gesundheitscheck unter `/health`. `api/storage` wird automatisch eingerichtet, Migrationen laufen beim Start. Eine `.env` ist optional; `api/.env.example` enthält alle Einstellungen. Bei mehreren PHP-Versionen:

```sh
KONTA_PHP=/pfad/zu/php bash api/bin/serve.sh
```

Auf diesem Entwicklungsrechner steht eine moderne PHP-Version unter `/opt/homebrew/opt/php@8.4/bin/php` zur Verfügung; das normale `php` im PATH ist älter.

Alternativ läuft ausschließlich die API in Docker:

```sh
docker compose -f api/compose.yml up --build -d
```

SQLite und hochgeladene Dateien liegen dann im persistenten Volume `konta-data`. Nur Port 8765 wird veröffentlicht. Mit `KONTA_PORT=8766` lässt sich ein anderer Port wählen.

Öffne anschließend `ios/Konta.xcodeproj` oder `macos/Konta.xcodeproj`, wähle das Scheme **Konta** und starte. Für den iOS-Simulator ist keine Developer-Signierung nötig. Debug-Builds erlauben HTTP ausschließlich für localhost; ein echtes iPhone und Release-Builds benötigen eine HTTPS-API. In der Anmeldung lässt sich die Server-Adresse einstellen.

**Konta kennenlernen** öffnet eine ausdrücklich gekennzeichnete Vorschau mit Beispieldaten. Diese Vorschau ist schreibgeschützt. Das Launch-Argument `--demo` startet dieselbe Vorschau direkt.

## Enthaltene Funktionen

- Registrierung, Login, E-Mail-Bestätigung, Passwort-Reset, Profil, Abmeldung und Benutzerkontolöschung.
- Beliebig viele Haushalte; Haushalt wechseln, Mitglieder einladen, Einladungen annehmen/ablehnen/widerrufen, Mitglied entfernen, Haushalt verlassen, Leitung übertragen und Haushalt löschen.
- Konten mit Startsaldo und Datum, Kategorien mit Stichwörtern/Budgets, Buchungen, manuelle Planung, Verträge, Gehälter, Kredite, Notizen und Tags.
- Native Vermögensprognose, monatliche Einnahmen/Ausgaben, Sparziel und Kategorienübersicht; gemeinsamer Zeitraum für Dashboard und Buchungslisten.
- Wiederholungen von einmalig bis jährlich, Intervall-Faktor, Monatsend-Korrektur, Ende, Pausierung und Kreditraten mit Zinsen und begrenzter Schlussrate.
- CSV-Import mit Erkennung von Datum/Betrag/Zweck, deutscher Zahlenschreibweise, Soll/Haben, Windows-1252, mehrzeiligen Feldern und überschneidungsfester Deduplizierung.
- Stichwort-Kategorisierung ohne API-Schlüssel; optionale OpenAI-Kategorisierung in Gruppen von 25 nach Freigabe durch die Haushaltsleitung. Manuelle Kategorien und Planabgleiche werden geschützt.
- Expliziter Abgleich gebuchter Zahlungen mit Plänen. Der Plan bleibt über seine Kennung nachvollziehbar und wird in Summen nicht erneut gezählt. Überfällige Pläne werden angezeigt.
- Native Apple-Push-Mitteilungen für Einladungen, stiller Datenabgleich per APNs sowie lokale Erinnerungen an Kündigungsfristen. Beim Aktivieren und auf aktuellen Snapshots werden Fristen auf dem Gerät geplant.
- Verschlüsselter Offline-Lesezugriff auf den letzten Haushalt; Schreiben benötigt eine Verbindung. JSON-Export des Haushalts über den nativen Dateidialog.

## Einladungen und Mitteilungen

Eine Einladung gibt noch keinen Datenzugriff. Beide Seiten müssen ihre E-Mail-Adresse bestätigen. Existierende Nutzer erhalten eine gespeicherte Mitteilung und eine APNs-Zustellung an registrierte Geräte. Neue Nutzer erhalten eine E-Mail; nach Registrierung mit derselben Adresse erscheint die Einladung automatisch. Einladungen gelten sieben Tage.

Lokal legt der Mailtransport private `.eml`-Dateien in `api/storage/mail` ab. Dort steht auch der Bestätigungscode für lokale Testkonten. Für echte Zustellung `MAIL_TRANSPORT=smtp` und SMTP-Daten in `api/.env` setzen. APNs benötigt einen `.p8`-Schlüssel und die Team-/Key-/Bundle-ID, siehe [Apple-Einrichtung](APPLE_SETUP.md).

Die Zustellung verwendet eine persistente Outbox mit Wiederholungen. Nach relevanten HTTP-Anfragen wird sie sofort verarbeitet. Richte für zuverlässige Wiederholungen und Bereinigung zusätzlich den Wartungsjob ein:

```cron
* * * * * cd /pfad/zu/konta/api && /usr/bin/php bin/cake.php maintenance >> /var/log/konta-maintenance.log 2>&1
```

Für Docker auf dem Host entsprechend `docker compose -f /pfad/zu/konta/api/compose.yml exec -T --user www-data api php bin/cake.php maintenance` ausführen. Fehlgeschlagene Zustellungen werden bis zu zwölfmal mit zunehmendem Abstand versucht. Ohne registriertes Gerät bleibt die Einladung im App-Postfach sichtbar. APNs garantiert keine sofortige Zustellung; beim Öffnen und über „Aktualisieren“ wird zusätzlich geladen.

## API bereitstellen

1. PHP ab 8.3 und die oben genannten Erweiterungen installieren, `composer install --no-dev --no-scripts --optimize-autoloader` ausführen.
2. Den Webserver-DocumentRoot **ausschließlich auf `api/webroot`** setzen; alle anderen Pfade auf `index.php` routen. `storage`, `.env`, `vendor` und `.p8` dürfen nicht öffentlich erreichbar sein.
3. `.env.example` nach `.env` kopieren. HTTPS, SMTP und optional MySQL/OpenAI/APNs konfigurieren. `DB_DRIVER=mysql` nutzt die Datenbankparameter; ohne Konfiguration funktioniert SQLite.
4. `storage`, `tmp`, `logs` für den PHP-Prozess schreibbar machen, `php bin/cake.php migrations migrate --no-lock` ausführen und den Wartungsjob einrichten.
5. Die produktive HTTPS-URL steht in `ios/Config/Shared.xcconfig`; lokale Abweichungen gehören in `Signing.local.xcconfig`. Backups von Datenbank und `storage/uploads` gemeinsam erstellen.

Auf Shared Hosting kann die Domainwurzel auf dem Repository bleiben: Die Root-`.htaccess` leitet intern ausschließlich nach `api/webroot` weiter. `/` zeigt die minimale Vorschauseite, `/health` und `/v1/*` bleiben API-Endpunkte. Nach jedem `git pull` genügt `bash api/bin/deploy.sh`; die nicht versionierte `api/.env` bleibt dabei erhalten.

SQLite eignet sich für eine einzelne API-Instanz; für mehrere Serverinstanzen MySQL und gemeinsam verfügbaren Dateispeicher verwenden. Die aktuell enthaltene Dateispeicherung ist lokal, ohne Redis, MinIO oder separate Worker.

## Prüfen

```sh
bash api/bin/test.sh                         # isolierte SQLite-Datenbank, PHPUnit
python3 api/tests/http_smoke.py              # echter lokaler HTTP-Server, Testkonten, keine externen Dienste
swift test --package-path ios/KontaKit       # Geld-, Kalender- und JSON-Vertragstests
xcodebuild -project ios/Konta.xcodeproj -scheme Konta \
  -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
xcodebuild -project macos/Konta.xcodeproj -scheme Konta \
  -destination 'platform=macOS' CODE_SIGNING_ALLOWED=NO build
```

`KONTA_PHP` kann auch vor die beiden API-Testbefehle gesetzt werden. Der HTTP-Test erzeugt eine ausschließlich synthetische Antwortdatei für den Swift-Decodierungstest. Testdatenbanken werden anschließend gelöscht.

Die Finanzberechnung wurde zusätzlich über alle 24 Monate der vorhandenen Excel-Referenz abgeglichen: Einnahmen, Ausgaben und Gesamtvermögen stimmen nach Rundung der Eingabebeträge auf Cent überein. Die ursprüngliche Tabelle enthält Gehaltswerte mit Bruchteilen eines Cents; dadurch weicht ihr kumulierter, ungerundeter Stand um höchstens einen Cent ab.

Beide Xcode-Schemes enthalten einen nativen Oberflächentest für Navigation und die schreibgeschützte Vorschau. Mit konfiguriertem Team lassen sie sich über **Product → Test** starten; für iOS ein Simulatorgerät auswählen.

Lokaler Prüfstand: 19 API-Tests, 12 Swift-Tests, HTTP-Integrationstest und iPhone-Navigationstest bestanden; beide Release-Builds erfolgreich. Der Mac-Klicktest konnte auf diesem Rechner wegen eines Timeouts beim Aktivieren des macOS-Automationsmodus nicht starten.

## Veröffentlichung

Die Projekte enthalten App-Icons, Privacy Manifest, APNs-Entitlements, Mac-Sandbox und Release-Konfigurationen. Eine erfolgreiche lokale Kompilierung ist noch keine signierte App-Store-Version. [APPLE_SETUP.md](APPLE_SETUP.md) führt durch App-ID, automatische Profile, APNs, App Store Connect und TestFlight. Für den Store müssen die endgültige Bundle-ID, das Apple-Team, die produktive API, Datenschutz-/Support-URLs, Screenshots und Review-Angaben eingerichtet und reale SMTP-/APNs-/KI-Verbindungen geprüft werden.

**Konta** ist der vorläufige Produktname; die Verfügbarkeit in App Store Connect und als Marke ist noch nicht geprüft. Die vorhandene Referenzdatei liegt unter `api/docs/reference.xlsx`. Der alte Django-/Next.js-Stack wurde entfernt; dieses Projekt übernimmt keine alten Datenbanken automatisch.
