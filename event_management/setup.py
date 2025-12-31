import frappe

def fix_terms_and_conditions():
    """
    Ensures all Terms and Conditions have at least one module selected
    to prevent ERPNext validation errors during migration.
    """
    # Use SQL to bypass the validation that is currently crashing the site
    frappe.db.sql("""
        UPDATE `tabTerms and Conditions` 
        SET selling = 1 
        WHERE (selling = 0 OR selling IS NULL) 
          AND (buying = 0 OR buying IS NULL) 
          AND (hr = 0 OR hr IS NULL)
    """)
    frappe.db.commit()