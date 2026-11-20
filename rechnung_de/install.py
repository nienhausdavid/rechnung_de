"""Einrichtung fuer Rechnungsdruck und E-Rechnung auf einer Site.

Setzt die Vorgaben, die sonst nur von Hand in der Datenbank stehen wuerden:
Druckformat, Feldbeschriftungen, Zahlungsart, Zahlungsbedingung,
Kundennummernkreis und E-Rechnungsprofil. Laeuft nach jedem Migrate und ist
idempotent - vorhandene Werte werden nur ueberschrieben, wo es gewollt ist.

Jede Vorgabe wird **einzeln** gesetzt und einzeln abgesichert (`_je_schritt`):
faellt eine aus, laufen die uebrigen weiter und die Site verliert nicht
stillschweigend alles hinter dem ersten Fehler.

Alle Property Setter tragen `module = MODULE`. Das ist keine Kosmetik: Frappe
loescht beim `uninstall-app` genau die Datensaetze, deren Modul zur App gehoert.
Ohne Modul bleibt der Setter stehen und zeigt danach z. B. auf ein geloeschtes
Druckformat.
"""

import frappe

RECHNUNG_PRINT_FORMAT = "Rechnung Kleinunternehmer"
MODULE = "Rechnung DE"
EINVOICE_PROFIL = "EN 16931"

#: Alle Property Setter, die diese App auf der Site anlegt:
#: (DocType, Feldname oder None fuer die DocType-Ebene, Property).
#: Einzige Quelle fuer das Anlegen (install) und das Aufraeumen (uninstall).
SETZER = (
	("Sales Invoice", None, "default_print_format"),
	("Sales Invoice", "from_date", "label"),
	("Sales Invoice", "to_date", "label"),
	("Sales Invoice", "to_date", "description"),
	("Sales Invoice", "payment_terms_template", "default"),
	("Payment Schedule", "mode_of_payment", "default"),
	("Customer", "naming_series", "options"),
	("Customer", "naming_series", "default"),
)

#: Setter, die auf jeder Site mit ERPNext und importierten Druckformaten entstehen
#: muessen. Die beiden uebrigen (`payment_terms_template`, `mode_of_payment`) sind
#: eine Entscheidung der Site und fehlen legitim, wenn die Voraussetzung fehlt.
PFLICHT_SETZER = (
	("Sales Invoice", None, "default_print_format"),
	("Sales Invoice", "from_date", "label"),
	("Sales Invoice", "to_date", "label"),
	("Sales Invoice", "to_date", "description"),
	("Customer", "naming_series", "options"),
	("Customer", "naming_series", "default"),
)


def after_install():
	_abgleichen()


def after_migrate():
	_abgleichen()


def _abgleichen():
	_rechnung_druck_abgleichen()
	_belegvorgaben_abgleichen()
	_module_nachtragen()


def _je_schritt(*schritte):
	"""Einzelschritte ausfuehren: ein Fehler beendet die folgenden nicht.

	Der Traceback landet mit sprechendem Titel im Error Log, ein Migrate laeuft
	weiter. Wichtig: ohne diese Trennung reisst ein fehlgeschlagener Setter alle
	folgenden Vorgaben mit und die Site sieht danach "normal" aus, obwohl nichts
	gesetzt wurde.
	"""
	for titel, schritt in schritte:
		try:
			schritt()
		except Exception:
			frappe.log_error(
				title=f"Rechnung DE: {titel} konnte nicht gesetzt werden",
				message=frappe.get_traceback(),
			)


def _setze_setter(doctype, fieldname, property, value, property_type):
	"""Einen Property Setter mit Modul-Zuordnung schreiben (idempotent).

	Immer die dict-Form von `frappe.make_property_setter`: nur damit laesst sich
	`doctype_or_field="DocType"` setzen (die Positionsargumente erzeugen einen
	DocField-Eintrag ohne Feldnamen, der nie greift). `module` ist dort
	keyword-only und wird aus dem dict ignoriert - deshalb als zweites Argument.

	Fehlt der `Module Def` der App (z. B. weil `install-app` auf einer Site ohne
	Modul-Sync lief), scheitert das Anlegen mit `LinkValidationError` ("Could not
	find Module (for export)"). Dann einmal ohne Modul anlegen, statt den Setter
	ganz zu verlieren: `_module_nachtragen()` zieht die Zuordnung nach, sobald der
	Datensatz existiert, und `uninstall.py` raeumt ueber den Namen ab - der Setter
	bleibt also in jedem Fall entfernbar.
	"""
	try:
		_setze_setter_mit_modul(doctype, fieldname, property, value, property_type, MODULE)
	except frappe.LinkValidationError:
		_setze_setter_mit_modul(doctype, fieldname, property, value, property_type, None)


def _setze_setter_mit_modul(doctype, fieldname, property, value, property_type, module):
	frappe.make_property_setter(
		{
			"doctype_or_field": "DocType" if fieldname is None else "DocField",
			"doctype": doctype,
			"fieldname": fieldname,
			"property": property,
			"value": value,
			"property_type": property_type,
		},
		module=module,
	)


def _setze_default_ohne_ueberschreiben(doctype, fieldname, value, property_type="Data"):
	"""Vorgabe nur setzen, wenn die Site noch keine hat.

	Zahlungsart und Zahlungsbedingung sind eine Entscheidung der Site - steht schon
	ein Wert da (auch von Hand gesetzt), bleibt er. Die Modul-Zuordnung zieht
	`_module_nachtragen()` nach.
	"""
	if frappe.db.exists("Property Setter", _setter_name(doctype, fieldname, "default")):
		return
	_setze_setter(doctype, fieldname, "default", value, property_type)


def _module_nachtragen():
	"""Altlasten ohne Modul-Zuordnung der App zuschlagen.

	Setter aus frueheren Versionen dieser App - und solche, die `_setze_setter()`
	ohne `Module Def` anlegen musste - tragen kein Modul und ueberleben deshalb ein
	`uninstall-app`. Sie werden hier auf MODULE gesetzt, damit die Deinstallation
	sie mitnimmt. Ohne `Module Def` waere das nur ein neuer Link-Fehler, deshalb
	passiert dann nichts.
	"""
	if not frappe.db.exists("Module Def", MODULE):
		return

	for doctype, fieldname, property in SETZER:
		name = _setter_name(doctype, fieldname, property)
		if not frappe.db.exists("Property Setter", name):
			continue
		if frappe.db.get_value("Property Setter", name, "module") == MODULE:
			continue
		try:
			frappe.db.set_value("Property Setter", name, "module", MODULE)
		except Exception:
			frappe.log_error(
				title=f"Rechnung DE: Modul-Zuordnung fuer {name} konnte nicht gesetzt werden",
				message=frappe.get_traceback(),
			)


def _setter_name(doctype, fieldname, property):
	"""Docname eines Property Setters - PropertySetter.autoname nachgebaut."""
	return f"{doctype}-{fieldname or 'main'}-{property}"


def _rechnung_druck_abgleichen():
	"""Setzt das mitgelieferte Rechnungs-Druckformat als Vorgabe fuer Ausgangsrechnungen
	und beschriftet die beiden Datumsfelder, die den Leistungszeitpunkt tragen.

	§ 14 Abs. 4 Nr. 6 UStG verlangt den Zeitpunkt der Leistung auf der Rechnung.
	ERPNext kennt dafuer kein eigenes Feld; die Standardfelder from_date/to_date sind
	genau dieser Zeitraum und werden von der E-Rechnung als Leistungsdatum (BT-72)
	gelesen. Deshalb nur umbenennen, kein zweites Feld daneben.

	Fehler werden mit Traceback ins Error Log geschrieben, aber nicht geworfen: ein
	Migrate soll nicht an einer fehlenden Voraussetzung haengen bleiben.
	"""
	if not frappe.db.exists("Print Format", RECHNUNG_PRINT_FORMAT):
		return

	_je_schritt(
		("Standard-Druckformat fuer Ausgangsrechnungen", _druckformat_vorgeben),
		("Beschriftung von from_date", _leistungsbeginn_beschriften),
		("Beschriftung von to_date", _leistungsdatum_beschriften),
		("Beschreibung von to_date", _leistungsdatum_beschreiben),
	)


def _druckformat_vorgeben():
	# DocType-Ebene: nur ueber die dict-Form landet der Eintrag wirklich auf dem
	# DocType (doctype_or_field="DocType").
	_setze_setter("Sales Invoice", None, "default_print_format", RECHNUNG_PRINT_FORMAT, "Data")


def _leistungsbeginn_beschriften():
	_setze_setter("Sales Invoice", "from_date", "label", "Leistungsbeginn", "Data")


def _leistungsdatum_beschriften():
	_setze_setter("Sales Invoice", "to_date", "label", "Leistungsdatum", "Data")


def _leistungsdatum_beschreiben():
	_setze_setter(
		"Sales Invoice",
		"to_date",
		"description",
		"Tag der Leistungserbringung - erscheint auf der Rechnung und als Leistungsdatum "
		"(BT-72) in der E-Rechnung",
		"Small Text",
	)


def _belegvorgaben_abgleichen():
	"""Site-Einstellungen setzen, die zu den Belegdrucken und zur E-Rechnung gehoeren.

	Ohne das waeren die Vorgaben nur von Hand in der Datenbank gesetzt und gingen bei
	einer neuen Site oder einem Restore verloren: Zahlungsart im Zahlungsplan,
	Zahlungsbedingung, Kundennummernkreis und E-Rechnungsprofil.
	Alles nur setzen, wenn die Voraussetzungen da sind - sonst still ueberspringen.
	"""
	_je_schritt(
		("Zahlungsart im Zahlungsplan", _zahlungsart_vorgeben),
		("Zahlungsbedingung", _zahlungsbedingung_vorgeben),
		("Kundennummernkreis", _kundennummernkreis_setzen),
		("E-Rechnungsprofil", _einvoice_profil_vorgeben),
	)


def _zahlungsart_vorgeben():
	"""Erste Zahlungsart, hinter der ein Bankkonto mit IBAN haengt."""
	from rechnung_de.rechnung import zahlungsart_mit_bankkonto

	firma = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not firma:
		return
	zahlungsart = zahlungsart_mit_bankkonto(firma)
	if zahlungsart:
		_setze_default_ohne_ueberschreiben("Payment Schedule", "mode_of_payment", zahlungsart)


def _zahlungsbedingung_vorgeben():
	"""Zahlungsbedingung nur uebernehmen, wenn genau eine Vorlage existiert."""
	vorlagen = frappe.get_all("Payment Terms Template", pluck="name")
	if len(vorlagen) == 1:
		_setze_default_ohne_ueberschreiben(
			"Sales Invoice", "payment_terms_template", vorlagen[0], "Link"
		)


def _kundennummernkreis_setzen():
	"""Fortlaufende Kundennummer statt Kundenname als Schluessel."""
	if not frappe.db.exists("DocType", "Selling Settings"):
		return
	einstellungen = frappe.get_doc("Selling Settings")
	if einstellungen.get("cust_master_name") != "Naming Series":
		einstellungen.cust_master_name = "Naming Series"
		einstellungen.save(ignore_permissions=True)
	_setze_setter("Customer", "naming_series", "options", "KUNDE-.YYYY.-.####\nCUST-.YYYY.-", "Text")
	_setze_setter("Customer", "naming_series", "default", "KUNDE-.YYYY.-.####", "Text")


def _einvoice_profil_vorgeben():
	"""E-Rechnungsprofil als Vorgabe - nur wenn die Site noch keine hat.

	`EN 16931` (ZUGFeRD/Factur-X "Comfort") ist die Vorgabe fuer B2B. Eine Site, die
	bewusst etwas anderes eingestellt hat (z. B. `XRECHNUNG` fuer B2G), behaelt ihre
	Wahl: das Feld ist eine Site-Entscheidung wie Zahlungsart und Zahlungsbedingung,
	kein Wert, den jedes Migrate zuruecksetzen darf.
	"""
	if "eu_einvoice" not in frappe.get_installed_apps():
		return

	feld = frappe.db.get_value(
		"Custom Field", {"dt": "Sales Invoice", "fieldname": "einvoice_profile"}, "name"
	)
	if not feld or frappe.db.get_value("Custom Field", feld, "default"):
		return

	frappe.db.set_value("Custom Field", feld, "default", EINVOICE_PROFIL)
	frappe.clear_cache(doctype="Sales Invoice")
