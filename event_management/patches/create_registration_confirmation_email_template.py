import frappe

def execute():
    """Create email template for Event Registration Confirmation"""
    
    template_name = "Event Registration Confirmation"
    
    if frappe.db.exists("Email Template", template_name):
        print(f"ℹ️  Email template '{template_name}' already exists")
        return
    
    try:
        template = frappe.get_doc({
            "doctype": "Email Template",
            "name": template_name,
            "enabled": 1,
            "reference_doctype": "Event Registration",
            "subject": "{{ event.event_name }} Registration Confirmation",
            "use_html": 0,
            "response": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">

<p><strong>Dear {{ delegate.full_name }},</strong></p>

<p><em><strong>THIS EVENT WILL NOT BE CANCELLED OR POSTPONED</strong></em></p>

<p>We acknowledge your dedication to expand your professional horizons in the journey of career growth and development; thank you for choosing us.</p>

<p><strong>TRAINING:</strong> {{ event.event_name }}</p>
<p><strong>DATES:</strong> {{ event_date }}</p>
<p><strong>VENUE:</strong> {{ location }}</p>

<p>We have attached the: <strong>Invitation Letter & Proforma Invoice</strong> to help you/your colleagues in getting the necessary approvals for the above-mentioned training. <br>
The <strong>Course Content</strong> will be shared within 24 Hours.</p>

<p><a href="{{ cpd_calendar_link }}" style="color: #1a0dab; text-decoration: underline; font-weight: bold;">DOWNLOAD CPD TRAINING CALENDARS</a> to access the full listing of our competency <strong>NITA & ODPC APPROVED</strong> programs <span style="color: #555;">designed to meet your researched needs, rather than standard packages.</span></p>

<p>Don't hesitate to contact us anytime for more information/support in your learning/development - 
<a href="tel:0722998105" style="color: #1a0dab;">0722-998-105</a> / 
<a href="tel:0717165425" style="color: #1a0dab;">0717-165-425</a> / 
<a href="tel:0712843395" style="color: #1a0dab;">0712-843-395</a> day/ night.</p>

</div>"""
        })
        
        template.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Email template '{template_name}' created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating template: {str(e)}")
        frappe.log_error(f"Error in patch: {str(e)}")
        raise
