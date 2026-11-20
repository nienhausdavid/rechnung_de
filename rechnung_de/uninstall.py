"""Aufraeumen, wenn die App von einer Site entfernt wird.

Frappe loescht beim `uninstall-app` alle Datensaetze, deren `module` auf das
Modul der App zeigt - also auch die Druckformate und die Property Setter dieser
App. Zwei Dinge bleiben trotzdem stehen und werden hier entfernt:

* Property Setter aus frueheren Versionen ohne Modul-Zuordnung (u. a. das
  Standard-Druckformat, der Label-Setter und der Kundennummernkreis). Ohne das
  zeigt `Sales Invoice.default_print_format` nach dem Entfernen der App auf ein
  geloeschtes Druckformat und `frappe.get_print()` faellt still auf das
  ERPNext-Standardlayout zurueck.
* `Selling Settings.cust_master_name`, das die App auf "Naming Series" gestellt
  hat. Es wird auf den ERPNext-Standard zurueckgesetzt, damit neue Kunden nach
  dem Entfernen wieder den Kundennamen als Docname bekommen.

Der Hook laeuft nach dem Loeschen von Modul und DocTypes; bereits entfernte
Setter werden uebersprungen.
"""

import frappe

from rechnung_de.install import SETZER, _setter_name


def after_uninstall():
	_setzer_entfernen()
	_nummernkreis_zuruecksetzen()
	frappe.clear_cache()


def _setzer_entfernen():
	"""Alle Setter dieser App loeschen, auch die ohne Modul-Zuordnung."""
	for doctype, fieldname, property in SETZER:
		name = _setter_name(doctype, fieldname, property)
		if frappe.db.exists("Property Setter", name):
			frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)


def _nummernkreis_zuruecksetzen():
	"""Kundennummernkreis auf den ERPNext-Standard zuruecksetzen.

	Nur wenn er noch auf dem Wert steht, den diese App gesetzt hat - eine andere
	Wahl des Nutzers wird nicht ueberschrieben.
	"""
	if (
		frappe.db.exists("DocType", "Selling Settings")
		and frappe.db.get_single_value("Selling Settings", "cust_master_name") == "Naming Series"
	):
		einstellungen = frappe.get_doc("Selling Settings")
		einstellungen.cust_master_name = "Customer Name"
		einstellungen.save(ignore_permissions=True)
