frappe.ui.form.on('Event Trainer', {
    refresh: function(frm) {
        // Make email and mobile_no fields editable
        frm.set_df_property('email', 'read_only', 0);
        frm.set_df_property('mobile_no', 'read_only', 0);
    },
    
    trainer: function(frm) {
        // When trainer is selected, fetch email and mobile if not already filled
        if (frm.doc.trainer) {
            frappe.db.get_value('Supplier', frm.doc.trainer, ['email_id', 'supplier_email', 'mobile_no'], (r) => {
                if (r) {
                    // Only auto-fill if fields are empty
                    if (!frm.doc.email) {
                        frm.set_value('email', r.email_id || r.supplier_email || '');
                    }
                    if (!frm.doc.mobile_no) {
                        frm.set_value('mobile_no', r.mobile_no || '');
                    }
                }
            });
        }
    },
    
    validate: function(frm) {
        // Ensure email and mobile are filled before saving
        if (!frm.doc.email) {
            frappe.msgprint(__('Email is mandatory. Please enter the trainer\'s email address.'));
            frappe.validated = false;
        }
        if (!frm.doc.mobile_no) {
            frappe.msgprint(__('Mobile number is mandatory. Please enter the trainer\'s mobile number.'));
            frappe.validated = false;
        }
    }
});