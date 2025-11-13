# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    csr_pledge_ids = fields.One2many(
        'csr.pledge',
        'owner_id',
        string="CSR Pledges"
    )
    csr_pledge_count = fields.Integer(
        string="CSR Pledges",
        compute="_compute_csr_pledge_count"
    )
    
    @api.depends('csr_pledge_ids')
    def _compute_csr_pledge_count(self):
        for rec in self:
            rec.csr_pledge_count = len(rec.csr_pledge_ids)
    
    def action_view_csr_pledges(self):
        """Smart button to view employee's CSR pledges"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('CSR Pledges'),
            'res_model': 'csr.pledge',
            'view_mode': 'list,form',
            'domain': [('owner_id', '=', self.id)],
        }

