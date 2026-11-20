import frappe
from frappe.tests import IntegrationTestCase

from rechnung_de.install import MODULE, SETZER, _abgleichen, _module_nachtragen, _setter_name
from rechnung_de.uninstall import _nummernkreis_zuruecksetzen, _setzer_entfernen


class TestBelegvorgaben(IntegrationTestCase):
	"""Site-Vorgaben aus install.py und das Aufraeumen in uninstall.py.

	Die Tests laufen in einer Transaktion, die Frappe nach jedem Test
	zurueckrollt - sie veraendern die Site also nicht dauerhaft.
	"""

	def setUp(self):
		_abgleichen()

	def test_leistungsdatum_labels_werden_gesetzt(self):
		meta = frappe.get_meta("Sales Invoice", cached=False)
		self.assertEqual(meta.get_field("to_date").label, "Leistungsdatum")
		self.assertEqual(meta.get_field("from_date").label, "Leistungsbeginn")

	def test_alle_setter_tragen_das_modul(self):
		for doctype, fieldname, property in SETZER:
			name = _setter_name(doctype, fieldname, property)
			if not frappe.db.exists("Property Setter", name):
				continue  # Voraussetzung auf dieser Site nicht erfuellt
			self.assertEqual(
				frappe.db.get_value("Property Setter", name, "module"),
				MODULE,
				msg=f"{name} hat keine Modul-Zuordnung und ueberlebt ein uninstall-app",
			)

	def test_default_print_format_steht_auf_der_rechnung(self):
		meta = frappe.get_meta("Sales Invoice", cached=False)
		self.assertEqual(meta.default_print_format, "Rechnung Kleinunternehmer")

	def test_vorgabe_wird_nicht_ueberschrieben(self):
		"""Zahlungsart als Site-Entscheidung: ein vorhandener Wert bleibt stehen."""
		name = _setter_name("Payment Schedule", "mode_of_payment", "default")
		if not frappe.db.exists("Property Setter", name):
			self.skipTest("Site hat keine Zahlungsart mit Bankkonto - Vorgabe entsteht nicht")
		frappe.db.set_value("Property Setter", name, "value", "Cheque")
		_abgleichen()
		self.assertEqual(frappe.db.get_value("Property Setter", name, "value"), "Cheque")

	def test_altlast_ohne_modul_wird_uebernommen(self):
		"""Setter aus frueheren Versionen hatten kein Modul - sie werden adoptiert."""
		name = _setter_name("Sales Invoice", "to_date", "label")
		frappe.db.set_value("Property Setter", name, "module", None)
		_module_nachtragen()
		self.assertEqual(frappe.db.get_value("Property Setter", name, "module"), MODULE)

	def test_uninstall_entfernt_die_setter(self):
		_setzer_entfernen()
		for doctype, fieldname, property in SETZER:
			self.assertFalse(
				frappe.db.exists("Property Setter", _setter_name(doctype, fieldname, property)),
				msg=f"Property Setter {_setter_name(doctype, fieldname, property)} blieb stehen",
			)

	def test_uninstall_setzt_den_nummernkreis_zurueck(self):
		frappe.db.set_single_value("Selling Settings", "cust_master_name", "Naming Series")
		_nummernkreis_zuruecksetzen()
		self.assertEqual(
			frappe.db.get_single_value("Selling Settings", "cust_master_name"), "Customer Name"
		)
