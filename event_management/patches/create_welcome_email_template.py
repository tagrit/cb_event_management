import frappe

def execute():
    """Create email template for Event Welcome with exact styling from image"""
    
    template_name = "Event Welcome"
    
    if frappe.db.exists("Email Template", template_name):
        print(f"ℹ️  Email template '{template_name}' already exists")
        return
    
    try:
        template = frappe.get_doc({
            "doctype": "Email Template",
            "name": template_name,
            "enabled": 1,
            "reference_doctype": "Event Registration",
            "subject": "Welcome to {{ event.event_name }}",
            "use_html": 0,
            "response": """
<div style="font-family: Arial, sans-serif; color: #333; line-height: 1.5; max-width: 600px; margin: 0 auto;">
    
    <p style="color: #20639B; font-weight: bold; font-size: 16px; margin-bottom: 20px;">Dear {{ delegate.full_name }},</p>

    <p style="margin-bottom: 20px;">Thank you for choosing <strong>The WORLD'S BEST CPD PROVIDER.</strong></p>

    <p style="margin-bottom: 20px;">We're excited to have your colleagues join us for the <strong>{{ event.event_name }}</strong>, scheduled from <strong>{{ event_date }}</strong>, to <strong>{{ location }}</strong>.</p>

    <p style="margin-bottom: 20px;">We have attached the <strong>Program Outline, Seminar Details,</strong> and <strong>Information on Accommodations and Amenities</strong> to help them plan their week.</p>

    <p style="margin-bottom: 10px;">Expect:</p>
    <ul style="list-style-type: disc; margin-left: 40px; margin-bottom: 20px;">
        <li style="margin-bottom: 5px;">Relevant and Up-to-Date Industry Insights</li>
        <li style="margin-bottom: 5px;">Enhanced Skills and Competencies</li>
        <li style="margin-bottom: 5px;">Recognition and Accreditation</li>
    </ul>

    <p style="margin-bottom: 25px;">For further inquiries, reach out to the Event Facilitator directly: <strong>Priscilla Nyambura +254 712 843395</strong></p>

    <p style="color: #20639B; margin-top: 25px;">Kind regards,</p>

</div>"""
        })
        
        template.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Email template '{template_name}' created successfully with exact image styling.")
        
    except Exception as e:
        frappe.log_error(f"Error in Event Welcome patch: {str(e)}")
        raise