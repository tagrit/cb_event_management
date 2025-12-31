import frappe

def execute():
    """Set up the administrative contact and branding defaults for event reports"""
    settings_doctype = "Event Management Setting"
    
    if not frappe.db.exists("DocType", settings_doctype):
        return

    # Use frappe.get_single to load the settings document
    settings = frappe.get_single(settings_doctype)

    # Set default values if fields are currently empty
    if not settings.admin_email:
        settings.admin_email = "info@tagrit.com"
    
    if not settings.calendar_link:
        # Default link for the "DOWNLOAD CPD TRAINING CALENDARS" button
        settings.calendar_link = "https://yourwebsite.com/calendars"
        
    if not settings.facilitator_name:
        # Based on your brand image requirements
        settings.facilitator_name = "Priscilla Nyambura"

    settings.save(ignore_permissions=True)
    frappe.db.commit()