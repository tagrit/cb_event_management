import frappe
from frappe.model.document import Document
from frappe.utils import now, add_days, get_datetime, nowdate, formatdate, get_url, validate_email_address
import hashlib
import json

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

    def generate_event_identifier(self):
        """Create unique ID from dates, venue and location"""
        if self.start_date and self.end_date and self.event_venue and self.event_location:
            start = self.start_date.replace("-", "")
            end = self.end_date.replace("-", "")
            venue_code = self.event_venue[:3].upper()
            location_code = self.event_location[:3].upper()
            self.event_identifier = f"{start}-{end}-{location_code}-{venue_code}"

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
        self.send_invitations_to_all_delegates()

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
        """Bulk send using the exact structure of your UI template"""
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
        """Shared logic for sending an email to a single delegate"""
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

        if template_info["type"] == "ui":
            email_template = frappe.get_doc("Email Template", template_info["name"])
            subject = frappe.render_template(email_template.subject, template_args)
            message = frappe.render_template(email_template.response, template_args)
            frappe.sendmail(recipients=[delegate.email], subject=subject, message=message)
        else:
            frappe.sendmail(
                recipients=[delegate.email],
                subject=f"{self.event_name} Registration Confirmation",
                template=template_info["path"],
                args=template_args
            )
            
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
    # ------------------------------------------------------------------
    # 1. Validate inputs early (fail fast)
    # ------------------------------------------------------------------
    if not event_name or not delegate_email:
        frappe.throw("Missing event or delegate email")

    validate_email_address(delegate_email, throw=True)

    # ------------------------------------------------------------------
    # 2. Load event (server-side, trusted context)
    # ------------------------------------------------------------------
    event = frappe.get_doc("Event Registration", event_name)

    # ------------------------------------------------------------------
    # 3. Locate delegate
    # ------------------------------------------------------------------
    delegate = next((d for d in event.delegates if d.email == delegate_email), None)

    if not delegate:
        frappe.throw("Delegate not found for this event")

    if delegate.confirmed:
        frappe.msgprint(
            f"{delegate.first_name} {delegate.last_name} has already confirmed attendance."
        )
        return

    # ------------------------------------------------------------------
    # 4. Build secure confirmation link (guest-safe)
    # ------------------------------------------------------------------
    confirmation_link = (
        get_url()
        + "/api/method/event_management.event_management.doctype.event_registration."
        "event_registration.confirm_delegate" + f"?token={delegate.confirmation_token}"
    )

    # ------------------------------------------------------------------
    # 5. Prepare template variables (shared by subject + body)
    # ------------------------------------------------------------------
    template_args = {
        # Subject variables
        "division": event.division or "Training",
        "event_date": formatdate(event.start_date, "dd MMM yyyy"),
        "location": f"{event.event_venue}, {event.event_location}",
        # Body variables
        "delegate": {"full_name": f"{delegate.first_name} {delegate.last_name}"},
        "event": event,
        "confirmation_link": confirmation_link,
        "client_list": [f"{d.first_name} {d.last_name}" for d in event.delegates],
        "company_name": frappe.defaults.get_global_default("company"),
    }

    # ------------------------------------------------------------------
    # 6. Resolve template (UI override OR app default)
    # ------------------------------------------------------------------
    template_info = _get_attendance_email_template()

    # ------------------------------------------------------------------
    # 7. Send email (queue-based, production safe)
    # ------------------------------------------------------------------
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
    Sends a detailed report of all active events and delegate statuses.
    If no recipient is provided, it defaults to the Admin Email in settings.
    """
    events = frappe.get_all(
        "Event Registration",
        filters={"docstatus": 1},
        fields=["name", "event_name", "organization_name", "start_date", "end_date", "all_confirmed"]
    )

    if not events:
        frappe.msgprint("No active events found for reporting.")
        return

    # Generate the professional HTML body
    html_report = _generate_event_report_html(events)

    # Determine recipient
    if not recipient:
        recipient = frappe.db.get_single_value("Event Management Setting", "admin_email") or "info@tagrit.com"

    try:
        frappe.sendmail(
            recipients=[recipient],
            subject=f"Event Confirmation Status Report - {formatdate(nowdate())}",
            message=html_report,
            now=True
        )
        frappe.msgprint(f"✅ Report successfully sent to {recipient}!")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Event Report Failed")
        frappe.msgprint("Failed to send report. Check Error Logs.")
        
        

def _generate_event_report_html(events):
    """Helper to build the HTML table structure for reports"""
    html = f"""<div style="font-family: Arial, sans-serif; color: #333;">
                <h2>Event Confirmation Status Report</h2>
                <p>Generated on: {formatdate(nowdate())}</p><hr>"""

    for event_summary in events:
        event = frappe.get_doc("Event Registration", event_summary.name)
        total = len(event.delegates)
        confirmed = sum(1 for d in event.delegates if d.confirmed)
        percentage = round((confirmed / total * 100) if total > 0 else 0, 1)
        status_color = "#20639B" if event.all_confirmed else "#ff9800"

        html += f"""
        <div style="margin: 20px 0; border: 1px solid #eee; padding: 15px; border-radius: 8px;">
            <h3 style="color: {status_color};">{event.event_name} ({percentage}%)</h3>
            <p><strong>Organization:</strong> {event.organization_name} | <strong>Date:</strong> {formatdate(event.start_date)}</p>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <tr style="background: #f8f9fa; border-bottom: 2px solid #eee;">
                    <th style="padding: 8px; text-align: left;">Delegate</th>
                    <th style="padding: 8px; text-align: left;">Email</th>
                    <th style="padding: 8px; text-align: center;">Status</th>
                </tr>"""

        for d in event.delegates:
            status = "✅ Confirmed" if d.confirmed else "⏳ Pending"
            row_bg = "#f0fff4" if d.confirmed else "#fffaf0"
            html += f"""<tr style="background: {row_bg}; border-bottom: 1px solid #eee;">
                        <td style="padding: 8px;">{d.first_name} {d.last_name}</td>
                        <td style="padding: 8px;">{d.email}</td>
                        <td style="padding: 8px; text-align: center;">{status}</td>
                    </tr>"""
        html += "</table></div>"
    
    html += "</div>"
    return html

@frappe.whitelist()
def send_welcome_email_to_confirmed(event_name):
    """Send welcome email only to confirmed delegates using the Event Welcome template"""
    if not event_name:
        frappe.throw("Missing event name")

    event = frappe.get_doc("Event Registration", event_name)

    # Get only confirmed delegates
    confirmed_delegates = [d for d in event.delegates if d.confirmed]

    if not confirmed_delegates:
        frappe.msgprint("No confirmed delegates yet!")
        return

    # Resolve template using the new 'Event Welcome' name
    template_info = _get_event_welcome_template()
    success_count = 0

    for delegate in confirmed_delegates:
        try:
            # Prepare template variables exactly as defined in your patch
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
                    now=True # Set to True for immediate sending
                )
            else:
                frappe.sendmail(
                    recipients=[delegate.email],
                    subject=f"Welcome to {event.event_name}",
                    template=template_info["path"],
                    args=template_args,
                )
            success_count += 1

        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Welcome Email Failed for {delegate.email}")

    if success_count > 0:
        event.db_set("welcome_email_sent", 1)
        frappe.msgprint(f"✅ Welcome email sent to {success_count} confirmed delegates!")

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
