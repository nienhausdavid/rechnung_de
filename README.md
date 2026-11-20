# Rechnung DE - Rechnungsdruck und E-Rechnung

Druckformate und E-Rechnungs-Vorgaben fuer deutsche Ausgangsbelege, unabhaengig von
der Zeiterfassung: Rechnung, Angebot, Auftragsbestätigung, Lieferschein.

## Druckformate

| Druckformat | DocType | Inhalt |
|---|---|---|
| `Rechnung Kleinunternehmer` | Sales Invoice | Pflichtangaben nach § 14 Abs. 4 UStG, Leistungsdatum, § 19-Hinweis, Bankverbindung (sonst „Bankverbindung auf Anfrage“) |
| `Angebot` | Quotation | Positionen, Gültigkeit, § 19-Hinweis, Bankverbindung |
| `Auftragsbestätigung` | Sales Order | Positionen, Liefertermin, § 19-Hinweis, Bankverbindung |
| `Lieferschein` | Delivery Note | Positionen ohne Preise, Unterschriftenfeld |

Ablage: `<modul>/print_format/<name>/<name>.json`, `module` = `Rechnung DE`;
`bench --site <site> migrate` importiert die Dateien. Der Pfad hat zwei
Verzeichnisebenen mit gleichem Namen: Code (`hooks.py`, `install.py`) liegt in
`rechnung_de/rechnung_de/`, die Formate in `rechnung_de/rechnung_de/rechnung_de/print_format/`.

**Beim Aendern eines Formats das Feld `modified` im JSON mitziehen** (Zeitstempel
beim Speichern setzen). `migrate` vergleicht den Zeitstempel mit der Datenbank und
laesst die Datei sonst unveraendert - ohne Fehlermeldung. Steht in der Datenbank ein
spaeterer Zeitstempel, einmalig erzwingen:

```
bench --site <site> console
>>> from frappe.modules.import_file import import_file_by_path
>>> import_file_by_path("/workspace/frappe-bench/apps/rechnung_de/rechnung_de/rechnung_de/"
...                     "print_format/<ordner>/<ordner>.json", force=True)
>>> frappe.db.commit()
```

`bench reload-doc` funktioniert hier nicht zuverlaessig: es erwartet den Modulnamen
`Rechnung DE` und findet Formate mit Umlaut im Namen (`Auftragsbestätigung`) nicht,
weil der Ordner `auftragsbestaetigung` heisst. Das `frappe.db.commit()` ist noetig -
ohne Commit rollt die Konsole die Aenderung beim Beenden zurueck.

Kopf- und Fusszeile stehen im Druckformat (kein Letterhead, damit alles im Repo
liegt). Die Fusszeile haengt in einem `<div id="footer-html">`; Frappe gibt sie als
`--footer-html` an wkhtmltopdf weiter, dadurch steht sie auf jeder Seite unten und
die Seitenzahlen (`Seite <span class="page"></span> von <span class="topage"></span>`)
stimmen. Keine Firmendaten im Template: Firma, Anschrift, USt-IdNr., Bank und Kunde
kommen aus den Datensaetzen, der § 19-Text aus
`E Invoice Settings.vat_exemption_reason_text`.

## Einrichtung auf der Site (`install.py`)

`after_install` und `after_migrate` rufen dieselbe idempotente Abgleichen-Funktion
auf. Sie setzt, jeweils nur wenn die Voraussetzung da ist:

| Einstellung | Bedingung |
|---|---|
| `Sales Invoice.default_print_format` = `Rechnung Kleinunternehmer` | Druckformat ist installiert |
| `Sales Invoice.from_date` / `.to_date`: Labels `Leistungsbeginn` / `Leistungsdatum` (+ Beschreibung an `to_date`) | dito |
| `Sales Invoice.payment_terms_template` = Vorgabe | es existiert **genau eine** Payment Terms Template und die Site hat noch keine Vorgabe |
| `Payment Schedule.mode_of_payment` = Vorgabe | es gibt eine Zahlungsart (Typ Bank) mit aktivem Bankkonto samt IBAN und die Site hat noch keine Vorgabe |
| `Selling Settings.cust_master_name` = `Naming Series`, `Customer.naming_series` (`options` + `default`) | immer |
| `Sales Invoice.einvoice_profile` = `EN 16931` (an einem Custom Field) | `eu_einvoice` installiert, Feld vorhanden und die Site hat noch keine Vorgabe |

Alle Property Setter werden mit `module = "Rechnung DE"` angelegt. Fehler landen mit
Traceback im Error Log (`Rechnung DE: <Vorgabe> konnte nicht gesetzt werden`),
blockieren ein Migrate aber nicht.

Jede Vorgabe wird **einzeln** gesetzt und einzeln abgesichert (`_je_schritt` in
`install.py`): faellt eine aus, laufen die uebrigen weiter. Vorher lag ein `try` um alle
Vorgaben - ein Fehler beim ersten Setter riss Zahlungsbedingung, Kundennummernkreis und
E-Rechnungsprofil mit, und die Site sah danach "normal" aus, obwohl nichts gesetzt war.

Fehlt der `Module Def` der App (z. B. `install-app` auf einer Site ohne Modul-Sync), legt
`_setze_setter()` den Setter nach einem `LinkValidationError` ohne Modul an, statt ihn
ganz zu verwerfen; `_module_nachtragen()` zieht die Zuordnung beim naechsten Migrate nach,
sobald es den `Module Def` gibt.

Vorgaben, die eine Site-Entscheidung sind (Zahlungsart im Zahlungsplan,
Zahlungsbedingung, E-Rechnungsprofil), setzt die App **nur, wenn noch keine da ist** -
sonst wuerde jedes Migrate die Wahl des Nutzers zuruecksetzen.


## Deinstallation

`uninstall-app rechnung_de` loescht die Druckformate und alle Property Setter der App,
weil sie das Modul `Rechnung DE` tragen. `uninstall.py` (`after_uninstall`) raeumt
zusaetzlich auf:

- Property Setter aus frueheren Versionen ohne Modul-Zuordnung (`SETZER` in
  `install.py` ist die gemeinsame Liste fuer Anlegen und Aufraeumen) - sonst zeigt
  `Sales Invoice.default_print_format` nach dem Entfernen auf ein geloeschtes
  Druckformat und `frappe.get_print()` faellt still auf das ERPNext-Standardlayout zurueck.
- `Selling Settings.cust_master_name` wird auf `Customer Name` zurueckgesetzt, wenn es
  noch auf dem von der App gesetzten Wert steht.

## E-Rechnung und Zahlungsart

Die Ausgangsrechnung holt den Zahlungsweg (BG-17) der E-Rechnung aus der
Zahlungsart im Zahlungsplan: Zahlungsart (Typ Bank) → Konto in
`Mode of Payment Account` → `Bank Account` mit IBAN. ERPNext fuellt die
Zahlungsart beim Aufbau des Zahlungsplans nicht aus der Zahlungsbedingung,
deshalb setzt `rechnung_de.rechnung.setze_zahlungsart` (Hook auf `validate`) leere
Zeilen auf die erste Zahlungsart der Firma, hinter der ein aktives Bankkonto
mit IBAN haengt. Vorhandene Zahlungsarten werden nie ueberschrieben; ohne passende
Zahlungsart bleibt die Zeile leer.

Die Vorbelegung aus `install.py` (Zahlungsbedingung, Zahlungsart) ist nur eine
Vorgabe fuer neue Belege und greift nur unter den oben genannten Bedingungen.

## Leistungsdatum (§ 14 Abs. 4 Nr. 6 UStG)

ERPNext hat kein eigenes Feld dafuer. Genutzt werden die Standardfelder
`from_date` / `to_date` der Ausgangsrechnung, die per Property Setter
(`_rechnung_druck_abgleichen()` in `install.py`) auf „Leistungsbeginn“ und
„Leistungsdatum“ umbenannt sind. Dieselben Felder liest die E-Rechnung als
Leistungsdatum (BT-72), es gibt also nur eine Datenquelle fuer PDF und XML.
Fehlt der Wert, setzt `ergaenze_leistungsdatum()` das Rechnungsdatum ein.

## Kundennummern

Neue Kunden bekommen eine fortlaufende Nummer `KUNDE-<Jahr>-<Nummer>`, z. B.
`KUNDE-2026-0001`. Der Anzeigename der Firma bleibt im Feld `customer_name` und
steht auf den Belegen als Empfaenger.

Eingestellt auf der Site (nicht im App-Code, weil es eine Firmenentscheidung ist):

- `Selling Settings.cust_master_name` = `Naming Series`
- Property Setter auf `Customer.naming_series`: `options` = `KUNDE-.YYYY.-.####` (plus
  `CUST-.YYYY.-` als Alternative), `default` = `KUNDE-.YYYY.-.####`

Bestehende Kunden behalten ihren Namen; sie lassen sich bei Bedarf per
`frappe.rename_doc("Customer", alt, neu, force=True)` umbenennen, Verknuepfungen
ziehen dabei automatisch mit.

## Buyer-Reference und Leitweg-ID

XRechnung verlangt das Feld `BuyerReference` (BT-10) **immer** — KoSIT-Regel BR-DE-15,
Schweregrad *fatal*. Bei Rechnungen an Behoerden steht dort die **Leitweg-ID** des
Kunden, im Geschaeftskundenverkehr die Bestell- oder Kundennummer. EN 16931 / ZUGFeRD
verlangt BT-10 nicht.

Damit eine Rechnung nicht ohne Eintrag haengen bleibt, fuellt
`ergaenze_buyer_reference()` (Validate-Hook, nur bei Profil `XRECHNUNG`) die
Kundennummer ein, wenn das Feld leer ist. Vorhandene Werte werden nie ueberschrieben.

## E-Rechnungsprofil: ZUGFeRD / Factur-X

Vorgabe fuer neue Ausgangsrechnungen ist `einvoice_profile = "EN 16931"` (ZUGFeRD 2.x
„Comfort“ / Factur-X EN 16931). Gesetzt als `default` am Custom Field
`Sales Invoice.einvoice_profile`; das Feld ist pro Rechnung umstellbar (`XRECHNUNG`,
`BASIC`, `EXTENDED`).

Der Default ist eine Site-Entscheidung: `install.py` setzt ihn nur, wenn am Custom Field
noch keiner steht. Eine Site, die bewusst `XRECHNUNG` (B2G/Behoerden) vorgibt, behaelt
ihre Wahl ueber jedes Migrate hinweg.

- `EN 16931` und `EXTENDED` erzeugen ein PDF mit eingebettetem CII-XML (`factur-x.xml`).
- `XRECHNUNG` erzeugt nur XML; die App bettet dort bewusst nichts ein.
- Fuer die PDF/A-3-Konvertierung braucht `attach_xml_to_pdf()` **Ghostscript** (`gs`).
  Fehlt es, wird das XML trotzdem eingebettet und die PDF/A-3-Kennung geschrieben, die
  Datei ist aber nicht vollstaendig konvertiert. Im Container: `apt-get install ghostscript`.
- Pruefung: `get_xml_from_pdf()` aus dem Paket `facturx` liest das XML zurueck und
  validiert es gegen die CII-XSD.

## Escaping in den Druckformaten

Alle Nutzdaten laufen durch `|e` (HTML-Escape). Ausnahmen mit Begruendung:

- `row.description`: `Item.description` ist ein Text-Editor-Feld, Frappe speichert
  dort HTML **und** Entities (`<b>`, `&amp;`). Deshalb `html_zu_text()` aus
  `rechnung_de/utils.py` (Jinja-Helfer ueber `jinja.methods` in `hooks.py`): Tags
  werden entfernt, Entities aufgeloest, `<br>`/`</p>` zu Zeilenumbruechen. Danach
  `|e` - sonst steht `&amp;` doppelt escaped im PDF.
- `uom_de.get(row.uom, row.uom or '')|e`: der Fallback auf `row.uom` ist mit escaped;
  die deutschen Kuerzel im Mapping enthalten kein HTML.
- `frappe.utils.format_date` / `fmt_money` liefern keine Freitextdaten.

Beim Aendern der Formate gegenpruefen: kein `{{ row.x }}` oder `{{ doc.x }}` ohne
Filter, und `html_zu_text(...)` immer mit `|e` kombinieren.

## Beim Buchen

- **ZUGFeRD-PDF wird angehängt:** `haenge_zugferd_pdf_an()` (on_submit) erzeugt das PDF
  im Standard-Druckformat, bettet das XML über `eu_einvoice.einvoice.attach_xml_to_pdf`
  ein und legt es als `<Belegname> (ZUGFeRD).pdf` an die Rechnung. Die E-Rechnungs-App
  selbst hängt nur bei Profil `XRECHNUNG` eine XML-Datei an.
- **Validierung blockiert:** `E Invoice Settings` steht auf Speichern **und** Buchen
  `Error Message`. Rechnungen mit XML-Fehlern (z. B. fehlende Kundenanschrift BR-10,
  fehlende Käufer-E-Mail BR-62) lassen sich nicht buchen.

## Site-Einstellungen, die dazugehören

- `Print Settings.pdf_generator` = `wkhtmltopdf`. Der Chrome-Generator braucht ein
  funktionierendes Chromium im Container; ohne das scheitert *jeder* PDF-Download.
  Die Druckformate dieser App setzen `wkhtmltopdf` ohnehin selbst.
- `E Invoice Settings.error_action_on_save/_on_submit` = `Error Message` (siehe oben).
