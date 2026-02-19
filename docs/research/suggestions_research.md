# Google Docs Suggestions: API-Recherche & Browser-Automation

## Ziel

Untersuchen, ob Änderungsvorschläge (Suggestions / Suggested Edits) in Google Docs programmatisch gelesen, akzeptiert oder abgelehnt werden können — und einen funktionierenden Prototyp bauen.

Testdokument: `https://docs.google.com/document/d/198oc28CG_VTsFnQM9NQFdC7q1WUcvabFGJ1W0a4r8Ik/edit`

---

## 1. API-Recherche: Was ist möglich?

### 1.1 Suggestions lesen — Google Docs API v1

Die Docs API unterstützt das **Auslesen** von Vorschlägen über den Parameter `suggestionsViewMode` auf `documents.get`:

| Modus | Effekt |
|-------|--------|
| `SUGGESTIONS_INLINE` | Alle Vorschläge inline sichtbar mit IDs |
| `PREVIEW_SUGGESTIONS_ACCEPTED` | Dokument als wären alle Vorschläge angenommen |
| `PREVIEW_WITHOUT_SUGGESTIONS` | Dokument als wären alle Vorschläge abgelehnt |
| `DEFAULT_FOR_CURRENT_ACCESS` | Default-Verhalten |

Im JSON-Body erscheinen auf `TextRun`-Elementen:
- `suggestedInsertionIds` — IDs für vorgeschlagene Einfügungen
- `suggestedDeletionIds` — IDs für vorgeschlagene Löschungen
- `suggestedTextStyleChanges` — Vorgeschlagene Formatierungsänderungen

Auf Paragraph-Ebene zusätzlich:
- `suggestedParagraphStyleChanges`
- `suggestedBulletChanges`

**Hinweis:** Die offizielle Google-Doku nennt den Modus `PREVIEW_WITH_SUGGESTIONS_ACCEPTED`, aber die tatsächliche API akzeptiert nur `PREVIEW_SUGGESTIONS_ACCEPTED` (ohne `WITH_`). Der Discovery-Service der Bibliothek validiert die echten Enum-Werte zur Laufzeit.

### 1.2 Revisionshistorie — Google Drive API v3

Die Drive API bietet `revisions.list` und `revisions.get` für die Versionshistorie:

```python
drive_service.revisions().list(
    fileId=FILE_ID,
    fields="revisions(id,modifiedTime,lastModifyingUser)"
).execute()
```

**Einschränkung:** Bei häufig bearbeiteten Docs ist die Liste oft unvollständig — Google mergt zeitlich nahe Revisionen intern zusammen.

### 1.3 Suggestions akzeptieren/ablehnen — NICHT MÖGLICH

Die `documents.batchUpdate`-Methode hat 37+ Request-Typen — **keiner davon betrifft Suggestions**.

| Quelle | Ergebnis |
|--------|----------|
| Docs API v1 `batchUpdate` | 37 Request-Typen, keiner für Suggestions |
| Google Apps Script `DocumentApp` | Kein `getSuggestions()` oder `accept()` |
| API Discovery Document | Nur Read-Only-Schemas |
| API Release Notes (2019-2026) | 4 Einträge total, kein Suggestion-Feature |
| [Issue #287903901](https://issuetracker.google.com/issues/287903901) | Offen seit Juni 2023, keine Antwort |

---

## 2. Bestehende Tools: Keines unterstützt Suggestions

Drei Google-Workspace-Tools wurden untersucht — keines nutzt `suggestionsViewMode`:

### 2.1 google-workspace-tools (gwt) — dieses Projekt

- Python CLI/Library für Drive, Gmail, Calendar Export
- Nutzt `documents().get(documentId=...)` ohne `suggestionsViewMode`
- Referenziert `revisionId` nur als Metadaten

### 2.2 gogcli (Go CLI)

- Go CLI von [github.com/simonw/gogcli](https://github.com/simonw/gogcli) (nicht verifiziert)
- `Documents.Get(id).Fields("documentId,title,revisionId")` — kein Suggestion-Support
- Nur `info` (Metadata) und `cat` (Plaintext-Extraktion)

### 2.3 google_workspace_mcp (Python MCP Server)

- [taylorwilsdon/workspace-mcp](https://github.com/taylorwilsdon/google_workspace_mcp) — umfangreicher MCP Server
- Hat `batchUpdate` und Editing-Tools (Tabellen, Formatierung, Find/Replace)
- Aber: `documents().get(documentId=...)` ohne `suggestionsViewMode`
- Hat eine Analyse-Datei `EXTEND_DOCUMENT_EDITING_CAPABILITIES.md` die genau diese API-Lücke dokumentiert

**Fazit:** Eine echte Lücke im gesamten Ökosystem — kein Tool nutzt die vorhandene Read-API für Suggestions.

---

## 3. Prototyp: Suggestions auslesen (API)

`scratch_suggestions.py` nutzt die bestehende gwt-Authentifizierung und liest Suggestions über die Docs API:

```bash
uv run python scratch_suggestions.py <document_url_or_id> [--raw] [--compare]
```

### Ergebnis für das Testdokument

```
Found 2 suggestion(s) across 2 suggestion ID(s):

Suggestion: suggest.olfvq78rq4r1
────────────────────────────────────────────────────────────
  [- DELETE] 'Test'

Suggestion: suggest.lmrviv1tgypm
────────────────────────────────────────────────────────────
  [+ INSERT] '456'
```

### Drei-Wege-Vergleich (--compare)

| Modus | Zeichenlänge |
|-------|-------------|
| SUGGESTIONS_INLINE | 13 chars |
| PREVIEW_WITHOUT_SUGGESTIONS (Original) | 10 chars |
| PREVIEW_SUGGESTIONS_ACCEPTED | 9 chars |

Diff Original vs Accepted:
```
Line 1:  - 'Test'  →  + ''
Line 3:  - ''      →  + '456'
```

### Funktionsumfang

- Alle Suggestion-Typen: Insertions, Deletions, Style Changes, Paragraph Style, Bullet Changes
- Gruppierung nach Suggestion-ID
- Drei-Wege-Vergleich (inline, original, accepted)
- Optional: Raw JSON Dump (`--raw`)

---

## 4. Workaround-Recherche: Suggestions akzeptieren

Da die API Accept/Reject nicht unterstützt, wurden alle bekannten Workarounds evaluiert:

| Ansatz | Funktioniert? | Nachteile |
|--------|--------------|-----------|
| **Browser-DOM-Manipulation** | Ja (fragil) | CSS-Selektoren können sich ändern |
| **Headless Browser Automation** | Ja (fragil) | Google Bot-Detection, Session-Management |
| **Content-Rewrite via API** | Simuliert | Destruktiv, verliert Formatierung & History |
| **DOCX-Roundtrip** | Simuliert | Verliert Sharing, neues Dokument |
| **Google Apps Script** | Nein | Keine Suggestion-Methoden |
| **Undokumentierte APIs** | Unbekannt | Proprietäre Protobufs, nicht öffentlich |

Bekannte CSS-Selektoren für Suggestion-Buttons (Stand Feb 2026):
- `[role="button"][aria-label="Accept suggestion"]`
- `[role="button"][aria-label="Reject suggestion"]`
- `.docos-accept-suggestion`

---

## 5. Browser-Automation mit Chromium + Rodney

### 5.1 Rodney

[simonw/rodney](https://github.com/simonw/rodney) ist ein Go-CLI-Tool, das eine persistente Chrome-Instanz über das Chrome DevTools Protocol (CDP) steuert. Quasi ein scriptbares Puppeteer als Shell-Kommandos.

### 5.2 Probleme und Fixes auf Apple Silicon

**Problem 1: Chrome crasht mit EOF** ([Issue #9](https://github.com/simonw/rodney/issues/9))

Root Cause: `--single-process` Flag ist inkompatibel mit macOS arm64. Chrome startet, schreibt die Debug-URL, stirbt dann sofort.

Fix: `--single-process` entfernt, hinter `ROD_SINGLE_PROCESS=1` Opt-in gestellt.

**Problem 2: Google blockiert Login ("insecure browser")**

Root Cause: `go-rod` setzt `--enable-automation` und `navigator.webdriver=true`. Google erkennt das und blockiert den Login.

Fix: `--enable-automation` und `--use-mock-keychain` im headed-Modus entfernt. Reichte aber nicht — Google prüft weitere CDP-Signale.

**Problem 3: Kein sichtbares Browser-Fenster**

Root Cause: `Headless(true)` war hardcoded.

Fix: `ROD_HEADLESS=false` Environment-Variable eingeführt.

### 5.3 Funktionierende Lösung: Chromium mit Remote Debugging

Statt go-rod ein neues Chrome starten zu lassen, wird ein bestehendes Chromium mit Remote Debugging Port genutzt:

```bash
# 1. Chromium mit Debugging starten
"/Applications/Chromium.app/Contents/MacOS/Chromium" --remote-debugging-port=9222

# 2. Manuell bei Google einloggen (einmalig)

# 3. Rodney State auf Chromium zeigen lassen
DEBUG_URL=$(curl -s http://127.0.0.1:9222/json/version | python3 -c "import sys,json; print(json.load(sys.stdin)['webSocketDebuggerUrl'])")
mkdir -p ~/.rodney
echo "{\"debug_url\":\"$DEBUG_URL\",\"pid\":0}" > ~/.rodney/state.json

# 4. Rodney nutzen
rodney status
rodney open "https://docs.google.com/document/d/DOCUMENT_ID/edit"
rodney screenshot /tmp/doc.png
```

**Warum das funktioniert:** Chromium läuft als normaler Browser (keine Automation-Flags), der User ist regulär eingeloggt. Rodney verbindet sich nur per WebSocket/CDP — für Google sieht es aus wie ein normaler Browser.

### 5.4 Ergebnis

Rodney erkennt im DOM des Testdokuments:

| Element | Anzahl |
|---------|--------|
| Accept suggestion Buttons | 2 |
| Reject suggestion Buttons | 2 |
| docos-Elemente (Collaboration UI) | 88 |
| suggestion-Elemente | 12 |

Die Suggestions können per Klick akzeptiert werden:

```bash
# Alle Suggestions akzeptieren
rodney js "document.querySelectorAll('[role=\"button\"][aria-label=\"Accept suggestion\"]').forEach(el => { ['mouseover','mousedown','click','mouseup'].forEach(e => el.dispatchEvent(new MouseEvent(e, {bubbles:true}))) })"

# Einzelne Suggestion akzeptieren (erste)
rodney click '[aria-label="Accept suggestion"]'
```

---

## 6. Zusammenfassung

| Fähigkeit | Methode | Status |
|-----------|---------|--------|
| Suggestions **lesen** | Google Docs API v1 (`suggestionsViewMode`) | Funktioniert (`scratch_suggestions.py`) |
| Suggestions **vergleichen** | API: 3 View Modes | Funktioniert (`--compare`) |
| Revisionshistorie | Google Drive API v3 (`revisions.list`) | Verfügbar, nicht prototypisiert |
| Suggestions **akzeptieren** | API | Nicht möglich (API-Lücke) |
| Suggestions **akzeptieren** | Chromium + Rodney (DOM-Klick) | Funktioniert |
| Suggestions **ablehnen** | Chromium + Rodney (DOM-Klick) | Verfügbar, nicht getestet |

### Patches an Rodney

Änderungen in `rodney/main.go`:

1. `--single-process` entfernt, hinter `ROD_SINGLE_PROCESS=1` gestellt
2. `ROD_HEADLESS=false` für sichtbaren Browser eingeführt
3. `--enable-automation` und `--use-mock-keychain` im headed-Modus entfernt

---

## Referenzen

- [Google Docs API: Work with suggestions](https://developers.google.com/workspace/docs/api/how-tos/suggestions)
- [Google Docs API: batchUpdate request types](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/request)
- [Google Drive API: revisions](https://developers.google.com/drive/api/guides/manage-revisions)
- [Feature Request: Issue #287903901](https://issuetracker.google.com/issues/287903901)
- [Rodney: Issue #9 (Apple Silicon crash)](https://github.com/simonw/rodney/issues/9)
- [DOM Accept Workaround (benzittlau)](https://gist.github.com/benzittlau/a05e7669a5a53d8f2333)
- [interface0 Browser Automation](https://andybromberg.com/interface0-google-docs)
