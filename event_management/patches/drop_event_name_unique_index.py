import frappe


def execute():
    """Drop the leftover unique index on Event Name.event_name.

    The field used to be a unique Data field used for naming. It is now a
    Small Text field (long titles, no longer used for naming) and the
    "unique" property has been removed from the DocType, but Frappe's schema
    sync does not drop unique indexes on Text/Small Text/Long Text columns
    automatically, so the old constraint would otherwise be left behind and
    could block legitimately duplicate long event titles.
    """
    if not frappe.db.exists("DocType", "Event Name"):
        return

    index_exists = frappe.db.sql(
        """
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = 'tabEvent Name'
          AND index_name = 'event_name'
        LIMIT 1
        """
    )

    if index_exists:
        frappe.db.sql("ALTER TABLE `tabEvent Name` DROP INDEX `event_name`")
        frappe.db.commit()
