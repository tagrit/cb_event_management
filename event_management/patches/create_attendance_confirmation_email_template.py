import frappe

def execute():
    """Create email template for Event Attendance Confirmation"""
    
    template_name = "Event Attendance Confirmation"
    
    if frappe.db.exists("Email Template", template_name):
        print(f"ℹ️  Email template '{template_name}' already exists")
        return
    
    try:
        template = frappe.get_doc({
            "doctype": "Email Template",
            "name": template_name,
            "enabled": 1,
            "reference_doctype": "Event Registration",
            "subject": "{{ division }} : {{ event.event_name }}, Scheduled For {{ event_date }}, At {{ location }}",
            "use_html": 0,
            "response": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">

<h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
    ATTENDANCE CONFIRMATION AND PAYMENT STATUS
</h2>

<p><strong>Event:</strong> {{ event.event_name }}</p>
<p><strong>Division:</strong> {{ division }}</p>
<p><strong>Scheduled For:</strong> {{ event_date }}</p>
<p><strong>Location:</strong> {{ location }}</p>

<hr style="margin: 20px 0;">

<p>Dear {{ delegate.full_name }},</p>

<p><strong style="color: #e74c3c;">The countdown has officially begun.</strong></p>

<p>Kindly confirm the Payment and Attendance Status for the upcoming training.</p>

<div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
    <h3 style="margin-top: 0;">Event Details</h3>
    <p><strong>Event Name:</strong> {{ event.event_name }}</p>
    <p><strong>Organization:</strong> {{ event.organization }}</p>
    <p><strong>Venue:</strong> {{ event.event_venue }}</p>
    <p><strong>Location:</strong> {{ event.event_location }}</p>
</div>

<div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
    <h3 style="margin-top: 0;">Expected Attendees</h3>
    <ul>
    {% for client in client_list %}
        <li>{{ client }}</li>
    {% endfor %}
    </ul>
</div>

<h3 style="color: #2e7d32; border-bottom: 2px solid #4CAF50; padding-bottom: 5px;">
    💳 PAYMENT STATUS
</h3>

<p>As part of the business capacity recovery measures, management has approved a policy requiring clients to pay for services and seminars upfront.</p>

<p>Upon approval of the training, we will also require an <strong>LSO / Commitment Letter</strong> from your organization for record purposes.</p>

<div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0;">
    <h3 style="margin-top: 0;">Payment Details</h3>
    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Number of Delegates:</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ event.number_of_delegates }}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Charge per Delegate:</strong></td>
            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ event.charges_per_delegate }}</td>
        </tr>
        <tr style="background-color: #4CAF50; color: white;">
            <td style="padding: 8px;"><strong>Total Amount:</strong></td>
            <td style="padding: 8px;"><strong>{{ event.revenue }}</strong></td>
        </tr>
    </table>
</div>

<p style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
    📧 Kindly share the payment evidence with our finance team via email:<br>
    <a href="mailto:customerservice@capabuil.com" style="color: #2196F3; font-size: 16px;">customerservice@capabuil.com</a>
</p>

# <div style="text-align: center; margin: 30px 0;">
#     <a href="{{ confirmation_link }}" 
#        style="background-color: #4CAF50; color: white; padding: 15px 30px; 
#               text-decoration: none; border-radius: 5px; font-size: 16px; 
#               display: inline-block;">
#         ✓ CONFIRM MY ATTENDANCE
#     </a>
# </div>

<div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
    <p>Kind regards,<br>
    <strong>{{ company_name }}</strong></p>
</div>

</div>"""
        })
        
        template.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Email template '{template_name}' created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating template: {str(e)}")
        frappe.log_error(f"Error in patch: {str(e)}")
        raise