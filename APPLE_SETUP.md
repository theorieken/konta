# Konta mit deinem Apple-Developer-Account veröffentlichen

Nutze dein bestehendes Apple-Developer-Team. Für Konta legst du eine eigene App-ID und einen App-Store-Eintrag an. Die zugehörigen Entwicklungs- und Distributionsprofile kann Xcode automatisch verwalten. Eine zusätzliche Apple-ID ist dafür nicht nötig.

## 1. Endgültige Kennung festlegen

Wähle eine dauerhafte Bundle-ID, zum Beispiel `de.deinefirma.konta`. Die im Projekt gesetzte `de.konta.app` ist ein Platzhalter. iOS und macOS verwenden dieselbe Kennung; Apple unterstützt eine App-ID über mehrere Plattformen. Prüfe den Namen „Konta“ vor der Veröffentlichung auf Verfügbarkeit. [Apple: App-ID registrieren](https://developer.apple.com/help/account/identifiers/register-an-app-id/)

## 2. App-ID im Developer-Portal anlegen

1. Öffne **Certificates, Identifiers & Profiles → Identifiers → +**.
2. Wähle **App IDs → App**, Beschreibung „Konta“.
3. Wähle **Explicit** und trage deine Bundle-ID ein.
4. Aktiviere **Push Notifications** und registriere die App-ID.

Die Kennung muss exakt mit beiden Xcode-Targets übereinstimmen. Die bestehenden Entitlements aktivieren Push; macOS erhält zusätzlich App Sandbox, ausgehende Netzwerkverbindungen und Zugriff auf vom Nutzer ausgewählte Dateien. [Apple: App-ID und Capabilities](https://developer.apple.com/help/account/identifiers/register-an-app-id/)

## 3. Xcode und Profile verbinden

1. Melde dich in **Xcode → Settings → Accounts** mit deinem Apple-Account an und wähle dein Team.
2. Kopiere `ios/Config/Signing.local.xcconfig.example` nach `ios/Config/Signing.local.xcconfig`.
3. Trage `DEVELOPMENT_TEAM`, `PRODUCT_BUNDLE_IDENTIFIER` und die produktive `KONTA_API_URL` ein. Beide Projekte lesen diese eine Datei; sie ist vom Git-Tracking ausgeschlossen.
4. Öffne beide `.xcodeproj`-Dateien. Unter **Signing & Capabilities** muss **Automatically manage signing** aktiv sein und dein Team erscheinen.
5. Starte zunächst auf deinem iPhone und auf dem Mac. Xcode erstellt die nötigen Profile für diese App-ID und Geräte.

Für App-Store-Uploads kann Xcode ebenfalls das Distributionsprofil verwalten. Wenn du Profile manuell anlegen willst: **Profiles → + → App Store Connect**, passende App-ID und Distributionszertifikat wählen und das Profil herunterladen. Beim Mac entsprechend den Mac-App-Store-Profiltyp wählen. [Apple: App-Store-Provisioning-Profil](https://developer.apple.com/help/account/provisioning-profiles/create-an-app-store-provisioning-profile/)

## 4. Apple-Push aktivieren

1. Im Developer-Portal **Keys → +** öffnen und einen Schlüssel mit **Apple Push Notifications service (APNs)** erstellen.
2. `.p8` herunterladen und außerhalb von Repository und Webroot speichern. Team-ID und Key-ID notieren.
3. Auf dem API-Server `APNS_KEY_PATH`, `APNS_KEY_ID`, `APNS_TEAM_ID` und `APNS_TOPIC` setzen. `APNS_TOPIC` entspricht der endgültigen Bundle-ID.
4. Bei Docker den Schlüssel zusätzlich als schreibgeschützte Datei in den Container mounten und den Containerpfad konfigurieren.
5. In beiden Apps **Einstellungen → Mitteilungen aktivieren** auswählen. Prüfe eine Einladung zwischen zwei echten Testkonten.

Debug-Entitlements verwenden `development`, Release-Entitlements `production`. TestFlight liefert über die Produktionsumgebung. Die API sendet HTTP/2-Anfragen mit einem ES256-Token. Ein fehlender Schlüssel blockiert keine Einladung im App-Postfach; die Outbox hält die Push-Zustellung zur Wiederholung vor. [Apple: Tokenbasierte APNs-Verbindung](https://developer.apple.com/documentation/usernotifications/establishing-a-token-based-connection-to-apns)

## 5. App in App Store Connect anlegen

1. In **App Store Connect → Apps → + → New App** gehen.
2. **iOS** und **macOS** auswählen, soweit die Oberfläche beide Plattformen beim Erstellen anbietet; die zweite Plattform kann ansonsten dem App-Eintrag hinzugefügt werden.
3. Name „Konta“, primäre Sprache Deutsch, deine Bundle-ID und eine interne SKU, beispielsweise `konta-001`, eintragen.
4. Die einzelnen Plattform-Versionen bekommen ihre jeweiligen Builds und Screenshots.

Vor dem Erstellen müssen eventuell aktuelle Verträge im Account bestätigt werden. Der Account Holder/Admin verwaltet die nötigen Zugriffe. [Apple: Neue App anlegen](https://developer.apple.com/help/app-store-connect/create-an-app-record/add-a-new-app/)

## 6. TestFlight und Review

Für jedes Projekt das Scheme **Konta** auf ein echtes Gerät/generisches iOS-Gerät beziehungsweise **Any Mac** setzen, **Product → Archive** wählen und im Organizer **Distribute App → App Store Connect** starten. Xcode validiert Bundle-ID, Entitlements, Zertifikat und Profil. Verwende anschließend die Builds in TestFlight und prüfe die App vor der Store-Einreichung auf echten Geräten.

Vor dem Upload ausfüllen und prüfen:

- Produktive HTTPS-API, erreichbarer SMTP-Versand und Wartungsjob; APNs auf iPhone und Mac testen.
- Endgültiger Name, Kategorie Finanzen, Beschreibung, Keywords und Support-URL.
- Öffentlich erreichbare Datenschutzerklärung mit Betreiber-/Kontaktangaben und passender Beschreibung von Haushaltsdaten, Dateien, APNs und optionaler OpenAI-Verarbeitung. Der Datenschutztext in der App ersetzt diese URL nicht.
- App-Privacy-Angaben passend zum tatsächlichen Betrieb: Identität/Kontakt, Finanzdaten, Nutzerinhalte und Gerätekennung für Push. Das enthaltene Privacy Manifest beschreibt den aktuellen Code, die Angaben in App Store Connect sind zusätzlich nötig.
- Screenshots von iPhone/iPad und Mac, Altersfreigabe, Export-Compliance-Angaben und Review-Notizen.
- Ein funktionsfähiges Review-Konto, Zugriff auf die produktive API und eine Erklärung der Haushalts-/Einladungsfunktionen. Kontolöschung und Passwort-Reset testen.

Die aktuellen Builds wurden lokal ohne Distributionssignierung geprüft. Es wurden noch keine Apple-App-Einträge angelegt, keine Profile im Portal erstellt und keine Builds hochgeladen. Deine privaten Apple-Schlüssel wurden nicht ausgelesen.
