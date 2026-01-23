frappe.ui.form.on('Event Registration', {
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
        if (frm.doc.docstatus === 1) {
            load_confirmation_summary(frm);
        }
        
        if ((frm.doc.docstatus === 1 || frm.doc.amended_from) && !frm.doc.welcome_email_sent) {
            frm.add_custom_button(__('Send Welcome Email to Confirmed'), function() {
                frm.set_df_property('send_welcome_email_btn'); 
                
                frappe.confirm(__('Are you sure you want to send welcome emails?'), () => {
                    frappe.call({
                        method: 'event_management.event_management.doctype.event_registration.event_registration.send_welcome_email_to_confirmed',
                        args: {
                            event_name: frm.doc.name
                        },
                        btn: $('.primary-action'),
                        callback: function(r) {
                            frm.reload_doc();
                        },
                        error: function() {
                            frm.set_df_property('send_welcome_email_btn', 'disabled', 0);
                        }
                    });
                });
            });
        }
        
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
        
        if (frm.doc.all_confirmed && frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Add Trainers'), function() {
                frappe.route_options = {
                    "event_registration": frm.doc.name
                };
                frappe.set_route("List", "Event Trainer");
            }, __("Training Management"));
            
            frm.add_custom_button(__('View Trainers'), function() {
                show_trainers_dialog(frm);
            }, __("Training Management"));
        }
        
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Trainer Summary'), function() {
                show_trainer_payment_summary(frm);
            }, __("Training Management"));
        }
    }
});

function calculate_revenue(frm) {
    if (frm.doc.number_of_delegates && frm.doc.charges_per_delegate) {
        let revenue = frm.doc.number_of_delegates * frm.doc.charges_per_delegate;
        frm.set_value('revenue', revenue);
    }
}

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

function show_trainers_dialog(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Event Trainer',
            filters: { event_registration: frm.doc.name },
            fields: ['name', 'trainer_name', 'email', 'mobile_no', 'rate_type', 'total_amount', 
                     'payment_status', 'contract_sent']
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                show_trainers_table(frm, r.message);
            } else {
                frappe.msgprint(__('No trainers assigned yet. Click "Add Trainers" to assign.'));
            }
        }
    });
}

function show_trainers_table(frm, trainers) {
    let html = `
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Trainer Name</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>Rate Type</th>
                    <th>Amount</th>
                    <th>Contract</th>
                    <th>Payment</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    trainers.forEach(trainer => {
        const contract_badge = trainer.contract_sent 
            ? '<span class="badge badge-success">Sent</span>' 
            : '<span class="badge badge-warning">Pending</span>';
        
        const payment_color = {
            'Paid': 'success',
            'Partially Paid': 'warning',
            'Unpaid': 'danger'
        }[trainer.payment_status] || 'secondary';
        
        const payment_badge = `<span class="badge badge-${payment_color}">${trainer.payment_status}</span>`;
        
        html += `
            <tr>
                <td><a href="/app/event-trainer/${trainer.name}">${trainer.trainer_name}</a></td>
                <td>${trainer.email || '-'}</td>
                <td>${trainer.mobile_no || '-'}</td>
                <td>${trainer.rate_type}</td>
                <td>${format_currency(trainer.total_amount)}</td>
                <td>${contract_badge}</td>
                <td>${payment_badge}</td>
                <td>
                    <button class="btn btn-xs btn-primary" 
                            onclick="send_contract('${trainer.name}')">
                        Contract
                    </button>
                    <button class="btn btn-xs btn-warning" 
                            onclick="create_invoice('${trainer.name}')">
                        Invoice
                    </button>
                    <button class="btn btn-xs btn-success" 
                            onclick="make_payment('${trainer.name}')">
                        Pay
                    </button>
                    <button class="btn btn-xs btn-info" 
                            onclick="view_payments('${trainer.name}')">
                        History
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    
    const dialog = new frappe.ui.Dialog({
        title: __('Event Trainers'),
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'trainers_html',
                options: html
            }
        ],
        primary_action_label: __('Add New Trainer'),
        primary_action: function() {
            dialog.hide();
            frappe.new_doc('Event Trainer', {
                event_registration: frm.doc.name
            });
        }
    });
    
    dialog.show();
}

window.send_contract = function(event_trainer_name) {
    frappe.confirm(__('Send contract to this trainer?'), function() {
        frappe.call({
            method: 'event_management.event_management.doctype.event_trainer.event_trainer.send_trainer_contract',
            args: { event_trainer_name: event_trainer_name },
            callback: function(r) {
                if (!r.exc) {
                    frappe.show_alert({
                        message: __('Contract sent successfully'),
                        indicator: 'green'
                    });
                }
            }
        });
    });
}

// UPDATED: Invoice creation with proper linking
window.create_invoice = function(event_trainer_name) {
    frappe.call({
        method: 'event_management.event_management.doctype.event_trainer.event_trainer.make_purchase_invoice',
        args: { source_name: event_trainer_name },
        freeze: true,
        freeze_message: __('Creating Purchase Invoice...'),
        callback: function(r) {
            if (r.message) {
                frappe.model.sync(r.message);
                frappe.set_route('Form', r.message.doctype, r.message.name);
            }
        },
        error: function() {
            frappe.msgprint(__('Failed to create invoice'));
        }
    });
}

// UPDATED: Payment creation with invoice linking
window.make_payment = function(event_trainer_name) {
    frappe.call({
        method: 'event_management.event_management.doctype.event_trainer.event_trainer.get_trainer_payment_summary',
        args: { event_trainer_name: event_trainer_name },
        callback: function(r) {
            if (r.message) {
                show_make_payment_dialog(event_trainer_name, r.message);
            }
        }
    });
}

// UPDATED: Payment dialog with invoice linking
function show_make_payment_dialog(event_trainer_name, data) {
    const balance = data.balance;
    
    // Build invoice options
    let invoice_options = '';
    if (data.invoices && data.invoices.length > 0) {
        data.invoices.forEach(inv => {
            if (inv.outstanding_amount > 0) {
                invoice_options += `<option value="${inv.name}">${inv.name} (Outstanding: ${format_currency(inv.outstanding_amount)})</option>`;
            }
        });
    }
    
    const d = new frappe.ui.Dialog({
        title: __('Record Payment - {0}', [data.trainer_name]),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'payment_info',
                options: `
                    <div style="background-color: #f8f9fa; padding: 15px; margin-bottom: 15px; border-radius: 5px;">
                        <p><strong>Event:</strong> ${data.event_name}</p>
                        <p><strong>Total Amount:</strong> ${format_currency(data.total_amount)}</p>
                        <p><strong>Total Invoiced:</strong> ${format_currency(data.total_invoiced)}</p>
                        <p><strong>Paid:</strong> <span class="text-success">${format_currency(data.total_paid)}</span></p>
                        <p><strong>Outstanding:</strong> <span class="text-warning">${format_currency(data.total_outstanding)}</span></p>
                        <p><strong>Balance:</strong> <span class="text-danger">${format_currency(balance)}</span></p>
                    </div>
                `
            },
            {
               label: 'Link to Invoice',
               fieldname: 'link_invoice',
               fieldtype: 'Select',
               options: [''].concat(
               data.invoices
              .filter(inv => inv.outstanding_amount > 0)
              .map(inv => ({
                label: `${inv.name} (Outstanding: ${format_currency(inv.outstanding_amount)})`,
                value: inv.name
             }))
          )
        },
            {
                label: 'Payment Amount',
                fieldname: 'amount',
                fieldtype: 'Currency',
                reqd: 1,
                default: data.total_outstanding > 0 ? data.total_outstanding : (balance > 0 ? balance : 0)
            },
            {
                label: 'Reference No',
                fieldname: 'reference_no',
                fieldtype: 'Data',
                description: 'Payment reference number (optional)'
            },
            {
                label: 'Remarks',
                fieldname: 'remarks',
                fieldtype: 'Small Text',
                default: `Payment for training - ${data.event_name}`
            }
        ],
        primary_action_label: __('Create Payment Entry'),
        primary_action: function(values) {
            if (values.amount <= 0) {
                frappe.msgprint(__('Payment amount must be greater than zero'));
                return;
            }
            
            frappe.call({
                method: 'event_management.event_management.doctype.event_trainer.event_trainer.create_trainer_payment_entry',
                args: {
                    event_trainer_name: event_trainer_name,
                    amount: values.amount,
                    reference_no: values.reference_no || event_trainer_name,
                    remarks: values.remarks,
                    link_to_invoice: values.link_invoice || null
                },
                freeze: true,
                freeze_message: __('Creating Payment Entry...'),
                callback: function(r) {
                    if (r.message) {
                        d.hide();
                        frappe.show_alert({
                            message: __('Payment Entry {0} created successfully', [`<a href="/app/payment-entry/${r.message}">${r.message}</a>`]),
                            indicator: 'green'
                        }, 5);
                        
                        frappe.confirm(
                            __('Payment Entry created. Do you want to open it now?'),
                            function() {
                                frappe.set_route('Form', 'Payment Entry', r.message);
                            }
                        );
                    }
                }
            });
        }
    });
    
    // ADDED: Update amount when invoice is selected
    d.fields_dict.link_invoice.$input.on('change', function() {
        const selected_invoice = d.get_value('link_invoice');
        if (selected_invoice) {
            const invoice = data.invoices.find(inv => inv.name === selected_invoice);
            if (invoice && invoice.outstanding_amount > 0) {
                d.set_value('amount', invoice.outstanding_amount);
            }
        }
    });
    
    d.show();
}

// UPDATED: View payments with invoice details
window.view_payments = function(event_trainer_name) {
    frappe.call({
        method: 'event_management.event_management.doctype.event_trainer.event_trainer.get_trainer_payment_summary',
        args: { event_trainer_name: event_trainer_name },
        callback: function(r) {
            if (r.message) {
                show_payment_summary_dialog(r.message);
            }
        }
    });
}

// UPDATED: Payment summary dialog with invoice section
function show_payment_summary_dialog(data) {
    let html = `
        <div class="row">
            <div class="col-sm-6">
                <h5>Trainer: ${data.trainer_name}</h5>
                <p><strong>Event:</strong> ${data.event_name}</p>
            </div>
            <div class="col-sm-6">
                <table class="table table-sm">
                    <tr>
                        <td><strong>Contract Amount:</strong></td>
                        <td>${format_currency(data.total_amount)}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Invoiced:</strong></td>
                        <td>${format_currency(data.total_invoiced)}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Paid:</strong></td>
                        <td class="text-success">${format_currency(data.total_paid)}</td>
                    </tr>
                    <tr>
                        <td><strong>Outstanding:</strong></td>
                        <td class="text-warning">${format_currency(data.total_outstanding)}</td>
                    </tr>
                    <tr>
                        <td><strong>Balance:</strong></td>
                        <td class="text-danger">${format_currency(data.balance)}</td>
                    </tr>
                </table>
            </div>
        </div>
        <hr>
    `;
    
    // ADDED: Invoices section
    if (data.invoices && data.invoices.length > 0) {
        html += `<h6>Invoices</h6><table class="table table-bordered table-sm">
            <thead><tr><th>Date</th><th>Invoice</th><th>Total</th><th>Outstanding</th><th>Status</th><th>Action</th></tr></thead><tbody>`;
        
        data.invoices.forEach(invoice => {
            const status_color = invoice.status === 'Paid' ? 'success' : (invoice.status === 'Unpaid' ? 'danger' : 'warning');
            html += `<tr>
                <td>${frappe.datetime.str_to_user(invoice.posting_date)}</td>
                <td><a href="/app/purchase-invoice/${invoice.name}" target="_blank">${invoice.name}</a></td>
                <td>${format_currency(invoice.grand_total)}</td>
                <td>${format_currency(invoice.outstanding_amount)}</td>
                <td><span class="badge badge-${status_color}">${invoice.status}</span></td>
                <td>
                    <button class="btn btn-xs btn-default" onclick="frappe.set_route('Form', 'Purchase Invoice', '${invoice.name}')">View</button>
                    ${invoice.outstanding_amount > 0 ? `<button class="btn btn-xs btn-success" onclick="pay_invoice('${invoice.name}')">Pay</button>` : ''}
                </td>
            </tr>`;
        });
        html += '</tbody></table><hr>';
    }
    
    // Payment history section
    if (data.payments && data.payments.length > 0) {
        html += `<h6>Payment History</h6><table class="table table-bordered table-sm">
            <thead><tr><th>Date</th><th>Reference</th><th>Amount</th><th>Remarks</th><th>Action</th></tr></thead><tbody>`;
        
        data.payments.forEach(payment => {
            html += `<tr>
                <td>${frappe.datetime.str_to_user(payment.posting_date)}</td>
                <td><a href="/app/payment-entry/${payment.name}" target="_blank">${payment.reference_no || payment.name}</a></td>
                <td>${format_currency(payment.paid_amount)}</td>
                <td>${payment.remarks || '-'}</td>
                <td><button class="btn btn-xs btn-default" onclick="frappe.set_route('Form', 'Payment Entry', '${payment.name}')">View</button></td>
            </tr>`;
        });
        html += '</tbody></table>';
    } else {
        html += '<p class="text-muted">No payments recorded yet.</p>';
    }
    
    new frappe.ui.Dialog({
        title: __('Payment Summary'),
        size: 'extra-large',
        fields: [{ fieldtype: 'HTML', fieldname: 'summary_html', options: html }]
    }).show();
}

// NEW: Function to pay invoice directly
window.pay_invoice = function(invoice_name) {
    frappe.call({
        method: 'event_management.event_management.doctype.event_trainer.event_trainer.make_payment_entry_from_invoice',
        args: { purchase_invoice_name: invoice_name },
        callback: function(r) {
            if (r.message) {
                frappe.model.sync(r.message);
                frappe.set_route('Form', 'Payment Entry', r.message.name);
            }
        }
    });
}

function show_trainer_payment_summary(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Event Trainer',
            filters: { event_registration: frm.doc.name },
            fields: ['name', 'trainer_name', 'email', 'mobile_no', 'total_amount', 'paid_amount', 'payment_status']
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let total_contract = 0, total_paid = 0;
                let html = `<table class="table table-bordered">
                    <thead><tr>
                        <th>Trainer</th>
                        <th>Email</th>
                        <th>Phone</th>
                        <th>Contract Amount</th>
                        <th>Paid</th>
                        <th>Balance</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr></thead><tbody>`;
                
                r.message.forEach(trainer => {
                    const balance = trainer.total_amount - (trainer.paid_amount || 0);
                    total_contract += trainer.total_amount;
                    total_paid += (trainer.paid_amount || 0);
                    
                    html += `<tr>
                        <td><a href="/app/event-trainer/${trainer.name}">${trainer.trainer_name}</a></td>
                        <td>${trainer.email || '-'}</td>
                        <td>${trainer.mobile_no || '-'}</td>
                        <td>${format_currency(trainer.total_amount)}</td>
                        <td class="text-success">${format_currency(trainer.paid_amount || 0)}</td>
                        <td class="text-danger">${format_currency(balance)}</td>
                        <td><span class="badge">${trainer.payment_status}</span></td>
                        <td>
                            <button class="btn btn-xs btn-success" onclick="make_payment('${trainer.name}')">
                                Pay
                            </button>
                            <button class="btn btn-xs btn-info" onclick="view_payments('${trainer.name}')">
                                View
                            </button>
                        </td>
                    </tr>`;
                });
                
                html += `<tr class="font-weight-bold">
                    <td colspan="3">TOTAL</td>
                    <td>${format_currency(total_contract)}</td>
                    <td class="text-success">${format_currency(total_paid)}</td>
                    <td class="text-danger">${format_currency(total_contract - total_paid)}</td>
                    <td colspan="2"></td>
                </tr></tbody></table>`;
                
                new frappe.ui.Dialog({
                    title: __('Trainer Payment Summary'),
                    fields: [{ fieldtype: 'HTML', fieldname: 'summary', options: html }],
                    size: 'extra-large'
                }).show();
            } else {
                frappe.msgprint(__('No trainers assigned to this event yet.'));
            }
        }
    });
}