import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days, now, get_datetime, nowdate, formatdate, get_url, validate_email_address
from frappe.utils.pdf import get_pdf
import hashlib
import json
import base64
from frappe import _  
import os
import re


class EventRegistration(Document):
    def validate(self):
        """This runs before saving the document"""
        if len(self.delegates) != self.number_of_delegates:
            frappe.throw(f"You said {self.number_of_delegates} delegates but added {len(self.delegates)} to the list.")

        if self.start_date and self.end_date:
            if get_datetime(self.end_date) < get_datetime(self.start_date):
                frappe.throw("End date cannot be before start date!")

        self.revenue = self.number_of_delegates * self.charges_per_delegate
        
        # Helper methods called on 'self'
        self.generate_event_identifier()

        for delegate in self.delegates:
            if not delegate.confirmation_token:
                delegate.confirmation_token = self.generate_confirmation_token(delegate.email)

        self.update_all_confirmed_status()
        
    def before_insert(self):
        """Runs once when the document is first created"""
        self.set_default_attachments()

    def set_default_attachments(self):
        """Pre-populate the child table with standard document requirements"""
        default_docs = [
            {"name": "Program Outline", "desc": "Detailed schedule of the training sessions."},
            {"name": "Seminar Details", "desc": "Overview of topics, speakers, and objectives."},
            {"name": "Accommodations & Amenities", "desc": "Information regarding stay and local facilities."}
        ]

        # Only add if the table is empty to avoid duplicates
        if not self.get("welcome_attachments"):
            for doc in default_docs:
                self.append("welcome_attachments", {
                    "document_name": doc["name"],
                    "description": doc["desc"]
                })
        
    def update_all_confirmed_status(self):
        """Check if all delegates have confirmed"""
        if not self.delegates:
            self.all_confirmed = 0
            return
        all_confirmed = all(d.confirmed for d in self.delegates)
        self.all_confirmed = 1 if all_confirmed else 0
        
    def on_update(self):
        """This runs after saving the document (catches manual updates)"""
        # Recalculate all_confirmed status on every update
        old_status = self.all_confirmed
        all_confirmed = all(d.confirmed for d in self.delegates) if self.delegates else False
        new_status = 1 if all_confirmed else 0
        
        # Only update if status changed to avoid infinite loop
        if old_status != new_status:
            frappe.db.set_value("Event Registration", self.name, "all_confirmed", new_status, update_modified=False)


    def autoname(self):
            """
            This method runs BEFORE the document is created.
            Whatever you set as self.name here becomes the Unique ID.
            """
            # 1. Clean strings (3 letters max)
            def get_code(text):
                if not text: return "NA"
                return re.sub(r'[^a-zA-Z0-9]', '', text)[:3].upper()

            org = get_code(self.organization_name)
            loc = get_code(self.event_location)
            
            # Format date as YYMMDD
            dt = getdate(self.start_date).strftime('%y%m%d') if self.start_date else "000000"
            
            base_id = f"{org}-{loc}-{dt}"

            # 2. Check for uniqueness and add a sequence suffix
            # We search the database for how many records start with this base_id
            existing_count = frappe.db.count("Event Registration", {
                "name": ["like", f"{base_id}-%"]
            })
            
            # Sequence 01, 02, etc.
            suffix = str(existing_count + 1).zfill(2)
            
            # SET THE NAME (This is the critical part)
            self.name = f"{base_id}-{suffix}"
        
             
        
    def generate_event_identifier(self):
        """
        Creates a guaranteed unique ID: ORG-LOC-YYMMDD-SEQ
        Example: TAG-NAI-260125-01
        """
        if all([self.organization_name, self.event_location, self.start_date]):
            # 1. Clean strings (3 letters max)
            def get_code(text):
                return re.sub(r'[^a-zA-Z0-9]', '', text)[:3].upper()

            org = get_code(self.organization_name)
            loc = get_code(self.event_location)
            dt = getdate(self.start_date).strftime('%y%m%d')
            
            base_id = f"{org}-{loc}-{dt}"

            # 2. Check for uniqueness and add a sequence suffix if needed
            # Only run this if the identifier isn't set yet or if core fields changed
            if not self.event_identifier or not self.event_identifier.startswith(base_id):
                existing_count = frappe.db.count("Event Registration", {
                    "event_identifier": ["like", f"{base_id}%"],
                    "name": ["!=", self.name] # Don't count yourself
                })
                
                # Sequence 01, 02, etc.
                suffix = str(existing_count + 1).zfill(2)
                self.event_identifier = f"{base_id}-{suffix}"
                
    def generate_confirmation_token(self, email):
        """Generate unique confirmation token for delegate"""
        token_string = f"{self.name}-{email}-{now()}"
        return hashlib.sha256(token_string.encode()).hexdigest()[:32]

    def update_all_confirmed_status(self):
        """Check if all delegates have confirmed"""
        if not self.delegates:
            self.all_confirmed = 0
            return
        all_confirmed = all(d.confirmed for d in self.delegates)
        self.all_confirmed = 1 if all_confirmed else 0

    def on_submit(self):
        # Only send invitations if this is NOT an amendment
        if not self.amended_from:
            self.send_invitations_to_all_delegates()
        else:
            frappe.msgprint(_("This is an amended record. Invitations were not re-sent automatically."))

    def _get_attendance_email_template(self):
        """Helper to resolve template using exact name from your patch"""
        template_name = "Event Registration Confirmation"
        if frappe.db.exists("Email Template", template_name):
            return {"type": "ui", "name": template_name}
        return {
            "type": "file",
            "path": "event_management/templates/emails/registration_confirmation.html"
        }

    def send_invitations_to_all_delegates(self):
        """Bulk send using the exact structure of your UI template with PDF attachments"""
        if not self.delegates:
            frappe.msgprint("No delegates found!")
            return

        success_count = 0
        template_info = self._get_attendance_email_template()
        
        for delegate in self.delegates:
            if delegate.confirmed:
                continue
            try:
                self._send_single_invitation(delegate, template_info)
                success_count += 1
            except Exception:
                frappe.log_error(frappe.get_traceback(), f"Invitation failed for {delegate.email}")

        if success_count > 0:
            self.db_set("invitation_sent", 1)
            frappe.msgprint(f"✅ {success_count} Invitations sent successfully!")

    def _send_single_invitation(self, delegate, template_info):
        """Send email to a single delegate with PDF attachments"""
        base_url = get_url()
        confirmation_link = (
            f"{base_url}/api/method/event_management.event_management.doctype."
            f"event_registration.event_registration.confirm_delegate?token={delegate.confirmation_token}"
        )

        settings = frappe.get_doc("Event Management Setting")
        
        template_args = {
            "event": self,
            "delegate": {
                "full_name": f"{delegate.first_name} {delegate.last_name}",
                "email": delegate.email,
            },
            "event_date": f"{formatdate(self.start_date, 'dd MMM yyyy')} to {formatdate(self.end_date, 'dd MMM yyyy')}",
            "location": f"{self.event_venue}, {self.event_location}",
            "confirmation_link": confirmation_link,
            "cpd_calendar_link": settings.calendar_link or "https://tagrit.com/calendars",
        }

        # Generate PDF attachments
        attachments = self._generate_pdf_attachments(template_args)

        if template_info["type"] == "ui":
            email_template = frappe.get_doc("Email Template", template_info["name"])
            subject = frappe.render_template(email_template.subject, template_args)
            message = frappe.render_template(email_template.response, template_args)
            frappe.sendmail(
                recipients=[delegate.email], 
                subject=subject, 
                message=message,
                attachments=attachments
            )
        else:
            frappe.sendmail(
                recipients=[delegate.email],
                subject=f"{self.event_name} Registration Confirmation",
                template=template_info["path"],
                args=template_args,
                attachments=attachments
            )

    def _generate_pdf_attachments(self, template_args):
        attachments = []
        try:
            # Ensure the template knows it's rendering for a PDF
            template_args.update({"is_pdf": True})

            # 1. Fetch paths from Event Management Setting
            settings = frappe.get_doc("Event Management Setting")
            
            # 2. Helper to find the file on the server (handles Public and Private)
            def get_full_path(file_url):
                if not file_url: 
                    return None
                clean_url = file_url.lstrip("/")
                # If it's private, it's in the site root's private folder
                if clean_url.startswith("private/"):
                    return frappe.get_site_path(clean_url)
                # Otherwise, it's in the public folder
                return frappe.get_site_path("public", clean_url)

            # 3. Process Logo (Dynamic Base64)
            logo_path = get_full_path(settings.company_logo)
            logo_base64 = ""
            if logo_path and os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    logo_base64 = base64.b64encode(f.read()).decode('utf-8')

            # 4. Process Signature (Dynamic Base64)
            signature_path = get_full_path(settings.company_signature)
            signature_base64 = ""
            if signature_path and os.path.exists(signature_path):
                with open(signature_path, 'rb') as f:
                    signature_base64 = base64.b64encode(f.read()).decode('utf-8')

            # 5. Add encoded data to template arguments
            template_args.update({
                "logo_base64": logo_base64,
                "signature_base64": signature_base64
            })

            # 6. Generate Invitation PDF
            invitation_html = frappe.render_template(
                "event_management/templates/attachments/training_invitation_letter.html",
                template_args
            )
            attachments.append({
                "fname": f"Invitation_{self.name}.pdf",
                "fcontent": get_pdf(invitation_html)
            })
            
            # 7. Generate Proforma PDF
            invoice_html = frappe.render_template(
                "event_management/templates/attachments/proforma_invoice.html",
                template_args
            )
            attachments.append({
                "fname": f"Proforma_{self.name}.pdf",
                "fcontent": get_pdf(invoice_html)
            })
            
        except Exception:
            # Log the full traceback to the 'Error Log' DocType
            frappe.log_error(frappe.get_traceback(), "PDF Attachment Generation Failed")
        
        return attachments
            
# API endpoint for delegate confirmation
@frappe.whitelist(allow_guest=True)
def confirm_delegate(token):
    """Confirm delegate attendance via email link"""
    if not token:
        return {"success": False, "message": "Invalid confirmation link"}

    # Find the delegate with this token
    delegates = frappe.get_all(
        "Event Delegate",
        filters={"confirmation_token": token},
        fields=["name", "parent", "first_name", "last_name", "email", "confirmed"],
    )

    if not delegates:
        return {"success": False, "message": "Invalid or expired confirmation link"}

    delegate = delegates[0]

    # Check if already confirmed
    if delegate.confirmed:
        return {
            "success": True,
            "already_confirmed": True,
            "message": f"Thank you {delegate.first_name}! Your attendance was already confirmed.",
        }

    try:
        # Update delegate confirmation
        frappe.db.set_value(
            "Event Delegate",
            delegate.name,
            {"confirmed": 1, "confirmation_date": now()},
        )

        # Get event details
        event = frappe.get_doc("Event Registration", delegate.parent)

        # Update all_confirmed status
        event.update_all_confirmed_status()
        event.save()

        # Send confirmation email
        frappe.sendmail(
            recipients=[delegate.email],
            subject=f"Confirmation Received - {event.event_name}",
            message=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #4CAF50;">✓ Attendance Confirmed!</h2>
                
                <p>Dear {delegate.first_name} {delegate.last_name},</p>
                
                <p>Thank you for confirming your attendance at <strong>{event.event_name}</strong>.</p>
                
                <div style="background-color: #e8f5e9; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Your attendance is confirmed for:</strong></p>
                    <p style="margin: 10px 0 0 0;">{event.start_date} to {event.end_date}</p>
                    <p style="margin: 5px 0 0 0;">{event.event_venue}, {event.event_location}</p>
                </div>
                
                <p>You will receive additional information about the event closer to the date.</p>
                
                <p>Best regards,<br>Event Management Team</p>
            </div>
            """,
        )

        frappe.db.commit()

        return {
            "success": True,
            "message": f"Thank you {delegate.first_name}! Your attendance has been confirmed.",
            "event_name": event.event_name,
            "event_date": f"{event.start_date} to {event.end_date}",
        }

    except Exception as e:
        frappe.log_error(f"Confirmation error: {str(e)}")
        return {
            "success": False,
            "message": "An error occurred. Please contact the event organizer.",
        }


@frappe.whitelist()
def get_confirmation_summary(event_name):
    """Get summary of delegate confirmations for display"""
    event = frappe.get_doc("Event Registration", event_name)

    total = len(event.delegates)
    confirmed = sum(1 for d in event.delegates if d.confirmed)
    pending = total - confirmed

    delegates_list = []
    for d in event.delegates:
        delegates_list.append(
            {
                "name": f"{d.first_name} {d.last_name}",
                "email": d.email,
                "confirmed": d.confirmed,
                "confirmation_date": d.confirmation_date,
            }
        )

    return {
        "total": total,
        "confirmed": confirmed,
        "pending": pending,
        "percentage": round((confirmed / total * 100) if total > 0 else 0, 1),
        "delegates": delegates_list,
    }


def _get_attendance_email_template():
    """
    Prefer UI Email Template if client created one.
    Fallback to file-based template shipped with the app.
    """
    if frappe.db.exists("Email Template", "Event Attendance Confirmation"):
        return {"type": "ui", "name": "Event Attendance Confirmation"}

    return {
        "type": "file",
        "path": "event_management/templates/emails/attendance_confirmation.html",
    }


@frappe.whitelist()
def resend_invitation(event_name, delegate_email):
    """Resend invitation with PDF attachments"""
    # Validate inputs early (fail fast)
    if not event_name or not delegate_email:
        frappe.throw("Missing event or delegate email")

    validate_email_address(delegate_email, throw=True)

    # Load event (server-side, trusted context)
    event = frappe.get_doc("Event Registration", event_name)

    # Locate delegate
    delegate = next((d for d in event.delegates if d.email == delegate_email), None)

    if not delegate:
        frappe.throw("Delegate not found for this event")

    if delegate.confirmed:
        frappe.msgprint(
            f"{delegate.first_name} {delegate.last_name} has already confirmed attendance."
        )
        return

    # Build secure confirmation link (guest-safe)
    confirmation_link = (
        get_url()
        + "/api/method/event_management.event_management.doctype.event_registration."
        "event_registration.confirm_delegate" + f"?token={delegate.confirmation_token}"
    )

    # Prepare template variables (shared by subject + body)
    template_args = {
        "division": event.division or "Training",
        "event_date": formatdate(event.start_date, "dd MMM yyyy"),
        "location": f"{event.event_venue}, {event.event_location}",
        "delegate": {"full_name": f"{delegate.first_name} {delegate.last_name}"},
        "event": event,
        "confirmation_link": confirmation_link,
        "client_list": [f"{d.first_name} {d.last_name}" for d in event.delegates],
        "company_name": frappe.defaults.get_global_default("company"),
    }

    # Resolve template (UI override OR app default)
    template_info = _get_attendance_email_template()

    # Send email (queue-based, production safe)
    try:
        if template_info["type"] == "ui":
            email_template = frappe.get_doc("Email Template", template_info["name"])
            subject = frappe.render_template(email_template.subject, template_args)
            message = frappe.render_template(email_template.response, template_args)

            frappe.sendmail(
                recipients=[delegate.email],
                subject=subject,
                message=message,
            )
        else:
            frappe.sendmail(
                recipients=[delegate.email],
                template=template_info["path"],
                args=template_args,
            )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Resend Attendance Invitation Failed")
        frappe.throw(
            "Failed to send invitation email. Please check Email Settings or logs."
        )


@frappe.whitelist()
def send_confirmation_list_email(recipient=None):
    """
    Sends a detailed report of all upcoming events showing confirmation status.
    Shows all events regardless of confirmation percentage.
    If no recipient is provided, it defaults to the Admin Email in settings.
    """
    today = getdate(nowdate())
    
    # Get ALL upcoming submitted events, regardless of confirmation status
    events = frappe.get_all(
        "Event Registration",
        filters={
            "docstatus": 1,
            "start_date": [">=", today]  # Only upcoming events
        },
        fields=["name", "event_name", "organization_name", "start_date", "end_date", "all_confirmed"],
        order_by="start_date asc"  # Sort by date, earliest first
    )

    if not events:
        frappe.msgprint("No upcoming events found for reporting.")
        return

    # Generate the professional HTML body
    html_report = _generate_event_report_html(events, report_type="upcoming_all")

    # Determine recipient
    if not recipient:
        recipient = frappe.db.get_single_value("Event Management Setting", "admin_email") or "info@tagrit.com"

    try:
        frappe.sendmail(
            recipients=[recipient],
            subject=f"Upcoming Events Confirmation Status - {formatdate(nowdate())}",
            message=html_report,
            now=True
        )
        frappe.msgprint(f"✅ Report successfully sent to {recipient}!")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Event Report Failed")
        frappe.msgprint("Failed to send report. Check Error Logs.")


def _generate_event_report_html(events, report_type="all"):
    """Helper to build the HTML table structure for reports"""
    
    # Simplified title logic - only two types needed
    if report_type == "upcoming_all":
        title = "Upcoming Events - Confirmation Status Report"
        subtitle = f"Showing all {len(events)} upcoming events with delegate confirmation details"
    else:
        title = "Event Confirmation Status Report"
        subtitle = f"Total Events: {len(events)}"
    
    html = f"""<div style="font-family: Arial, sans-serif; color: #333;">
                <h2>{title}</h2>
                <p>Generated on: {formatdate(nowdate())}</p>
                <p style="color: #666;">{subtitle}</p>
                <hr>"""

    for event_summary in events:
        event = frappe.get_doc("Event Registration", event_summary.name)
        total = len(event.delegates)
        confirmed = sum(1 for d in event.delegates if d.confirmed)
        pending = total - confirmed
        percentage = round((confirmed / total * 100) if total > 0 else 0, 1)
        status_color = "#20639B" if event.all_confirmed else "#ff9800"
        
        # Calculate days until event
        days_until = (getdate(event.start_date) - getdate(nowdate())).days
        days_text = f"{days_until} days away" if days_until > 0 else "Today" if days_until == 0 else f"{abs(days_until)} days ago"

        html += f"""
        <div style="margin: 20px 0; border: 1px solid #eee; padding: 15px; border-radius: 8px;">
            <h3 style="color: {status_color};">{event.event_name}</h3>
            <p>
                <strong>Organization:</strong> {event.organization_name} | 
                <strong>Date:</strong> {formatdate(event.start_date)} to {formatdate(event.end_date)} 
                <span style="color: #666;">({days_text})</span>
            </p>
            <p><strong>Venue:</strong> {event.event_venue}, {event.event_location}</p>
            <p style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin: 10px 0;">
                <strong>Confirmation Status:</strong> 
                <span style="color: #20639B; font-weight: bold;">{confirmed} Confirmed</span> | 
                <span style="color: #ff9800; font-weight: bold;">{pending} Pending</span> | 
                <span style="color: #666; font-weight: bold;">{percentage}% Complete</span>
            </p>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <tr style="background: #f8f9fa; border-bottom: 2px solid #eee;">
                    <th style="padding: 8px; text-align: left;">Delegate</th>
                    <th style="padding: 8px; text-align: left;">Email</th>
                    <th style="padding: 8px; text-align: center;">Status</th>
                    <th style="padding: 8px; text-align: center;">Confirmed On</th>
                </tr>"""

        for d in event.delegates:
            status = "✅ Confirmed" if d.confirmed else "⏳ Pending"
            row_bg = "#f0fff4" if d.confirmed else "#fffaf0"
            conf_date = formatdate(d.confirmation_date) if d.confirmation_date else "N/A"
            html += f"""<tr style="background: {row_bg}; border-bottom: 1px solid #eee;">
                        <td style="padding: 8px;">{d.first_name} {d.last_name}</td>
                        <td style="padding: 8px;">{d.email}</td>
                        <td style="padding: 8px; text-align: center;">{status}</td>
                        <td style="padding: 8px; text-align: center;">{conf_date}</td>
                    </tr>"""
        html += "</table></div>"
    
    html += "</div>"
    return html

@frappe.whitelist()
def send_welcome_email_to_confirmed(event_name):
    """Send welcome email with user-specified attachments to confirmed delegates"""
    if not event_name:
        frappe.throw("Missing event name")

    event = frappe.get_doc("Event Registration", event_name)

    # 1. Get only confirmed delegates
    confirmed_delegates = [d for d in event.delegates if d.confirmed]
    if not confirmed_delegates:
        frappe.msgprint("No confirmed delegates yet!")
        return

    # 2. Collect the user-uploaded attachments from the child table
    # 2. Collect the user-uploaded attachments from the child table
    custom_attachments = []
    for row in event.get("welcome_attachments"):
        if row.file:
            # Get the File document using the URL
            file_doc = frappe.get_doc("File", {"file_url": row.file})
            
            # Use the ACTUAL filename from the system (e.g., seminar_v2.pdf)
            # This ensures the extension (.pdf, .png) is always present
            custom_attachments.append({
                "fname": file_doc.file_name, 
                "fcontent": file_doc.get_content()
            })

    # 3. Resolve template
    template_info = _get_event_welcome_template()
    success_count = 0

    for delegate in confirmed_delegates:
        try:
            template_args = {
                "event": event,
                "delegate": {
                    "full_name": f"{delegate.first_name} {delegate.last_name}",
                    "email": delegate.email,
                },
                "event_date": f"{formatdate(event.start_date, 'dd MMM yyyy')} to {formatdate(event.end_date, 'dd MMM yyyy')}",
                "location": f"{event.event_venue}, {event.event_location}",
            }

            if template_info["type"] == "ui":
                email_template = frappe.get_doc("Email Template", template_info["name"])
                subject = frappe.render_template(email_template.subject, template_args)
                message = frappe.render_template(email_template.response, template_args)

                frappe.sendmail(
                    recipients=[delegate.email],
                    subject=subject,
                    message=message,
                    attachments=custom_attachments, # Attach the user documents here
                    now=True
                )
            else:
                frappe.sendmail(
                    recipients=[delegate.email],
                    subject=f"Welcome to {event.event_name}",
                    template=template_info["path"],
                    args=template_args,
                    attachments=custom_attachments # Attach here as well
                )
            success_count += 1

        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Welcome Email Failed for {delegate.email}")

    if success_count > 0:
        event.db_set("welcome_email_sent", 1)
        frappe.msgprint(f"✅ Welcome email with {len(custom_attachments)} attachments sent to {success_count} delegates!")

def _get_event_welcome_template():
    """Helper to find the Event Welcome template"""
    template_name = "Event Welcome"
    if frappe.db.exists("Email Template", template_name):
        return {"type": "ui", "name": template_name}
    
    return {
        "type": "file",
        "path": "event_management/templates/emails/event_welcome.html",
    }
    
@frappe.whitelist()
def get_venues_by_location(location):
    """Get all venues for a specific location"""
    venues = frappe.get_all(
        "Event Venue",
        filters={"location": location},
        fields=["name", "venue_name", "capacity"],
    )
    return venues


@frappe.whitelist()
def send_automated_reminders():
    """Runs every Monday at 9am"""
    today = getdate(nowdate())
    
    # Range: 7 days from now (Next Monday) to 13 days from now (Next Sunday)
    start_range = add_days(today, 7)
    end_range = add_days(today, 13)
    
    events = frappe.get_all(
        "Event Registration",
        filters={
            "docstatus": 1,
            "start_date": ["between", [start_range, end_range]],
            "all_confirmed": 0
        },
        fields=["name"]
    )

    for e in events:
        doc = frappe.get_doc("Event Registration", e.name)
        for d in doc.delegates:
            if not d.confirmed:
                resend_invitation(doc.name, d.email)
        

@frappe.whitelist()
def trigger_automated_wednesday_report():
    """
    Scheduled job for Wednesdays. 
    Finds ALL upcoming events (starting in the next 10 days) showing their confirmation status,
    regardless of how many delegates have confirmed.
    """
    today = getdate(nowdate())
    reporting_window = add_days(today, 10)

    # Find ALL submitted upcoming events, regardless of confirmation status
    events_to_process = frappe.get_all(
        "Event Registration",
        filters={
            "docstatus": 1,
            "start_date": ["between", [today, reporting_window]],  # Next 10 days
            "final_report_sent": 0
        },
        fields=["name", "event_name", "organization_name", "start_date", "end_date", "all_confirmed"],
        order_by="start_date asc"
    )

    if not events_to_process:
        # Optional: Log that no events need reporting
        frappe.log_error("No upcoming events found for Wednesday report", "Wednesday Report - No Events")
        return

    # Use existing professional HTML generator
    html_report = _generate_event_report_html(events_to_process, report_type="upcoming_all")

    # Send the mail
    recipient = frappe.db.get_single_value("Event Management Setting", "admin_email") or "info@tagrit.com"
    
    frappe.sendmail(
        recipients=[recipient],
        subject=f"Upcoming Events Status - Weekly Report - {formatdate(nowdate())}",
        message=html_report,
        now=True
    )

    # Mark them as sent so they don't send again next Wednesday
    for e in events_to_process:
        frappe.db.set_value("Event Registration", e.name, "final_report_sent", 1, update_modified=False)
    
    frappe.db.commit()
    
    # Log success
    frappe.log_error(
        f"Wednesday report sent successfully for {len(events_to_process)} events to {recipient}", 
        "Wednesday Report Success"
    )
    
@frappe.whitelist()
def get_dashboard_data():
    """Get aggregated data for Event Management dashboard"""
    
    # Total Events by Status
    draft_count = frappe.db.count("Event Registration", {"docstatus": 0})
    confirmed_count = frappe.db.count("Event Registration", {"docstatus": 1, "all_confirmed": 1})
    pending_count = frappe.db.count("Event Registration", {"docstatus": 1, "all_confirmed": 0})
    
    # Total Revenue
    total_revenue = frappe.db.sql("""
        SELECT SUM(revenue) as total
        FROM `tabEvent Registration`
        WHERE docstatus = 1
    """, as_dict=1)[0].total or 0
    
    # Total Delegates
    total_delegates = frappe.db.sql("""
        SELECT COUNT(*) as total
        FROM `tabEvent Delegate`
        WHERE parent IN (
            SELECT name FROM `tabEvent Registration` WHERE docstatus = 1
        )
    """, as_dict=1)[0].total or 0
    
    # Confirmed vs Pending Delegates
    confirmed_delegates = frappe.db.sql("""
        SELECT COUNT(*) as total
        FROM `tabEvent Delegate`
        WHERE confirmed = 1
        AND parent IN (
            SELECT name FROM `tabEvent Registration` WHERE docstatus = 1
        )
    """, as_dict=1)[0].total or 0
    
    pending_delegates = total_delegates - confirmed_delegates
    
    # Upcoming Events (next 30 days)
    upcoming_events = frappe.db.sql("""
        SELECT COUNT(*) as total
        FROM `tabEvent Registration`
        WHERE docstatus = 1
        AND start_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
    """, as_dict=1)[0].total or 0
    
    # Events by Month (last 6 months)
    events_by_month = frappe.db.sql("""
        SELECT 
            DATE_FORMAT(start_date, '%b %Y') as month,
            COUNT(*) as count
        FROM `tabEvent Registration`
        WHERE docstatus = 1
        AND start_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(start_date, '%Y-%m')
        ORDER BY start_date
    """, as_dict=1)
    
    # Revenue by Month (last 6 months)
    revenue_by_month = frappe.db.sql("""
        SELECT 
            DATE_FORMAT(start_date, '%b %Y') as month,
            SUM(revenue) as revenue
        FROM `tabEvent Registration`
        WHERE docstatus = 1
        AND start_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(start_date, '%Y-%m')
        ORDER BY start_date
    """, as_dict=1)
    
    # Top Organizations by Events
    top_organizations = frappe.db.sql("""
        SELECT 
            organization_name,
            COUNT(*) as event_count,
            SUM(revenue) as total_revenue
        FROM `tabEvent Registration`
        WHERE docstatus = 1
        GROUP BY organization_name
        ORDER BY event_count DESC
        LIMIT 5
    """, as_dict=1)
    
    # Confirmation Rate
    confirmation_rate = round((confirmed_delegates / total_delegates * 100) if total_delegates > 0 else 0, 1)
    
    return {
        "summary": {
            "draft_events": draft_count,
            "confirmed_events": confirmed_count,
            "pending_events": pending_count,
            "total_revenue": total_revenue,
            "total_delegates": total_delegates,
            "confirmed_delegates": confirmed_delegates,
            "pending_delegates": pending_delegates,
            "confirmation_rate": confirmation_rate,
            "upcoming_events": upcoming_events
        },
        "charts": {
            "events_by_month": events_by_month,
            "revenue_by_month": revenue_by_month
        },
        "top_organizations": top_organizations
    }