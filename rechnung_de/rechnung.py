"""Beleg-Hooks fuer Rechnungsdruck und E-Rechnung (Deutschland).

Diese App kuemmert sich um alles, was mit dem Rechnungsbeleg zu tun hat:
Zahlungsweg fuer die E-Rechnung, Leistungsdatum, Buyer-Reference.
"""

import frappe
from frappe.utils import getdate


def setze_zahlungsart(doc, method=None):
	"""Zahlungsplan-Zeilen ohne Zahlungsart auffuellen.

	Die Zahlungsart bestimmt das Bankkonto, das als Zahlungsweg (BG-17) in die
	E-Rechnung geht. ERPNext uebernimmt sie beim Aufbau des Zahlungsplans nicht
	aus der Zahlungsbedingung, deshalb hier: nur leere Zeilen fuellen, nichts
	ueberschreiben. Ohne passende Zahlungsart bleibt die Zeile unveraendert.
	"""
	fehlend = [row for row in doc.get("payment_schedule") or [] if not row.get("mode_of_payment")]
	if not fehlend:
		return
	zahlungsart = zahlungsart_mit_bankkonto(doc.company)
	if not zahlungsart:
		return
	for row in fehlend:
		row.mode_of_payment = zahlungsart


def zahlungsart_mit_bankkonto(company):
	"""Erste Zahlungsart (Typ Bank) der Firma, hinter der ein aktives Bankkonto
	mit IBAN haengt - nur so entsteht ein Zahlungsweg in der E-Rechnung."""
	for zahlungsart in frappe.get_all(
		"Mode of Payment", filters={"type": "Bank", "enabled": 1}, order_by="name asc", pluck="name"
	):
		konto = frappe.db.get_value(
			"Mode of Payment Account",
			{"parent": zahlungsart, "parenttype": "Mode of Payment", "company": company},
			"default_account",
		)
		if not konto:
			continue
		hat_iban = frappe.db.exists(
			"Bank Account",
			{
				"account": konto,
				"company": company,
				"is_company_account": 1,
				"disabled": 0,
				"iban": ["is", "set"],
			},
		)
		if hat_iban:
			return zahlungsart
	return None


def ergaenze_leistungsdatum(doc, method=None):
	"""Leistungsdatum auf der Rechnung sicherstellen.

	§ 14 Abs. 4 Nr. 6 UStG verlangt den Zeitpunkt der Leistung. ERPNext traegt ihn
	in from_date/to_date; die E-Rechnung liest to_date als Leistungsdatum (BT-72).
	Fehlt der Wert, wird das Rechnungsdatum gesetzt - nur fuellen, nie ueberschreiben.
	"""
	if not doc.get("to_date"):
		doc.to_date = doc.posting_date or getdate()


def ergaenze_buyer_reference(doc, method=None):
	"""Buyer-Reference (BT-10) fuellen, wenn sie fehlt.

	XRechnung verlangt BT-10 immer (KoSIT-Regel BR-DE-15, fatal) - unabhaengig davon,
	ob an eine Behoerde fakturiert wird. Im Behordenfall steht dort die Leitweg-ID des
	Kunden, im Geschaeftskundenfall die Bestell- oder Kundennummer. Fehlt beides,
	blockiert die Rechnung sonst beim Buchen.
	"""
	if doc.get("einvoice_profile") != "XRECHNUNG" or doc.get("buyer_reference"):
		return
	doc.buyer_reference = doc.get("customer") or doc.get("customer_name")
