app_name = "rechnung_de"
app_title = "Rechnung DE"
app_publisher = "David Nienhaus"
app_description = "Rechnungsdruck und E-Rechnung fuer Deutschland"
app_email = "david@nienhaus-it.de"
app_license = "mit"

# Apps
# ------------------

required_apps = ["frappe/erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "rechnung_de",
# 		"logo": "/assets/rechnung_de/logo.png",
# 		"title": "Rechnung DE",
# 		"route": "/rechnung_de",
# 		"has_permission": "rechnung_de.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `rechnung_de/dock/rechnung_de/rechnung_de.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/rechnung_de/css/rechnung_de.css"
# app_include_js = "/assets/rechnung_de/js/rechnung_de.js"

# include js, css files in header of web template
# web_include_css = "/assets/rechnung_de/css/rechnung_de.css"
# web_include_js = "/assets/rechnung_de/js/rechnung_de.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "rechnung_de/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "rechnung_de/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "rechnung_de.utils.jinja_methods",
# 	"filters": "rechnung_de.utils.jinja_filters"
# }

# Installation
# ------------

# Uninstallation
# ------------

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "rechnung_de.utils.before_app_install"
# after_app_install = "rechnung_de.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "rechnung_de.utils.before_app_uninstall"
# after_app_uninstall = "rechnung_de.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "rechnung_de.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "rechnung_de.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "rechnung_de.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["rechnung_de.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"rechnung_de.tasks.all"
# 	],
# 	"daily": [
# 		"rechnung_de.tasks.daily"
# 	],
# 	"hourly": [
# 		"rechnung_de.tasks.hourly"
# 	],
# 	"weekly": [
# 		"rechnung_de.tasks.weekly"
# 	],
# 	"monthly": [
# 		"rechnung_de.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "rechnung_de.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "rechnung_de.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "rechnung_de.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "rechnung_de.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["rechnung_de.utils.before_request"]
# after_request = ["rechnung_de.utils.after_request"]

# Job Events
# ----------
# before_job = ["rechnung_de.utils.before_job"]
# after_job = ["rechnung_de.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"rechnung_de.auth.validate"
# ]

# on_social_login = "rechnung_de.auth.on_social_login"

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []



# Einrichtung
# -----------
after_install = "rechnung_de.install.after_install"
after_migrate = "rechnung_de.install.after_migrate"

# Jinja-Helfer fuer die Druckformate (z. B. html_zu_text)
jinja = {
	"methods": ["rechnung_de.utils"],
}

# Aufraeumen beim Deinstallieren: Druckformate und Property Setter mit Modul
# entfernt Frappe selbst, den Rest nimmt `uninstall.py` mit.
after_uninstall = "rechnung_de.uninstall.after_uninstall"

# Beleg-Hooks
# -----------
doc_events = {
	"Sales Invoice": {
		# before_validate: die E-Rechnungs-App prueft das XML in ihrem eigenen
		# validate-Handler, der je nach App-Reihenfolge vor unserem laeuft. Leistungsdatum
		# (BT-72) und Buyer-Reference (BT-10) muessen deshalb vorher stehen.
		"before_validate": [
			"rechnung_de.rechnung.ergaenze_leistungsdatum",
			"rechnung_de.rechnung.ergaenze_buyer_reference",
		],
		# validate: der Zahlungsplan wird erst im validate der Rechnung aufgebaut.
		"validate": "rechnung_de.rechnung.setze_zahlungsart",
	},
}
