"""Einrichtung fuer Rechnungsdruck und E-Rechnung auf einer Site.

Setzt die Vorgaben, die sonst nur von Hand in der Datenbank stehen wuerden:
Druckformat, Feldbeschriftungen, Zahlungsart, Zahlungsbedingung,
Kundennummernkreis und E-Rechnungsprofil. Laeuft nach jedem Migrate und ist
idempotent - vorhandene Werte werden nur ueberschrieben, wo es gewollt ist.

Alle Property Setter tragen `module = MODULE`. Das ist keine Kosmetik: Frappe
loescht beim `uninstall-app` genau die Datensaetze, deren Modul zur App gehoert.
Ohne Modul bleibt der Setter stehen und zeigt danach z. B. auf ein geloeschtes
Druckformat.
"""

import frappe

RECHNUNG_PRINT_FORMAT = "Rechnung Kleinunternehmer"
MODULE = "Rechnung DE"

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


def after_install():
	_abgleichen()


def after_migrate():
	_abgleichen()


def _abgleichen():
	_rechnung_druck_abgleichen()
	_belegvorgaben_abgleichen()
	_module_nachtragen()


def _setze_setter(doctype, fieldname, property, value, property_type):
	"""Einen Property Setter mit Modul-Zuordnung schreiben (idempotent).

	Immer die dict-Form von `frappe.make_property_setter`: nur damit laesst sich
	`doctype_or_field="DocType"` setzen (die Positionsargumente erzeugen einen
	DocField-Eintrag ohne Feldnamen, der nie greift). `module` ist dort
	keyword-only und wird aus dem dict ignoriert - deshalb als zweites Argument.
	"""
	frappe.make_property_setter(
		{
			"doctype_or_field": "DocType" if fieldname is None else "DocField",
			"doctype": doctype,
			"fieldname": fieldname,
			"property": property,
			"value": value,
			"property_type": property_type,
		},
		module=MODULE,
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

	Setter aus frueheren Versionen dieser App wurden ohne `module` angelegt und
	ueberleben deshalb ein `uninstall-app`. Sie werden hier auf MODULE gesetzt,
	damit die Deinstallation sie mitnimmt.
	"""
	try:
		for doctype, fieldname, property in SETZER:
			name = _setter_name(doctype, fieldname, property)
			if not frappe.db.exists("Property Setter", name):
				continue
			if frappe.db.get_value("Property Setter", name, "module") != MODULE:
				frappe.db.set_value("Property Setter", name, "module", MODULE)
	except Exception:
		frappe.log_error(
			title="Rechnung DE: Modul-Zuordnung der Property Setter fehlgeschlagen",
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
	try:
		if not frappe.db.exists("Print Format", RECHNUNG_PRINT_FORMAT):
			return

		# DocType-Ebene: nur ueber die dict-Form landet der Eintrag wirklich auf dem
		# DocType (doctype_or_field="DocType").
		_setze_setter("Sales Invoice", None, "default_print_format", RECHNUNG_PRINT_FORMAT, "Data")
		_setze_setter("Sales Invoice", "from_date", "label", "Leistungsbeginn", "Data")
		_setze_setter("Sales Invoice", "to_date", "label", "Leistungsdatum", "Data")
		_setze_setter(
			"Sales Invoice",
			"to_date",
			"description",
			"Tag der Leistungserbringung - erscheint auf der Rechnung und als Leistungsdatum "
			"(BT-72) in der E-Rechnung",
			"Small Text",
		)
	except Exception:
		frappe.log_error(
			title="Rechnung DE: Rechnungs-Druckformat konnte nicht gesetzt werden",
			message=frappe.get_traceback(),
		)


def _belegvorgaben_abgleichen():
	"""Site-Einstellungen setzen, die zu den Belegdrucken und zur E-Rechnung gehoeren.

	Ohne das waeren die Vorgaben nur von Hand in der Datenbank gesetzt und gingen bei
	einer neuen Site oder einem Restore verloren: Zahlungsart im Zahlungsplan,
	Zahlungsbedingung, Kundennummernkreis und E-Rechnungsprofil.
	Alles nur setzen, wenn die Voraussetzungen da sind - sonst still ueberspringen.
	"""
	try:
		from rechnung_de.rechnung import zahlungsart_mit_bankkonto

		# Zahlungsart: erste Zahlungsart, hinter der ein Bankkonto mit IBAN haengt
		firma = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
		if firma:
			zahlungsart = zahlungsart_mit_bankkonto(firma)
			if zahlungsart:
				_setze_default_ohne_ueberschreiben(
					"Payment Schedule", "mode_of_payment", zahlungsart
				)

		# Zahlungsbedingung: nur uebernehmen, wenn genau eine Vorlage existiert
		vorlagen = frappe.get_all("Payment Terms Template", pluck="name")
		if len(vorlagen) == 1:
			_setze_default_ohne_ueberschreiben(
				"Sales Invoice", "payment_terms_template", vorlagen[0], "Link"
			)

		# Kundennummern: fortlaufende Serie statt Kundenname als Schluessel
		if frappe.db.exists("DocType", "Selling Settings"):
			einstellungen = frappe.get_doc("Selling Settings")
			if einstellungen.get("cust_master_name") != "Naming Series":
				einstellungen.cust_master_name = "Naming Series"
				einstellungen.save(ignore_permissions=True)
			_setze_setter(
				"Customer", "naming_series", "options", "KUNDE-.YYYY.-.####\nCUST-.YYYY.-", "Text"
			)
			_setze_setter("Customer", "naming_series", "default", "KUNDE-.YYYY.-.####", "Text")

		# E-Rechnung: ZUGFeRD/Factur-X als Vorgabe, wenn die App installiert ist
		if "eu_einvoice" in frappe.get_installed_apps() and frappe.db.exists(
			"Custom Field", {"dt": "Sales Invoice", "fieldname": "einvoice_profile"}
		):
			frappe.db.set_value(
				"Custom Field",
				{"dt": "Sales Invoice", "fieldname": "einvoice_profile"},
				"default",
				"EN 16931",
			)
			frappe.clear_cache(doctype="Sales Invoice")
	except Exception:
		frappe.log_error(
			title="Rechnung DE: Belegvorgaben konnten nicht gesetzt werden",
			message=frappe.get_traceback(),
		)
