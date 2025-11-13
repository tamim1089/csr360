# -*- coding: utf-8 -*-
from odoo import api, fields, models

class CSRDashboard(models.TransientModel):
    _name = "csr.dashboard"
    _description = "CSR Dashboard"

    # -----------------------------
    # KPI Fields for Visual Dashboard
    # -----------------------------
    total_pledges = fields.Integer(string="Total Pledges", compute="_compute_kpis", store=False)
    completed_pledges = fields.Integer(string="Completed Pledges", compute="_compute_kpis")
    in_progress_pledges = fields.Integer(string="In Progress Pledges", compute="_compute_kpis")
    at_risk_pledges = fields.Integer(string="At Risk Pledges", compute="_compute_kpis")
    completion_rate = fields.Float(string="Completion Rate (%)", compute="_compute_kpis")

    energy_saved = fields.Float(string="Energy Saved (kWh)", compute="_compute_kpis")
    volunteer_hours = fields.Float(string="Volunteer Hours", compute="_compute_kpis")
    avg_progress = fields.Float(string="Average Progress (%)", compute="_compute_kpis")

    @api.depends()
    def _compute_kpis(self):
        """Compute key indicators for CSR dashboard"""
        pledge_model = self.env['csr.pledge']
        progress_model = self.env['csr.progress']

        total_pledges = pledge_model.search_count([('status', '!=', 'draft')])
        completed_pledges = pledge_model.search_count([('status', '=', 'completed')])
        in_progress_pledges = pledge_model.search_count([('status', '=', 'in_progress')])
        at_risk_pledges = pledge_model.search_count([('status', '=', 'at_risk')])

        # Calculate energy saved from pledges with kWh unit
        energy_pledges = pledge_model.search([
            ('unit', 'ilike', 'kwh'),
            ('status', '!=', 'draft')
        ])
        energy_saved = sum(pledge.current_value for pledge in energy_pledges)

        # Calculate volunteer hours from pledges with hours unit
        volunteer_pledges = pledge_model.search([
            ('unit', 'ilike', 'hour'),
            ('status', '!=', 'draft')
        ])
        volunteer_hours = sum(pledge.current_value for pledge in volunteer_pledges)

        # Calculate average progress
        all_pledges = pledge_model.search([('status', '!=', 'draft')])
        avg_progress = sum(pledge.progress_percent for pledge in all_pledges) / len(all_pledges) if all_pledges else 0.0

        for record in self:
            record.total_pledges = total_pledges
            record.completed_pledges = completed_pledges
            record.in_progress_pledges = in_progress_pledges
            record.at_risk_pledges = at_risk_pledges
            record.completion_rate = (completed_pledges / total_pledges) * 100 if total_pledges else 0.0
            record.energy_saved = energy_saved
            record.volunteer_hours = volunteer_hours
            record.avg_progress = avg_progress

    # -----------------------------
    # Detailed Stats for Backend / API Use
    # -----------------------------
    @api.model
    def get_dashboard_stats(self):
        """Get aggregated dashboard statistics"""
        Pledge = self.env['csr.pledge']

        total_pledges = Pledge.search_count([('status', '!=', 'draft')])
        completed_pledges = Pledge.search_count([('status', '=', 'completed')])
        in_progress_pledges = Pledge.search_count([('status', '=', 'in_progress')])
        at_risk_pledges = Pledge.search_count([('status', '=', 'at_risk')])

        all_pledges = Pledge.search([('status', '!=', 'draft')])

        # Calculate various metrics
        energy_pledges = all_pledges.filtered(lambda p: 'kwh' in (p.unit or '').lower())
        total_energy_saved = sum(energy_pledges.mapped('current_value'))

        volunteer_pledges = all_pledges.filtered(lambda p: 'hour' in (p.unit or '').lower())
        total_volunteer_hours = sum(volunteer_pledges.mapped('current_value'))

        avg_progress = (
            sum(all_pledges.mapped('progress_percent')) / len(all_pledges)
            if all_pledges else 0
        )

        # Department distribution
        department_stats = {}
        Department = self.env['csr.department']
        for dept in Department.search([]):
            dept_pledges = Pledge.search([
                ('department_id', '=', dept.id),
                ('status', '!=', 'draft')
            ])
            if dept_pledges:
                department_stats[dept.name] = {
                    'count': len(dept_pledges),
                    'avg_progress': sum(dept_pledges.mapped('progress_percent')) / len(dept_pledges),
                }

        return {
            'total_pledges': total_pledges,
            'completed_pledges': completed_pledges,
            'in_progress_pledges': in_progress_pledges,
            'at_risk_pledges': at_risk_pledges,
            'completion_rate': (completed_pledges / total_pledges * 100)
            if total_pledges > 0 else 0,
            'total_energy_saved': total_energy_saved,
            'total_volunteer_hours': total_volunteer_hours,
            'avg_progress': avg_progress,
            'department_stats': department_stats,
        }

    # -----------------------------
    # Departmental Analysis
    # -----------------------------
    @api.model
    def get_contribution_by_department(self):
        """Get contribution breakdown by department"""
        Pledge = self.env['csr.pledge']
        Department = self.env['csr.department']

        result = {}
        for dept in Department.search([]):
            dept_pledges = Pledge.search([
                ('department_id', '=', dept.id),
                ('status', '!=', 'draft')
            ])
            if dept_pledges:
                result[dept.name] = {
                    'count': len(dept_pledges),
                    'avg_progress': sum(dept_pledges.mapped('progress_percent')) / len(dept_pledges),
                    'completed': len(dept_pledges.filtered(lambda p: p.status == 'completed')),
                }
        return result

