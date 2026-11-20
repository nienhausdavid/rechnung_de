import frappe
from unittest.mock import patch

from frappe.tests import IntegrationTestCase

import rechnung_de.install as install
from rechnung_de.install import (
	MODULE,
	PFLICHT_SETZER,
	SETZER,
	EINVOICE_PROFIL,
	_abgleichen,
	_module_nachtragen,
	_setter_name,
)
from rechnung_de.uninstall import _nummernkreis_zuruecksetzen, _setzer_entfernen


def _app_fehler():
	"""Namen aller Error-Log-Eintraege dieser App (`method` traegt den Titel)."""
	return set(
		frappe.get_all("Error Log", filters={"method": ["like", "Rechnung DE:%"]}, pluck="name")
	)


def _setter_loeschen(*setter):
	for doctype, fieldname, property in setter:
		name = _setter_name(doctype, fieldname, property)
		if frappe.db.exists("Property Setter", name):
			frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)


def _neue_fehler_entfernen(vorher):
	"""Error Log wieder aufraeumen, den ein Test absichtlich erzeugt hat.

	Besonders erzeugte Eintraege ueberleben den Rollback des Test-Frameworks und
	wuerden die naechste Fehlersuche auf der Test-Site verwirren.
	"""
	for name in _app_fehler() - vorher:
		frappe.delete_doc("Error Log", name, ignore_permissions=True, force=True)


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

	def test_pflicht_setter_existieren(self):
		"""Pflicht-Setter muessen da sein - fehlen sie, ist die Einrichtung kaputt.

		Frueher uebersprang `test_alle_setter_tragen_das_modul` fehlende Setter,
		deshalb blieb der Test gruen, obwohl sechs andere fielen.
		"""
		for doctype, fieldname, property in PFLICHT_SETZER:
			name = _setter_name(doctype, fieldname, property)
			self.assertTrue(
				frappe.db.exists("Property Setter", name),
				msg=f"{name} fehlt, obwohl er auf jeder Site entstehen muss",
			)

	def test_pflicht_setzer_stehen_in_der_setzer_liste(self):
		"""PFLICHT_SETZER darf nicht an SETZER vorbeilaufen (Quelle fuer Uninstall)."""
		self.assertSequenceSubset(SETZER, PFLICHT_SETZER)

	def test_alle_setter_tragen_das_modul(self):
		for setter in SETZER:
			name = _setter_name(*setter)
			if not frappe.db.exists("Property Setter", name):
				self.assertNotIn(
					setter,
					PFLICHT_SETZER,
					msg=f"{name} fehlt, obwohl er ein Pflicht-Setter ist",
				)
				continue  # Voraussetzung auf dieser Site nicht erfuellt
			self.assertEqual(
				frappe.db.get_value("Property Setter", name, "module"),
				MODULE,
				msg=f"{name} hat keine Modul-Zuordnung und ueberlebt ein uninstall-app",
			)

	def test_default_print_format_steht_auf_der_rechnung(self):
		meta = frappe.get_meta("Sales Invoice", cached=False)
		self.assertEqual(meta.default_print_format, "Rechnung Kleinunternehmer")

	def test_abgleichen_loggt_keine_neuen_fehler(self):
		"""Genau dieser Test haette die stille Fehlerserie am 2026-11-20 rot gemacht."""
		vorher = _app_fehler()
		_abgleichen()
		neu = _app_fehler() - vorher
		self.assertFalse(
			neu,
			msg="_abgleichen() hat Fehler protokolliert: "
			+ repr([frappe.db.get_value("Error Log", name, "method") for name in sorted(neu)]),
		)

	def test_ein_kaputter_setter_bricht_die_folgenden_nicht_ab(self):
		"""Faellt ein Setter aus, laufen die uebrigen Vorgaben trotzdem durch."""
		vorher = _app_fehler()
		self.addCleanup(_neue_fehler_entfernen, vorher)
		_setter_loeschen(
			("Sales Invoice", None, "default_print_format"),  # Schritt vor dem Fehler
			("Sales Invoice", "to_date", "description"),  # Schritt nach dem Fehler
			("Customer", "naming_series", "default"),  # andere Gruppe, kommt spaeter
			("Sales Invoice", "to_date", "label"),  # der Schritt, der ausfaellt
		)
		echt = install._setze_setter

		def kaputt(doctype, fieldname, property, value, property_type):
			if (doctype, fieldname, property) == ("Sales Invoice", "to_date", "label"):
				raise frappe.ValidationError("Testfehler: Modul fehlt")
			return echt(doctype, fieldname, property, value, property_type)

		with patch.object(install, "_setze_setter", kaputt):
			install._abgleichen()

		for setter in (
			("Sales Invoice", None, "default_print_format"),
			("Sales Invoice", "to_date", "description"),
			("Customer", "naming_series", "default"),
		):
			self.assertTrue(
				frappe.db.exists("Property Setter", _setter_name(*setter)),
				msg=f"{_setter_name(*setter)} fehlt - der Fehler eines Setters hat die folgenden abgebrochen",
			)

		# Der Fehler darf nicht still bleiben.
		self.assertTrue(
			frappe.db.exists(
				"Error Log", {"method": ["like", "Rechnung DE: Beschriftung von to_date%"]}
			),
			msg="Der fehlgeschlagene Setter wurde nicht protokolliert",
		)

	def test_setter_entsteht_auch_ohne_module_def(self):
		"""Fehlt der Module Def, entsteht der Setter ohne Modul statt gar nicht."""
		_setter_loeschen(("Sales Invoice", "from_date", "label"))
		name = _setter_name("Sales Invoice", "from_date", "label")
		echt = install._setze_setter_mit_modul
		aufrufe = []

		def ohne_module_def(doctype, fieldname, property, value, property_type, module):
			aufrufe.append(module)
			if module:
				raise frappe.LinkValidationError(
					"Could not find Module (for export): Rechnung DE"
				)
			return echt(doctype, fieldname, property, value, property_type, module)

		with patch.object(install, "_setze_setter_mit_modul", ohne_module_def):
			install._setze_setter("Sales Invoice", "from_date", "label", "Leistungsbeginn", "Data")

		self.assertEqual(aufrufe, [MODULE, None], msg="Es wurde nicht ohne Modul nachgelegt")
		self.assertTrue(frappe.db.exists("Property Setter", name), msg=f"{name} wurde nicht angelegt")
		self.assertFalse(frappe.db.get_value("Property Setter", name, "module"))

		# Sobald der Module Def existiert, zieht _module_nachtragen() die Zuordnung nach.
		_module_nachtragen()
		self.assertEqual(frappe.db.get_value("Property Setter", name, "module"), MODULE)

	def test_vorgabe_wird_nicht_ueberschrieben(self):
		"""Zahlungsart als Site-Entscheidung: ein vorhandener Wert bleibt stehen."""
		name = _setter_name("Payment Schedule", "mode_of_payment", "default")
		if not frappe.db.exists("Property Setter", name):
			self.skipTest("Site hat keine Zahlungsart mit Bankkonto - Vorgabe entsteht nicht")
		frappe.db.set_value("Property Setter", name, "value", "Cheque")
		_abgleichen()
		self.assertEqual(frappe.db.get_value("Property Setter", name, "value"), "Cheque")

	def test_einvoice_profil_wird_nicht_ueberschrieben(self):
		"""Profil ist eine Site-Entscheidung: XRECHNUNG bleibt bei jedem Migrate stehen."""
		feld = frappe.db.get_value(
			"Custom Field", {"dt": "Sales Invoice", "fieldname": "einvoice_profile"}, "name"
		)
		if not feld:
			self.skipTest("eu_einvoice ist auf dieser Site nicht installiert")
		vorher = frappe.db.get_value("Custom Field", feld, "default")
		self.addCleanup(frappe.db.set_value, "Custom Field", feld, "default", vorher)
		self.addCleanup(frappe.clear_cache, doctype="Sales Invoice")

		frappe.db.set_value("Custom Field", feld, "default", "XRECHNUNG")
		_abgleichen()
		self.assertEqual(frappe.db.get_value("Custom Field", feld, "default"), "XRECHNUNG")

	def test_einvoice_profil_wird_gesetzt_wenn_leer(self):
		feld = frappe.db.get_value(
			"Custom Field", {"dt": "Sales Invoice", "fieldname": "einvoice_profile"}, "name"
		)
		if not feld:
			self.skipTest("eu_einvoice ist auf dieser Site nicht installiert")
		vorher = frappe.db.get_value("Custom Field", feld, "default")
		self.addCleanup(frappe.db.set_value, "Custom Field", feld, "default", vorher)
		self.addCleanup(frappe.clear_cache, doctype="Sales Invoice")

		frappe.db.set_value("Custom Field", feld, "default", None)
		_abgleichen()
		self.assertEqual(
			frappe.db.get_value("Custom Field", feld, "default"),
			EINVOICE_PROFIL,
			msg="Ohne Vorgabe auf der Site muss install.py EN 16931 setzen",
		)

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
