# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class CSRKPI(models.Model):
    _name = "csr.kpi"
    _description = "CSR KPI"
    _order = "name asc"

    name = fields.Char(string="KPI Name", required=True)
    formula = fields.Char(string="Formula", help="Description of how this KPI is calculated")
    unit = fields.Char(string="Unit")
    value = fields.Float(string="Current Value", compute="_compute_value", store=False)
    pledge_ids = fields.Many2many('csr.pledge', string="Related Pledges")
    
    @api.depends('pledge_ids', 'name')
    def _compute_value(self):
        for rec in self:
            if rec.name == "Total Pledges":
                rec.value = self.env['csr.pledge'].search_count([('status', '!=', 'draft')])
            elif rec.name == "Completed %":
                total = self.env['csr.pledge'].search_count([('status', '!=', 'draft')])
                completed = self.env['csr.pledge'].search_count([('status', '=', 'completed')])
                rec.value = (completed / total * 100) if total > 0 else 0
            elif rec.name == "Energy Saved (kWh)":
                energy_pledges = self.env['csr.pledge'].search([
                    ('unit', 'ilike', 'kwh')
                ])
                rec.value = sum(pledge.current_value for pledge in energy_pledges)
            elif rec.name == "Volunteer Hours":
                volunteer_pledges = self.env['csr.pledge'].search([
                    ('unit', 'ilike', 'hour')
                ])
                rec.value = sum(pledge.current_value for pledge in volunteer_pledges)
            else:
                rec.value = 0.0

