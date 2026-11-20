# Rechnung DE - Rechnungsdruck und E-Rechnung

Druckformate und E-Rechnungs-Vorgaben fuer deutsche Ausgangsbelege, unabhaengig von
der Zeiterfassung: Rechnung, Angebot, Auftragsbestätigung, Lieferschein.

## Druckformate

| Druckformat | DocType | Inhalt |
|---|---|---|
| `Rechnung Kleinunternehmer` | Sales Invoice | Pflichtangaben nach § 14 Abs. 4 UStG, Leistungsdatum, § 19-Hinweis, Bankverbindung |
| `Angebot` | Quotation | Positionen, Gültigkeit, § 19-Hinweis, Bankverbindung |
| `Auftragsbestätigung` | Sales Order | Positionen, Liefertermin, § 19-Hinweis, Bankverbindung |
| `Lieferschein` | Delivery Note | Positionen ohne Preise, Unterschriftenfeld |

Ablage: `<modul>/print_format/<name>/<name>.json`; `bench migrate` importiert Änderungen.
Kopf- und Fußzeile stehen im Druckformat (kein Letterhead, damit alles im Repo liegt).
Die Fußzeile hängt in einem `<div id="footer-html">`; Frappe gibt sie als `--footer-html`
an wkhtmltopdf weiter, dadurch steht sie auf jeder Seite unten und die Seitenzahlen
(`Seite <span class="page"></span> von <span class="topage"></span>`) stimmen.
Keine Firmendaten im Template: Firma, Anschrift, USt-IdNr., Bank und Kunde kommen aus
den Datensätzen, der § 19-Text aus `E Invoice Settings.vat_exemption_reason_text`.

## E-Rechnung und Zahlungsart

Die Ausgangsrechnung holt den Zahlungsweg (BG-17) der E-Rechnung aus der
Zahlungsart im Zahlungsplan: Zahlungsart (Typ Bank) → Konto in
`Mode of Payment Account` → `Bank Account` mit IBAN. ERPNext füllt die
Zahlungsart beim Aufbau des Zahlungsplans nicht aus der Zahlungsbedingung,
deshalb setzt `sales_invoice.setze_zahlungsart` (Hook auf `validate`) leere
Zeilen auf die erste Zahlungsart der Firma, hinter der ein aktives Bankkonto
mit IBAN hängt. Vorhandene Zahlungsarten werden nie überschrieben.

Damit eine neue Rechnung überhaupt einen Zahlungsplan hat, ist per Property
Setter `Sales Invoice.payment_terms_template` auf die Zahlungsbedingung und
`Payment Schedule.mode_of_payment` auf die Zahlungsart vorbelegt.

## Erweiterungsideen

- „Neuer Auftrag" direkt aus der Fahrt (wie beim Kundeneinsatz).
- Kilometer per Route/Adresse berechnen statt über das Tacho-Foto.
- Standort bei Beginn und Ende gibt es für die Fahrt (optional, siehe `fahrtenbuch.md`); offen: dasselbe für den Kundeneinsatz und eine laufende Aufzeichnung (im Browser nur im Vordergrund zuverlässig, sonst eine Tracker-App).
- Externes Signaturpad statt Finger/Stift.
- Custom Fields oder Property Setter, die später über die Oberfläche
  entstehen, gehören nicht automatisch zur App – in `install.py`
  nachtragen, dann entfernt die Deinstallation sie mit.


## Rechnungs- und Belegdruck (§ 14 UStG)

Die App bringt vier eigene Druckformate mit (Jinja, `pdf_generator: wkhtmltopdf`,
Modul "Zeit Projekt", also mit der App installiert und deinstalliert):

| Druckformat | DocType | Inhalt |
|---|---|---|
| `Rechnung Kleinunternehmer` | Sales Invoice | Pflichtangaben nach § 14 Abs. 4 UStG, Leistungsdatum, § 19-Hinweis, Bankverbindung |
| `Angebot` | Quotation | Positionen, Gültigkeit, § 19-Hinweis, Bankverbindung |
| `Auftragsbestätigung` | Sales Order | Positionen, Liefertermin, § 19-Hinweis, Bankverbindung |
| `Lieferschein` | Delivery Note | Positionen ohne Preise, Unterschriftenfeld |

Ablage: `<modul>/print_format/<name>/<name>.json`; `bench migrate` importiert Änderungen.

**Leistungsdatum.** ERPNext hat kein eigenes Feld dafür. Genutzt werden die
Standardfelder `from_date` / `to_date` der Ausgangsrechnung, die per Property Setter
(`_rechnung_druck_abgleichen()` in `install.py`) auf "Leistungsbeginn" und
"Leistungsdatum" umbenannt sind. Dieselben Felder liest die E-Rechnung als
Leistungsdatum (BT-72), es gibt also nur eine Datenquelle für PDF und XML.
Fehlt der Wert, setzt `ergaenze_leistungsdatum()` das Rechnungsdatum ein.

**Rechnungsdruck als Vorgabe.** `_rechnung_druck_abgleichen()` setzt
`default_print_format` auf der DocType-Ebene (Property Setter mit
`doctype_or_field="DocType"`; die Positionsargumente von `make_property_setter`
erzeugen sonst einen DocField-Eintrag ohne Feldnamen, der nicht greift).

**Kein Letterhead.** Kopf- und Fußzeile stehen im Druckformat, nicht in einem
Letterhead-Datensatz: Letterheads liegen nur in der Datenbank, das Druckformat ist
HTML im Repo und damit versioniert.


## Kundennummern

Neue Kunden bekommen eine fortlaufende Nummer `KUNDE-<Jahr>-<Nummer>`, z. B.
`KUNDE-2026-0001`. Der Anzeigename der Firma bleibt im Feld `customer_name` und
steht auf den Belegen als Empfänger.

Eingestellt auf der Site (nicht im App-Code, weil es eine Firmenentscheidung ist):

- `Selling Settings.cust_master_name` = `Naming Series`
- Property Setter auf `Customer.naming_series`: `options` = `KUNDE-.YYYY.-.####` (plus
  `CUST-.YYYY.-` als Alternative), `default` = `KUNDE-.YYYY.-.####`

Bestehende Kunden behalten ihren Namen; sie lassen sich bei Bedarf per
`frappe.rename_doc("Customer", alt, neu, force=True)` umbenennen, Verknüpfungen
ziehen dabei automatisch mit.


## Buyer-Reference und Leitweg-ID

XRechnung verlangt das Feld `BuyerReference` (BT-10) **immer** — KoSIT-Regel BR-DE-15,
Schweregrad *fatal*. Bei Rechnungen an Behörden steht dort die **Leitweg-ID** des
Kunden, im Geschäftskundenverkehr die Bestell- oder Kundennummer. EN 16931 / ZUGFeRD
verlangt BT-10 nicht.

Damit eine Rechnung nicht ohne Eintrag hängen bleibt, füllt
`ergaenze_buyer_reference()` (Validate-Hook, nur bei Profil `XRECHNUNG`) die
Kundennummer ein, wenn das Feld leer ist. Vorhandene Werte werden nie überschrieben.


## E-Rechnungsprofil: ZUGFeRD / Factur-X

Vorgabe für neue Ausgangsrechnungen ist `einvoice_profile = "EN 16931"` (ZUGFeRD 2.x
„Comfort" / Factur-X EN 16931). Gesetzt als `default` am Custom Field
`Sales Invoice.einvoice_profile`; das Feld ist pro Rechnung umstellbar (`XRECHNUNG`,
`BASIC`, `EXTENDED`).

- `EN 16931` und `EXTENDED` erzeugen ein PDF mit eingebettetem CII-XML (`factur-x.xml`).
- `XRECHNUNG` erzeugt nur XML; die App bettet dort bewusst nichts ein.
- Für die PDF/A-3-Konvertierung braucht `attach_xml_to_pdf()` **Ghostscript** (`gs`).
  Fehlt es, wird das XML trotzdem eingebettet und die PDF/A-3-Kennung geschrieben, die
  Datei ist aber nicht vollständig konvertiert. Im Container: `apt-get install ghostscript`.
- Prüfung: `get_xml_from_pdf()` aus dem Paket `facturx` liest das XML zurück und
  validiert es gegen die CII-XSD.
