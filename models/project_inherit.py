# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    csr_pledge_id = fields.Many2one(
        'csr.pledge',
        string="CSR Pledge",
        ondelete='set null',
        help="Link this project to a CSR initiative pledge"
    )
    csr_pledge_count = fields.Integer(
        string="CSR Pledges",
        compute="_compute_csr_pledge_count"
    )
    
    @api.depends('csr_pledge_id')
    def _compute_csr_pledge_count(self):
        for rec in self:
            rec.csr_pledge_count = 1 if rec.csr_pledge_id else 0
    
    def action_view_csr_pledge(self):
        """Smart button to view linked CSR pledge"""
        self.ensure_one()
        if self.csr_pledge_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('CSR Pledge'),
                'res_model': 'csr.pledge',
                'res_id': self.csr_pledge_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

