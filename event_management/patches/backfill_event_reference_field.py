import frappe


def execute():
    """Backfill Event Registration.event_reference from the legacy event_name column.

    event_name used to be the Link field itself (Event Name's docname was the full
    event title). It is now a read-only fetched field and event_reference is the
    real Link, so existing rows need event_reference populated from the value that
    used to live in event_name before it becomes fetch-only.
    """
    if not frappe.db.exists("DocType", "Event Registration"):
        return

    if not frappe.db.has_column("Event Registration", "event_reference"):
        return

    frappe.db.sql("""
        UPDATE `tabEvent Registration`
        SET event_reference = event_name
        WHERE (event_reference IS NULL OR event_reference = '')
          AND event_name IS NOT NULL AND event_name != ''
    """)

    frappe.db.commit()
