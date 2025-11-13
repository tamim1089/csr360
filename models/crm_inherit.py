# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    csr_pledge_ids = fields.Many2many(
        'csr.pledge',
        'crm_lead_csr_pledge_rel',
        'lead_id',
        'pledge_id',
        string="CSR Pledges",
        help="Link CSR pledges to this opportunity/lead"
    )

