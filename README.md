# Haushalts-Finanzplanung

Selbst gehostete Finanzplanung für einen Haushalt: Einnahmen, Ausgaben,
Verträge, Kredite und eine Prognose bis zum Sparziel.

```bash
bash deploy.sh
```

Danach läuft alles auf **http://localhost:8080**. Beim ersten Aufruf führt die App
durch das Onboarding und legt Benutzer, Konten und Standardkategorien an.

---

## Was die App kann

- **Dashboard** — Vermögensverlauf mit Markierung von *heute*, Kernkennzahlen,
  größte Ausgaben, Kontostände. Zeitraum frei wählbar.
- **Ausgaben** — geplante und gebuchte Ausgaben, Verträge, Kredite.
- **Einnahmen** — regelmäßiges Einkommen und einzelne Zahlungseingänge.
- **CSV-Import** — Kontoauszug der Bank hochladen. Die Umsätze werden gelesen,
  im Hintergrund automatisch kategorisiert und mit den geplanten Transaktionen
  abgeglichen, damit nichts doppelt zählt.
- **Prognose** — aus Verträgen, Krediten und Einkommen entstehen automatisch
  geplante Transaktionen bis zum eingestellten Horizont.
- **Objekt-Drawer** — jedes Objekt lässt sich von jeder Liste aus in einer
  seitlichen Ansicht öffnen, ohne die Seite zu verlassen.

---

## Voraussetzungen

Docker und Docker Compose. Sonst nichts — Datenbank, Redis, MinIO, Backend,
Worker und Frontend laufen als Container.

---

## Kommandos

```bash
bash deploy.sh              # bauen, starten, migrieren, seeden
bash deploy.sh --rebuild    # Images ohne Cache neu bauen
bash deploy.sh --logs       # starten und Logs verfolgen
bash deploy.sh --down       # stoppen, Daten bleiben erhalten
bash deploy.sh --reset      # stoppen und alle Daten löschen
```

### Django-Management

Die Befehle laufen im Backend-Container. `add_user` fragt das Passwort verdeckt
und zweimal ab; `--admin` legt einen Administrator an.

```bash
docker compose exec backend python manage.py add_user theo@example.com --name "Theo"
docker compose exec backend python manage.py add_user admin@example.com --name "Admin" --admin
docker compose exec backend python manage.py reset_data
```

`reset_data` löscht nach Eingabe von `RESET` alle Daten in PostgreSQL und stellt
Standarddaten sowie periodische Aufgaben wieder her. Hochgeladene Dateien in
MinIO und Redis bleiben dabei erhalten. Für einen vollständigen Reset aller
Volumes dient weiterhin `bash deploy.sh --reset`. Für automatisierte Abläufe
kann die Sicherheitsabfrage mit `reset_data --yes` übersprungen werden.

---

## Konfiguration

Alle Werte stehen in `.env.example` und haben einen funktionierenden Standard.
`deploy.sh` legt beim ersten Start eine `.env` an und erzeugt die Secrets. Nur
anfassen, wenn du etwas ändern willst:

| Variable | Bedeutung |
|---|---|
| `DOMAIN`, `SCHEME`, `PORT` | Öffentliche Adresse (Standard `http://localhost:8080`) |
| `POSTGRES_*` | Datenbank |
| `MINIO_*` | Objektspeicher für hochgeladene Dateien |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | KI-Kategorisierung (auch in der UI setzbar) |
| `PREDICTION_HORIZON_MONTHS` | Wie weit die Planung rechnet |
| `BOOTSTRAP_ADMIN_*` | Optionaler Admin statt Onboarding-Assistent |

Ist der gewünschte Port belegt, sucht `deploy.sh` automatisch den nächsten
freien und schreibt ihn in die `.env`.

---

## KI-Kategorisierung

Ohne OpenAI-Key funktioniert der Import vollständig — die Kategorien werden dann
über Stichwörter zugeordnet, die an jeder Kategorie hinterlegt sind. Mit Key
(Einstellungen → KI-Import) übernimmt das gewählte Modell die Zuordnung in
Batches; unsichere Fälle werden zur Prüfung markiert.

Über `OPENAI_BASE_URL` lässt sich jedes OpenAI-kompatible Gateway verwenden.

---

## Adressen

| | |
|---|---|
| App | http://localhost:8080 |
| API | http://localhost:8080/api/ |
| API-Doku | http://localhost:8080/api/docs/ |
| Django Admin | http://localhost:8080/admin/ |
| Dateien | http://localhost:8080/s3/ |

Der komplette Stack belegt genau einen Port auf dem Host.

---

## Entwicklung

Details zu Architektur, Konventionen und Fallstricken: **[AGENTS.md](AGENTS.md)**.

```bash
# Backend
cd backend && pip install -r requirements.txt
python manage.py check

# Frontend (nutzt das Backend im Container über einen Proxy)
cd frontend && npm install && npm run dev
npx tsc --noEmit
```
