# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class CSRProgress(models.Model):
    _name = "csr.progress"
    _description = "CSR Progress Update"
    _order = "date desc"

    name = fields.Char(string="Title", compute="_compute_name", store=True)
    pledge_id = fields.Many2one('csr.pledge', string="Pledge", required=True, ondelete='cascade')
    date = fields.Date(string="Date", required=True, default=fields.Date.today)
    current_value = fields.Float(string="Current Value", required=True)
    notes = fields.Text(string="Notes")
    
    @api.depends('pledge_id', 'date', 'current_value')
    def _compute_name(self):
        for rec in self:
            if rec.pledge_id and rec.date:
                rec.name = f"{rec.pledge_id.title} - {rec.date} ({rec.current_value} {rec.pledge_id.unit})"
            else:
                rec.name = "Progress Update"
    
    @api.model
    def create(self, vals):
        res = super(CSRProgress, self).create(vals)
        # Trigger recompute of pledge progress
        if res.pledge_id:
            res.pledge_id._compute_progress()
            res.pledge_id.invalidate_recordset(['current_value', 'progress_percent'])
        return res
    
    def write(self, vals):
        res = super(CSRProgress, self).write(vals)
        # Trigger recompute of pledge progress
        for rec in self:
            if rec.pledge_id:
                rec.pledge_id._compute_progress()
                rec.pledge_id.invalidate_recordset(['current_value', 'progress_percent'])
        return res
    
    def unlink(self):
        pledge_ids = self.mapped('pledge_id')
        res = super(CSRProgress, self).unlink()
        # Trigger recompute of pledge progress after deletion
        for pledge in pledge_ids:
            pledge._compute_progress()
            pledge.invalidate_recordset(['current_value', 'progress_percent'])
        return res

