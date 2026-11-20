"""Jinja-Helfer fuer die Druckformate (siehe `jinja` in hooks.py).

Die Formate selbst enthalten nur Aufrufe wie `{{ html_zu_text(row.description)|e }}`,
damit die Umwandlung an einer Stelle steht und getestet werden kann.
"""

import re

from frappe.utils.html_utils import unescape_html

# Blockenden und <br> werden zu Zeilenumbruechen (im Druck: white-space: pre-wrap)
_ZEILENENDE = re.compile(r"(?i)<br\s*/?>|</(?:p|div|li|tr|h[1-6]|blockquote)\s*>")
_TAG = re.compile(r"<[^>]*>")


def html_zu_text(wert):
	"""(Text-Editor-)HTML in reinen Text umwandeln.

	`Item.description` und vergleichbare Felder speichert Frappe als HTML:
	Auszeichnung (`<b>`, `<p>`) **und** Entities (`&amp;`, `&nbsp;`). Ein blosses
	`|e` im Druckformat wuerde die Auszeichnung als Text drucken, ein blosses
	`strip_html` liesse `&amp;` stehen (doppelt escaped im PDF).

	Rueckgabe ist reiner Text ohne Auszeichnung und ohne Entities; im Template
	muss er mit `|e` wieder escaped werden.
	"""
	if not wert:
		return ""

	text = _ZEILENENDE.sub("\n", str(wert))
	text = _TAG.sub("", text)
	text = unescape_html(text)  # &amp; -> &, &nbsp; -> geschuetztes Leerzeichen
	text = text.replace("\xa0", " ")

	# Einrueckung aus dem HTML-Quelltext entfernen, Leerzeilen begrenzen
	zeilen = [re.sub(r"[ \t]+", " ", zeile).strip() for zeile in text.splitlines()]
	text = "\n".join(zeilen)
	text = re.sub(r"\n{3,}", "\n\n", text)
	return text.strip()
