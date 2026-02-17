# Acceptance Test: Google Docs Review Skill

## Ziel

Validierung aller Operationen, die der `gdocs` Skill in zwei Rollen unterstützen soll:
- **Rolle A: Reviewer** — Dokument prüfen, Kommentare hinterlassen, Änderungsvorschläge einbringen
- **Rolle B: Author/Owner** — Auf Feedback reagieren, Vorschläge annehmen/ablehnen, Dokument verbessern

## Testdokument

- **URL**: `https://docs.google.com/document/d/198oc28CG_VTsFnQM9NQFdC7q1WUcvabFGJ1W0a4r8Ik/edit`
- **Document ID**: `198oc28CG_VTsFnQM9NQFdC7q1WUcvabFGJ1W0a4r8Ik`
- **Voraussetzung**: Dokument muss mindestens enthalten:
  - Mehrere Absätze mit Text
  - Mindestens eine Überschrift (H1/H2)
  - Mindestens eine Liste (bulleted oder numbered)
  - Optional: eine Tabelle

## Toolchain

| Tool | Zweck | Typ |
|------|-------|-----|
| `gwt` | Export/Download (read-only) | API |
| `workspace-mcp` | Edits, Kommentare, Formatierung (read-write) | API |
| `scratch_suggestions.py` | Suggestions lesen (read-only) | API |
| `rodney` + CDP | Suggestions erstellen/akzeptieren/ablehnen, Mode-Switching | Browser |

---

## Rolle A: Reviewer

### A1. Dokument lesen & verstehen

| # | Operation | Tool | Status | Notizen |
|---|-----------|------|--------|---------|
| A1.1 | Dokument als Markdown exportieren | `gwt` | ✅ | `gwt download "$URL" -f md -o /tmp/review/` — Export korrekt, Suggestions nicht enthalten |
| A1.2 | Dokumentstruktur inspizieren (Indizes) | `workspace-mcp` | ✅ | `inspect_doc_structure` — 3 Paragraphen, 14 chars, keine Tabellen |
| A1.3 | Bestehende Kommentare lesen | `workspace-mcp` | ✅ | `read_document_comments` — korrekt (0 Kommentare im Testdoc) |
| A1.4 | Bestehende Suggestions lesen | `scratch_suggestions.py` | ✅ | `--compare` zeigt 3-Wege-Vergleich: Inline, Original, Accepted |

### A2. Feedback geben — Kommentare

| # | Operation | Tool | Status | Notizen |
|---|-----------|------|--------|---------|
| A2.1 | Neuen Kommentar erstellen | `workspace-mcp` | ⬜ | `create_document_comment` — doc-level |
| A2.2 | Auf bestehenden Kommentar antworten | `workspace-mcp` | ⬜ | `reply_to_document_comment` |
| A2.3 | Kommentar mit Textanker erstellen | `workspace-mcp` | ⬜ ❓ | Unklar ob `quoted_text` Parameter existiert |

### A3. Feedback geben — Änderungsvorschläge (Suggestions)

| # | Operation | Tool | Status | Notizen |
|---|-----------|------|--------|---------|
| A3.1 | Text-Einfügung als Suggestion | `rodney` + CDP | ✅ | Suggesting Mode → CDP `char` events. Sauber, keine Verdopplung |
| A3.2 | Text-Löschung als Suggestion | `rodney` + CDP | ✅ | CDP triple-click (Maus) + `rawKeyDown` Backspace (vkCode 8) |
| A3.3 | Text-Ersetzung als Suggestion | `rodney` + CDP | ⬜ | Theoretisch: Select + Delete + Type. Problem: Text-Targeting per Pixel |
| A3.4 | Formatierung als Suggestion | `rodney` + CDP | ⬜ | Unklar — braucht Toolbar-Interaktion im Suggesting Mode |

> **Erkenntnisse A3:**
> - Google Docs API kann Suggestions NICHT erstellen (bestätigt, API-Lücke seit 2023)
> - Browser-Workaround funktioniert: Suggesting Mode aktivieren → CDP Keyboard Events
> - **Kritische Unterscheidung:** Printable chars brauchen `keyDown`+`char`+`keyUp`, Special Keys brauchen `rawKeyDown`+`windowsVirtualKeyCode`+`keyUp`
> - **Text-Selection** funktioniert per CDP triple-click (Maus-Events), NICHT per Keyboard-Navigation (Home/End/Shift+Arrows)
> - **Offenes Problem:** Gezieltes Text-Targeting (bestimmtes Wort/Absatz selektieren) braucht Pixel-Koordinaten oder Ctrl+F

### A4. Direkte Edits (als Alternative zu Suggestions)

| # | Operation | Tool | Status | Notizen |
|---|-----------|------|--------|---------|
| A4.1 | Text ersetzen (Find & Replace) | `workspace-mcp` | ⬜ | `find_and_replace_doc` |
| A4.2 | Text an Position einfügen | `workspace-mcp` | ⬜ | `modify_doc_text` (index-basiert) |
| A4.3 | Formatierung ändern (bold, italic) | `workspace-mcp` | ⬜ | `modify_doc_text` mit Styling |
| A4.4 | Absatzstil ändern (Heading, Liste) | `workspace-mcp` | ⬜ | `update_paragraph_style` |

---

## Rolle B: Author / Document Owner

### B1. Feedback sichten

| # | Operation | Tool | Status | Notizen |
|---|-----------|------|--------|---------|
| B1.1 | Alle Kommentare lesen (inkl. Replies) | `workspace-mcp` | ✅ | `read_document_comments` — strukturiert mit IDs |
| B1.2 | Alle Suggestions lesen | `scratch_suggestions.py` | ✅ | Insertions, Deletions, Style Changes alle erkannt |
| B1.3 | Drei-Wege-Vergleich (Original vs Accepted) | `scratch_suggestions.py` | ✅ | `--compare` Flag zeigt Diff |

### B2. Auf Kommentare reagieren

| # | Operation | Tool | Status | Notizen |
|---|-----------|------|--------|---------|
| B2.1 | Auf Kommentar antworten | `workspace-mcp` | ⬜ | `reply_to_document_comment` |
| B2.2 | Kommentar als erledigt markieren (resolve) | `workspace-mcp` | ⬜ | `resolve_document_comment` |

### B3. Suggestions verarbeiten

| # | Operation | Tool | Status | Notizen |
|---|-----------|------|--------|---------|
| B3.1 | Einzelne Suggestion akzeptieren | `rodney` | ✅ | `rodney click '[aria-label="Accept suggestion"]'` — saved to Drive |
| B3.2 | Einzelne Suggestion ablehnen | `rodney` | ✅ | `rodney click '[aria-label="Reject suggestion"]'` — saved to Drive |
| B3.3 | Alle Suggestions akzeptieren | `rodney` | ⬜ | JS `querySelectorAll` + Mouse-Event-Sequence |
| B3.4 | Alle Suggestions ablehnen | `rodney` | ⬜ | JS `querySelectorAll` + Mouse-Event-Sequence |

> **Erkenntnisse B3:**
> - API-Verifikation nach Browser-Aktion funktioniert sofort (kein Caching)
> - `aria-label` Selektoren sind stabil (semantisch, accessibility-relevant)

### B4. Dokument verbessern

| # | Operation | Tool | Status | Notizen |
|---|-----------|------|--------|---------|
| B4.1 | Text korrigieren (Find & Replace) | `workspace-mcp` | ⬜ | `find_and_replace_doc` |
| B4.2 | Formatierung anpassen | `workspace-mcp` | ⬜ | `modify_doc_text` |
| B4.3 | Absatzstile korrigieren | `workspace-mcp` | ⬜ | `update_paragraph_style` |
| B4.4 | Tabelle einfügen/bearbeiten | `workspace-mcp` | ⬜ | `create_table_with_data` / `batch_update_doc` |

---

## Browser-Automation: Rodney + CDP

### Validierte Operationen

| Operation | Methode | Ergebnis |
|-----------|---------|----------|
| Chromium starten + Rodney verbinden | `--remote-debugging-port=9222` + state.json | ✅ |
| Google Doc öffnen | `rodney open` + 3s wait | ✅ |
| Screenshot | `rodney screenshot` | ✅ |
| Suggestion-Buttons zählen | `rodney js` + `querySelectorAll` | ✅ |
| Mode-Dropdown öffnen | `rodney click '[aria-label="Editing mode"]'` | ✅ |
| Zu Suggesting Mode wechseln | `rodney click '[aria-label="Suggesting Edits become suggestions s"]'` | ✅ |
| Text tippen als Suggestion (INSERT) | CDP `Input.dispatchKeyEvent`: `keyDown`→`char`→`keyUp` | ✅ |
| Text löschen als Suggestion (DELETE) | CDP triple-click + `rawKeyDown` Backspace (vkCode 8) | ✅ |
| Suggestion akzeptieren | `rodney click '[aria-label="Accept suggestion"]'` | ✅ |
| Suggestion ablehnen | `rodney click '[aria-label="Reject suggestion"]'` | ✅ |
| Zurück zu Editing Mode | Mode-Dropdown → Editing | ✅ |

### Gescheiterte Versuche

| Versuch | Warum gescheitert |
|---------|-------------------|
| `rodney input` für Text | Google Docs nutzt kein Standard-Input, `selectAllText` crasht |
| `document.execCommand('insertText')` | Google Docs fängt das nicht ab |
| Keyboard-Navigation (Home/End/Shift+Arrows) per CDP `keyDown` | Events kommen nicht im Editor an |
| Backspace per `keyDown` (ohne vkCode) | Nur `rawKeyDown` + `windowsVirtualKeyCode` funktioniert |
| `Ctrl+A` per CDP (modifier 2) | Nicht von Google Docs verarbeitet |

### CDP Key Event Referenz

| Key-Typ | CDP `type` | `windowsVirtualKeyCode` | Beispiel |
|---------|-----------|------------------------|---------|
| Printable chars | `keyDown`→`char`→`keyUp` | Nicht nötig | `{type:'char', text:'a'}` |
| Backspace | `rawKeyDown`→`keyUp` | 8 | `{type:'rawKeyDown', key:'Backspace', code:'Backspace', windowsVirtualKeyCode:8}` |
| Delete | `rawKeyDown`→`keyUp` | 46 | Ungetestet |
| Enter | `rawKeyDown`→`keyUp` | 13 | Ungetestet |

---

## Offene Fragen & Risiken

### ❓ Offene Fragen

1. ~~**Suggestion-Erstellung per API**~~ → **Beantwortet: NEIN** (API-Lücke bestätigt)
2. ~~**Suggesting Mode per Browser**~~ → **Beantwortet: JA** (CDP Keyboard Events funktionieren)
3. **Kommentare mit Textanker**: Unterstützt `workspace-mcp` das Ankern von Kommentaren an spezifische Textstellen (`quotedFileContent`)?
4. **Text-Targeting im Browser**: Wie selektiert man gezielt ein bestimmtes Wort/Absatz? (Ctrl+F? Find-and-Replace? API-Index → Pixel-Koordinaten?)
5. **Replace als Suggestion**: Funktioniert Select + Delete + Type als atomarer Suggestion-Vorschlag?
6. **Concurrent Editing**: Was passiert, wenn der Skill editiert während jemand anders im Dokument arbeitet?

### ⚡ Risiken

| Risiko | Schwere | Mitigation |
|--------|---------|------------|
| Rodney CSS-Selektoren ändern sich | Hoch | `aria-label` Selektoren bevorzugen (semantisch) |
| Google Bot-Detection bei Rodney | Mittel | Echtes Chromium mit manuellem Login, keine Automation-Flags |
| Pixel-basierte Text-Selection fragil | Hoch | Find-based Selection oder API-Index-Mapping entwickeln |
| Index-Verschiebung bei Batch-Edits | Mittel | Immer `inspect_doc_structure` vor Edits |
| API Rate Limits | Niedrig | Batch-Operationen bevorzugen |

---

## Test-Protokoll

### Vorbereitung

- [x] Testdokument vorhanden (minimal: "123" + leere Zeile)
- [x] `gwt` installiert und authentifiziert
- [x] `workspace-mcp` verfügbar
- [x] `scratch_suggestions.py` funktioniert
- [x] Chromium mit Remote Debugging gestartet
- [x] Rodney verbunden (`rodney status` → OK)
- [ ] Testdokument mit reichhaltigerem Content (Headings, Listen, Tabelle)

### Durchführung — 2026-02-17

**Session 1: API-Tests (A1)**
- ✅ A1.1–A1.4: Alle API-Leseoperationen funktionieren einwandfrei

**Session 2: Rodney Suggestions (B3)**
- ✅ B3.1: Accept first suggestion (Delete "Test") — saved to Drive
- ✅ B3.2: Reject first suggestion (Add "456") — saved to Drive
- ✅ API-Verifikation: `scratch_suggestions.py` bestätigt 0 remaining

**Session 3: Suggesting Mode (A3)**
- ✅ Mode-Switching: Editing → Suggesting → Editing
- ✅ A3.1: INSERT "HELLO_SUGGESTION" als Suggestion erstellt
  - Fix: `keyDown` ohne `text` param, nur `char` event mit `text` (sonst Verdopplung)
- ✅ A3.2: DELETE "123" als Suggestion erstellt
  - Fix: `rawKeyDown` + `windowsVirtualKeyCode: 8` (normales `keyDown` ignoriert)
  - Fix: Triple-click per CDP Mouse Events für Text-Selection (Keyboard-Nav funktioniert nicht)
