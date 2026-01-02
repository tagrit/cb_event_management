frappe.pages['event-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Event Management Dashboard',
        single_column: true
    });
    
    new EventDashboard(page);
};

class EventDashboard {
    constructor(page) {
        this.page = page;
        this.make();
    }
    
    make() {
        this.$container = $('<div class="event-dashboard">').appendTo(this.page.main);
        this.load_data();
    }
    
    load_data() {
        frappe.call({
            method: 'event_management.event_management.doctype.event_registration.event_registration.get_dashboard_data',
            callback: (r) => {
                if (r.message) {
                    this.render_dashboard(r.message);
                }
            }
        });
    }
    
    render_dashboard(data) {
        let html = `
            <div class="dashboard-cards" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px;">
                ${this.render_card('Total Revenue', frappe.format(data.summary.total_revenue, {fieldtype: 'Currency'}), 'text-success', 'fa-money')}
                ${this.render_card('Total Delegates', data.summary.total_delegates, 'text-primary', 'fa-users')}
                ${this.render_card('Confirmation Rate', data.summary.confirmation_rate + '%', 'text-info', 'fa-check-circle')}
                ${this.render_card('Upcoming Events', data.summary.upcoming_events, 'text-warning', 'fa-calendar')}
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;">
                <div class="card">
                    <div class="card-body">
                        <h5>Delegate Status</h5>
                        <div style="padding: 20px;">
                            <div style="margin-bottom: 10px;">
                                <strong>Confirmed:</strong> ${data.summary.confirmed_delegates}
                            </div>
                            <div>
                                <strong>Pending:</strong> ${data.summary.pending_delegates}
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-body">
                        <h5>Event Status</h5>
                        <div style="padding: 20px;">
                            <div style="margin-bottom: 10px;">
                                <strong>Draft:</strong> ${data.summary.draft_events}
                            </div>
                            <div style="margin-bottom: 10px;">
                                <strong>Fully Confirmed:</strong> ${data.summary.confirmed_events}
                            </div>
                            <div>
                                <strong>Pending Confirmations:</strong> ${data.summary.pending_events}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-body">
                    <h5>Top Organizations</h5>
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Organization</th>
                                <th>Events</th>
                                <th>Total Revenue</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.top_organizations.map(org => `
                                <tr>
                                    <td>${org.organization_name}</td>
                                    <td>${org.event_count}</td>
                                    <td>KES ${frappe.format(org.total_revenue, {fieldtype: 'Currency'})}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        
        this.$container.html(html);
    }
    
    render_card(title, value, color_class, icon) {
        return `
            <div class="card">
                <div class="card-body text-center">
                    <i class="fa ${icon} fa-3x ${color_class}" style="margin-bottom: 15px;"></i>
                    <h3 class="${color_class}">${value}</h3>
                    <p class="text-muted">${title}</p>
                </div>
            </div>
        `;
    }
}