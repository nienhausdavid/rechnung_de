from frappe.tests import IntegrationTestCase

from rechnung_de.utils import html_zu_text


class TestHtmlZuText(IntegrationTestCase):
	"""Der Jinja-Helfer fuer Item.description (HTML-Feld) in den Druckformaten."""

	def test_auszeichnung_wird_entfernt_entities_aufgeloest(self):
		roh = "<p>Netzwerk &amp; Server<br>und <b>mehr</b></p>"
		self.assertEqual(html_zu_text(roh), "Netzwerk & Server\nund mehr")

	def test_verschachtelte_auszeichnung_und_leerraum(self):
		roh = '<div style="color:#000">\n  <span>Hallo</span>\n</div>'
		self.assertEqual(html_zu_text(roh), "Hallo")

	def test_reiner_text_bleibt_erhalten(self):
		self.assertEqual(html_zu_text("Zwei Stunden vor Ort"), "Zwei Stunden vor Ort")

	def test_leere_werte(self):
		self.assertEqual(html_zu_text(None), "")
		self.assertEqual(html_zu_text(""), "")
