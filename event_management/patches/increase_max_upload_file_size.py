import frappe


def execute():
    """Raise the default max attachment/upload size to 200MB for event documents
    (proforma invoices, contracts, CVs, etc.) unless an admin already changed it."""
    settings = frappe.get_single("System Settings")

    if not settings.max_file_size:
        settings.max_file_size = 200
        settings.save(ignore_permissions=True)
        frappe.db.commit()
