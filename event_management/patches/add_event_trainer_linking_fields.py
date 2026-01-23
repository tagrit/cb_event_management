"""
Patch to add custom fields for Event Trainer linking

File Location: event_management/patches/v1_0/add_event_trainer_linking_fields.py

This patch will automatically run once when you execute: bench migrate
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Add custom fields to link Purchase Invoice and Payment Entry to Event Trainer"""
    
    custom_fields = {
        "Purchase Invoice": [
            {
                "fieldname": "event_trainer",
                "label": "Event Trainer",
                "fieldtype": "Link",
                "options": "Event Trainer",
                "insert_after": "supplier_name",
                "read_only": 1,
                "print_hide": 1,
                "allow_on_submit": 0,
                "translatable": 0
            }
        ],
        "Payment Entry": [
            {
                "fieldname": "event_trainer",
                "label": "Event Trainer",
                "fieldtype": "Link",
                "options": "Event Trainer",
                "insert_after": "party_name",
                "read_only": 1,
                "print_hide": 1,
                "allow_on_submit": 0,
                "translatable": 0
            }
        ]
    }
    
    # This function handles checking if fields exist and creates them if they don't
    create_custom_fields(custom_fields, update=True)
    
    frappe.db.commit()
    
    print("Custom fields for Event Trainer linking added successfully!")