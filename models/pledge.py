# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class CSRDepartment(models.Model):
    _name = "csr.department"
    _description = "CSR Department"
    _order = "name asc"

    name = fields.Char(required=True)
    pledge_ids = fields.One2many('csr.pledge', 'department_id', string="Pledges")

class CSRPledge(models.Model):
    _name = "csr.pledge"
    _description = "CSR Pledge"
    _order = "create_date desc"
    _rec_name = "title"

    title = fields.Char(required=True, string="Pledge Title")
    owner_id = fields.Many2one('hr.employee', string="Owner", required=True)
    department_id = fields.Many2one('csr.department', string="Department", required=True)
    target_value = fields.Float(string="Target Value", required=True)
    unit = fields.Char(string="Unit", required=True, help="e.g., %, kWh, hours, trees")
    current_value = fields.Float(string="Current Value", compute="_compute_progress", store=True)
    progress_percent = fields.Float(string="Progress %", compute="_compute_progress", store=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('at_risk', 'At Risk')
    ], string="Status", default='draft', required=True)
    notes = fields.Text(string="Notes")
    sdg_tags = fields.Char(string="SDG Tags", help="e.g., SDG7, SDG13")
    progress_ids = fields.One2many('csr.progress', 'pledge_id', string="Progress Updates")
    progress_count = fields.Integer(string="Progress Count", compute="_compute_progress_count")
    
    # Project Integration
    project_id = fields.Many2one(
        'project.project',
        string="Linked Project",
        ondelete='set null',
        help="Link this pledge to a project for detailed task management"
    )
    project_task_ids = fields.One2many(
        'project.task',
        'csr_pledge_id',
        string="Project Tasks"
    )
    project_task_count = fields.Integer(
        string="Task Count",
        compute="_compute_project_task_count"
    )
    
    @api.depends('progress_ids', 'progress_ids.current_value', 'progress_ids.date', 'target_value')
    def _compute_progress(self):
        for rec in self:
            if rec.progress_ids:
                # Get the latest progress entry
                latest = max(rec.progress_ids, key=lambda x: x.date)
                rec.current_value = latest.current_value
            else:
                rec.current_value = 0.0
            
            if rec.target_value > 0:
                rec.progress_percent = (rec.current_value / rec.target_value) * 100
            else:
                rec.progress_percent = 0.0
            
            # Auto-update status based on progress
            if rec.progress_percent >= 100:
                rec.status = 'completed'
            elif rec.progress_percent >= 70:
                if rec.status == 'draft':
                    rec.status = 'in_progress'
                elif rec.status != 'completed':
                    rec.status = 'in_progress'
            elif rec.progress_percent < 40 and rec.status != 'draft':
                rec.status = 'at_risk'
            elif rec.status == 'draft' and rec.current_value > 0:
                rec.status = 'in_progress'
    
    def _compute_progress_count(self):
        for rec in self:
            rec.progress_count = len(rec.progress_ids)
    
    @api.depends('project_task_ids')
    def _compute_project_task_count(self):
        for rec in self:
            rec.project_task_count = len(rec.project_task_ids)
    
    def action_log_progress(self):
        """Smart button action to log progress"""
        return {
            'name': _('Log Progress'),
            'type': 'ir.actions.act_window',
            'res_model': 'csr.progress',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_pledge_id': self.id}
        }
    
    def action_analyze_impact(self):
        """Smart button action to analyze impact"""
        return {
            'name': _('Analyze Impact'),
            'type': 'ir.actions.act_window',
            'res_model': 'csr.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_pledge_ids': [(6, 0, [self.id])]}
        }
    
    def action_view_project(self):
        """Smart button to view linked project"""
        self.ensure_one()
        if self.project_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Project'),
                'res_model': 'project.project',
                'res_id': self.project_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Create Project'),
                'res_model': 'project.project',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_name': self.title,
                    'default_csr_pledge_id': self.id,
                }
            }
    
    def action_view_project_tasks(self):
        """Smart button to view project tasks"""
        self.ensure_one()
        context = {'default_csr_pledge_id': self.id}
        
        # If pledge has a project, set it in context to avoid stage issues
        if self.project_id:
            context['default_project_id'] = self.project_id.id
            context['default_stage_id'] = False  # Let Odoo assign default project stage
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Project Tasks'),
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [('csr_pledge_id', '=', self.id)],
            'context': context
        }

