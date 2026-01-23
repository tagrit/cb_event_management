import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """
    Patch to add trainer management custom fields
    This will run once during migration
    """
    
    custom_fields = {
        "Supplier": [
            {
                "fieldname": "is_trainer",
                "label": "Is Trainer",
                "fieldtype": "Check",
                "insert_after": "supplier_type",
                "description": "Check this if supplier is also a trainer"
            },
            {
                "fieldname": "trainer_details_section",
                "label": "Trainer Details",
                "fieldtype": "Section Break",
                "insert_after": "is_trainer",
                "depends_on": "eval:doc.is_trainer==1",
                "collapsible": 1
            },
            {
                "fieldname": "area_of_expertise",
                "label": "Area of Expertise",
                "fieldtype": "Small Text",
                "insert_after": "trainer_details_section",
                "depends_on": "eval:doc.is_trainer==1"
            },
            {
                "fieldname": "trainer_rate_type",
                "label": "Rate Type",
                "fieldtype": "Select",
                "options": "Fixed Rate\nHourly Rate\nDaily Rate",
                "insert_after": "area_of_expertise",
                "depends_on": "eval:doc.is_trainer==1"
            },
            {
                "fieldname": "trainer_rate",
                "label": "Rate Amount",
                "fieldtype": "Currency",
                "insert_after": "trainer_rate_type",
                "depends_on": "eval:doc.is_trainer==1",
                "description": "Base rate per hour/day or fixed rate per event"
            },
            {
                "fieldname": "cv_attachment",
                "label": "CV / Resume",
                "fieldtype": "Attach",
                "insert_after": "trainer_rate",
                "depends_on": "eval:doc.is_trainer==1"
            }
        ],
        "Purchase Invoice": [
            {
                "fieldname": "event_registration",
                "label": "Event Registration",
                "fieldtype": "Link",
                "options": "Event Registration",
                "insert_after": "supplier",
                "description": "Link this invoice to a training event"
            }
        ],
        "Payment Entry": [
            {
                "fieldname": "event_registration",
                "label": "Event Registration",
                "fieldtype": "Link",
                "options": "Event Registration",
                "insert_after": "party",
                "description": "Link this payment to a training event"
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    
    frappe.db.commit()