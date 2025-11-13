# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ProjectTask(models.Model):
    _inherit = 'project.task'
    
    csr_pledge_id = fields.Many2one(
        'csr.pledge',
        string="CSR Pledge",
        ondelete='set null',
        help="Link this task to a CSR pledge"
    )
    
    @api.model
    def default_get(self, fields_list):
        """Override to ensure project_id is set when creating task from CSR pledge"""
        res = super(ProjectTask, self).default_get(fields_list)
        
        # If csr_pledge_id is in context, get the project_id from the pledge
        if 'default_csr_pledge_id' in self.env.context:
            pledge_id = self.env.context.get('default_csr_pledge_id')
            if pledge_id:
                pledge = self.env['csr.pledge'].browse(pledge_id)
                if pledge.exists() and pledge.project_id:
                    res['project_id'] = pledge.project_id.id
                    # Ensure we're using project stages, not personal stages
                    if 'stage_id' in res:
                        # Clear personal stage if task is not private
                        if not res.get('is_private', False):
                            stage = self.env['project.task.type'].browse(res.get('stage_id'))
                            if stage.exists() and stage.user_id:
                                # Remove personal stage for non-private tasks
                                del res['stage_id']
        
        return res
    
    @api.model
    def create(self, vals):
        """Override create to handle CSR pledge linking properly"""
        # If csr_pledge_id is set but project_id is not, get it from the pledge
        if vals.get('csr_pledge_id') and not vals.get('project_id'):
            pledge = self.env['csr.pledge'].browse(vals['csr_pledge_id'])
            if pledge.exists() and pledge.project_id:
                vals['project_id'] = pledge.project_id.id
        
        # Ensure personal stages are only used for private tasks
        if vals.get('stage_id') and not vals.get('is_private', False):
            stage = self.env['project.task.type'].browse(vals['stage_id'])
            if stage.exists() and stage.user_id:
                # Remove personal stage for non-private tasks
                # Let Odoo assign the default project stage instead
                del vals['stage_id']
        
        return super(ProjectTask, self).create(vals)

