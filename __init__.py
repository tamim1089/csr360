from . import models

def post_init_hook(cr, registry):
    """Recalculate computed fields after demo data is loaded"""
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Recompute all pledge progress fields
    pledges = env['csr.pledge'].search([])
    pledges._compute_progress()
    cr.commit()
