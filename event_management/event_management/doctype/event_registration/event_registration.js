frappe.ui.form.on('Event Registration', {
    // When location field changes
    location: function(frm) {
        frm.set_value('venue', '');
        
        if (frm.doc.location) {
            frm.set_query('venue', function() {
                return {
                    filters: {
                        'location': frm.doc.location
                    }
                };
            });
        }
    },
    
    number_of_delegates: function(frm) {
        calculate_revenue(frm);
    },
    
    charges_per_delegate: function(frm) {
        calculate_revenue(frm);
    },
    
    refresh: function(frm) {
        // Load confirmation summary
        if (frm.doc.docstatus === 1) {
            load_confirmation_summary(frm);
        }
        
        // Button to send welcome email to confirmed delegates only
       if ((frm.doc.docstatus === 1 || frm.doc.amended_from) && !frm.doc.welcome_email_sent) {
            frm.add_custom_button(__('Send Welcome Email to Confirmed'), function() {
                
                // 1. Disable the button immediately to prevent double-click
                frm.set_df_property('send_welcome_email_btn'); 
                
                frappe.confirm(__('Are you sure you want to send welcome emails?'), () => {
                    frappe.call({
                        method: 'event_management.event_management.doctype.event_registration.event_registration.send_welcome_email_to_confirmed',
                        args: {
                            event_name: frm.doc.name
                        },
                        btn: $('.primary-action'), // Shows a spinner on the main button
                        callback: function(r) {
                            frm.reload_doc();
                        },
                        error: function() {
                            // Re-enable on error so they can try again
                            frm.set_df_property('send_welcome_email_btn', 'disabled', 0);
                        }
                    });
                });
            });
        }
        
        // Button to send confirmation list
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Send Confirmation Report'), function() {
                frappe.call({
                    method: 'event_management.event_management.doctype.event_registration.event_registration.send_confirmation_list_email',
                    callback: function(r) {
                        frappe.msgprint(__('Report sent!'));
                    }
                });
            }, __('Actions'));
        }
    }
});

// Helper function to calculate revenue
function calculate_revenue(frm) {
    if (frm.doc.number_of_delegates && frm.doc.charges_per_delegate) {
        let revenue = frm.doc.number_of_delegates * frm.doc.charges_per_delegate;
        frm.set_value('revenue', revenue);
    }
}

// Load and display confirmation summary
function load_confirmation_summary(frm) {
    frappe.call({
        method: 'event_management.event_management.doctype.event_registration.event_registration.get_confirmation_summary',
        args: {
            event_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                display_confirmation_summary(frm, r.message);
            }
        }
    });
}

// Display confirmation summary in HTML field
function display_confirmation_summary(frm, data) {
    let html = `
        <div style="padding: 15px; background-color: #f8f9fa; border-radius: 5px; margin-top: 10px;">
            <h4 style="margin-top: 0;">Confirmation Status</h4>
            
            <div style="display: flex; gap: 20px; margin: 15px 0;">
                <div style="flex: 1; text-align: center; padding: 15px; background-color: #4CAF50; color: white; border-radius: 5px;">
                    <div style="font-size: 24px; font-weight: bold;">${data.confirmed}</div>
                    <div>Confirmed</div>
                </div>
                <div style="flex: 1; text-align: center; padding: 15px; background-color: #ff9800; color: white; border-radius: 5px;">
                    <div style="font-size: 24px; font-weight: bold;">${data.pending}</div>
                    <div>Pending</div>
                </div>
                <div style="flex: 1; text-align: center; padding: 15px; background-color: #2196F3; color: white; border-radius: 5px;">
                    <div style="font-size: 24px; font-weight: bold;">${data.percentage}%</div>
                    <div>Completion</div>
                </div>
            </div>
            
            <table style="width: 100%; margin-top: 15px; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #e9ecef;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Delegate</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Status</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Confirmed On</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Action</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.delegates.forEach(function(delegate) {
        let status_color = delegate.confirmed ? '#d4edda' : '#fff3cd';
        let status_icon = delegate.confirmed ? '✓' : '✗';
        let status_text = delegate.confirmed ? 'Confirmed' : 'Pending';
        let conf_date = delegate.confirmation_date || 'N/A';
        let resend_btn = !delegate.confirmed ? 
            `<button class="btn btn-xs btn-default" onclick="resend_invitation('${frm.doc.name}', '${delegate.email}')">Resend</button>` : 
            '-';
        
        html += `
            <tr style="background-color: ${status_color};">
                <td style="padding: 8px; border: 1px solid #ddd;">${delegate.name}</td>
                <td style="padding: 8px; text-align: center; border: 1px solid #ddd;">${status_icon} ${status_text}</td>
                <td style="padding: 8px; text-align: center; border: 1px solid #ddd;">${conf_date}</td>
                <td style="padding: 8px; text-align: center; border: 1px solid #ddd;">${resend_btn}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    frm.get_field('confirmation_summary').$wrapper.html(html);
}

// Global function to resend invitation
window.resend_invitation = function(event_name, email) {
    frappe.call({
        method: 'event_management.event_management.doctype.event_registration.event_registration.resend_invitation',
        args: {
            event_name: event_name,
            delegate_email: email
        },
        callback: function(r) {
            frappe.show_alert({
                message: 'Invitation resent!',
                indicator: 'green'
            });
        }
    });
};