"""Einrichtung fuer Rechnungsdruck und E-Rechnung auf einer Site.

Setzt die Vorgaben, die sonst nur von Hand in der Datenbank stehen wuerden:
Standard-Druckformat, Feldbeschriftungen, Zahlungsart, Zahlungsbedingung,
Kundennummernkreis und E-Rechnungsprofil. Laeuft nach jedem Migrate und ist
idempotent - vorhandene Werte werden nur ueberschrieben, wo es gewollt ist.
"""

import frappe

RECHNUNG_PRINT_FORMAT = "Rechnung Kleinunternehmer"
MODULE = "Rechnung DE"


def after_install():
	_rechnung_druck_abgleichen()
	_belegvorgaben_abgleichen()


def after_migrate():
	_rechnung_druck_abgleichen()
	_belegvorgaben_abgleichen()


def _rechnung_druck_abgleichen():
	"""Setzt das mitgelieferte Rechnungs-Druckformat als Vorgabe fuer Ausgangsrechnungen
	und beschriftet die beiden Datumsfelder, die den Leistungszeitpunkt tragen.

	§ 14 Abs. 4 Nr. 6 UStG verlangt den Zeitpunkt der Leistung auf der Rechnung.
	ERPNext kennt dafuer kein eigenes Feld; die Standardfelder from_date/to_date sind
	genau dieser Zeitraum und werden von der E-Rechnung als Leistungsdatum (BT-72)
	gelesen. Deshalb nur umbenennen, kein zweites Feld daneben.
	Laeuft still (Log), damit ein Migrate ohne Print Format nicht haengt."""
	try:
		if not frappe.db.exists("Print Format", RECHNUNG_PRINT_FORMAT):
			return

		from frappe.custom.doctype.property_setter.property_setter import make_property_setter

		# DocType-Ebene: nur ueber die dict-Form landet der Eintrag wirklich auf dem
		# DocType (doctype_or_field="DocType"); die Positionsargumente erzeugen sonst
		# einen DocField-Eintrag ohne Feldnamen, der nie greift.
		frappe.make_property_setter(
			{
				"doctype_or_field": "DocType",
				"doctype": "Sales Invoice",
				"property": "default_print_format",
				"value": RECHNUNG_PRINT_FORMAT,
				"property_type": "Data",
				"module": MODULE,
			}
		)
		make_property_setter(
			"Sales Invoice", "to_date", "label", "Leistungsdatum", "Data", module=MODULE
		)
		make_property_setter(
			"Sales Invoice",
			"to_date",
			"description",
			"Tag der Leistungserbringung - erscheint auf der Rechnung und als Leistungsdatum "
			"(BT-72) in der E-Rechnung",
			"Small Text",
			module=MODULE,
		)
		make_property_setter(
			"Sales Invoice", "from_date", "label", "Leistungsbeginn", "Data", module=MODULE
		)
	except Exception:
		frappe.log_error("Zeit & Projekt: Rechnungs-Druckformat konnte nicht gesetzt werden")


def _belegvorgaben_abgleichen():
	"""Site-Einstellungen setzen, die zu den Belegdrucken und zur E-Rechnung gehoeren.

	Ohne das waeren die Vorgaben nur von Hand in der Datenbank gesetzt und gingen bei
	einer neuen Site oder einem Restore verloren: Zahlungsart im Zahlungsplan,
	Zahlungsbedingung, Kundennummernkreis und E-Rechnungsprofil.
	Alles nur setzen, wenn die Voraussetzungen da sind - sonst still ueberspringen.
	"""
	try:
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter

		from rechnung_de.rechnung import zahlungsart_mit_bankkonto

		# Zahlungsart: erste Zahlungsart, hinter der ein Bankkonto mit IBAN haengt
		firma = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
		if firma:
			zahlungsart = zahlungsart_mit_bankkonto(firma)
			if zahlungsart:
				make_property_setter(
					"Payment Schedule", "mode_of_payment", "default", zahlungsart, "Data", module=MODULE
				)

		# Zahlungsbedingung: nur uebernehmen, wenn genau eine Vorlage existiert
		vorlagen = frappe.get_all("Payment Terms Template", pluck="name")
		if len(vorlagen) == 1:
			make_property_setter(
				"Sales Invoice", "payment_terms_template", "default", vorlagen[0], "Link"
			)

		# Kundennummern: fortlaufende Serie statt Kundenname als Schluessel
		if frappe.db.exists("DocType", "Selling Settings"):
			settings = frappe.get_doc("Selling Settings")
			if settings.get("cust_master_name") != "Naming Series":
				settings.cust_master_name = "Naming Series"
				settings.save(ignore_permissions=True)
			make_property_setter(
				"Customer",
				"naming_series",
				"options",
				"KUNDE-.YYYY.-.####\nCUST-.YYYY.-",
				"Text",
			)
			make_property_setter(
				"Customer", "naming_series", "default", "KUNDE-.YYYY.-.####", "Text"
			)

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
		frappe.log_error("Zeit & Projekt: Belegvorgaben konnten nicht gesetzt werden")
