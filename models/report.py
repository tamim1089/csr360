# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
import base64
import json
try:
    import urllib.request
    import urllib.parse
    import urllib.error
    URLLIB_AVAILABLE = True
except ImportError:
    URLLIB_AVAILABLE = False

class CSRReport(models.Model):
    _name = "csr.report"
    _description = "CSR Report"
    _order = "generated_on desc"
    _rec_name = "name"

    name = fields.Char(string="Report Name", compute="_compute_name", store=True)
    report_date = fields.Date(string="Report Date", default=fields.Date.today, required=True)
    period = fields.Char(string="Period", required=True, default=lambda self: f"{datetime.now().year}-Q{((datetime.now().month - 1) // 3) + 1}")
    generated_on = fields.Datetime(string="Generated On", default=fields.Datetime.now, required=True)
    
    # Report scope
    pledge_ids = fields.Many2many('csr.pledge', string="Included Pledges")
    include_all = fields.Boolean(string="Include All Pledges", default=True)
    department_ids = fields.Many2many('csr.department', string="Filter by Departments")
    status_filter = fields.Selection(
        [('all', 'All'), ('completed', 'Completed'), ('in_progress', 'In Progress'), ('at_risk', 'At Risk'), ('draft', 'Draft')],
        default='all',
        string="Status Filter"
    )
    
    # Generated report content
    kpi_snapshot = fields.Text(string="KPI Snapshot", compute="_compute_kpi_snapshot")
    summary = fields.Html(string="Executive Summary", readonly=True)
    detailed_analysis = fields.Html(string="Detailed Analysis", readonly=True)
    recommendations = fields.Text(string="Recommendations", readonly=True)
    ai_summary = fields.Text(string="AI Summary", compute="_compute_ai_summary")
    
    # Auto-generated insights
    impact_score = fields.Float(string="Overall Impact Score", compute="_compute_impact_score", store=True)
    on_track_status = fields.Char(string="On Track Status", compute="_compute_on_track_status")
    
    # AI PDF Report fields
    ai_pdf_filename = fields.Char(string="AI PDF Filename", readonly=True)
    ai_pdf_data = fields.Binary(string="AI PDF File", readonly=True)
    ai_pdf_generated = fields.Boolean(string="AI PDF Generated", default=False)
    ai_api_url = fields.Char(string="AI API URL", default="http://127.0.0.1:5000/generate_report", help="URL of the AI report generation service")
    
    # Standard PDF Report fields
    pdf_filename = fields.Char(string="PDF Filename", readonly=True)
    pdf_report = fields.Binary(string="PDF Report", readonly=True, attachment=True)
    pdf_generated = fields.Boolean(string="PDF Generated", default=False)
    
    state = fields.Selection(
        [('draft', 'Draft'), ('generated', 'Generated')],
        default='draft',
        string="State"
    )
    
    @api.depends('period', 'generated_on')
    def _compute_name(self):
        for rec in self:
            rec.name = f"CSR Report - {rec.period}"
    
    @api.depends('pledge_ids', 'include_all', 'status_filter', 'department_ids')
    def _compute_impact_score(self):
        for rec in self:
            pledges = rec._get_filtered_pledges()
            if pledges:
                rec.impact_score = sum(pledges.mapped('progress_percent')) / len(pledges)
            else:
                rec.impact_score = 0.0
    
    @api.depends('impact_score', 'pledge_ids', 'include_all')
    def _compute_on_track_status(self):
        for rec in self:
            pledges = rec._get_filtered_pledges()
            if not pledges:
                rec.on_track_status = "No pledges to analyze"
                continue
            
            completed = len(pledges.filtered(lambda p: p.status == 'completed'))
            completion_rate = (completed / len(pledges) * 100) if pledges else 0
            avg_progress = rec.impact_score
            
            if completion_rate >= 70 and avg_progress >= 70:
                rec.on_track_status = "✅ Your CSR goals are on track! Excellent progress."
            elif completion_rate >= 50 and avg_progress >= 50:
                rec.on_track_status = "⚠️ Your CSR goals are progressing well, but some initiatives need attention."
            elif completion_rate < 40 or avg_progress < 40:
                rec.on_track_status = "❌ Some goals need more attention."
            else:
                rec.on_track_status = "📊 Monitoring in progress..."
    
    def _get_filtered_pledges(self):
        """Get filtered pledges based on report criteria"""
        self.ensure_one()
        domain = []
        
        if not self.include_all:
            if self.pledge_ids:
                domain.append(('id', 'in', self.pledge_ids.ids))
            else:
                return self.env['csr.pledge']
        else:
            domain.append(('status', '!=', 'draft'))
        
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        
        if self.status_filter != 'all':
            if self.status_filter == 'draft':
                domain.append(('status', '=', 'draft'))
            else:
                domain.append(('status', '=', self.status_filter))
        
        return self.env['csr.pledge'].search(domain)
    
    @api.depends('pledge_ids', 'include_all', 'status_filter', 'department_ids', 'period')
    def _compute_kpi_snapshot(self):
        for rec in self:
            pledges = rec._get_filtered_pledges()
            total = len(pledges)
            completed = len(pledges.filtered(lambda p: p.status == 'completed'))
            in_progress = len(pledges.filtered(lambda p: p.status == 'in_progress'))
            at_risk = len(pledges.filtered(lambda p: p.status == 'at_risk'))
            
            rec.kpi_snapshot = f"""Total Pledges: {total}
Completed: {completed}
In Progress: {in_progress}
At Risk: {at_risk}
Average Progress: {sum(p.progress_percent for p in pledges) / total if total > 0 else 0:.1f}%"""
    
    @api.depends('pledge_ids', 'include_all', 'status_filter', 'department_ids', 'period', 'kpi_snapshot')
    def _compute_ai_summary(self):
        for rec in self:
            pledges = rec._get_filtered_pledges()
            total = len(pledges)
            completed = len(pledges.filtered(lambda p: p.status == 'completed'))
            in_progress = len(pledges.filtered(lambda p: p.status == 'in_progress'))
            at_risk = len(pledges.filtered(lambda p: p.status == 'at_risk'))
            
            completed_pct = (completed / total * 100) if total > 0 else 0
            on_track_pct = (in_progress / total * 100) if total > 0 else 0
            
            # Rule-based AI summary generation
            summary_parts = []
            
            # Overall status
            if completed_pct >= 70:
                summary_parts.append(f"Excellent progress: {completed_pct:.0f}% of pledges are completed, {on_track_pct:.0f}% are on track.")
            elif completed_pct >= 40:
                summary_parts.append(f"Moderate progress: {completed_pct:.0f}% of pledges are completed, {on_track_pct:.0f}% are on track.")
            else:
                summary_parts.append(f"Limited progress: {completed_pct:.0f}% of pledges are completed. Focus needed on pending goals.")
            
            # Department highlights
            dept_stats = {}
            for pledge in pledges:
                dept = pledge.department_id.name or "Unknown"
                if dept not in dept_stats:
                    dept_stats[dept] = {'total': 0, 'completed': 0, 'avg_progress': []}
                dept_stats[dept]['total'] += 1
                if pledge.status == 'completed':
                    dept_stats[dept]['completed'] += 1
                dept_stats[dept]['avg_progress'].append(pledge.progress_percent)
            
            # Find top performing department
            if dept_stats:
                top_dept = max(dept_stats.items(), key=lambda x: sum(x[1]['avg_progress']) / len(x[1]['avg_progress']) if x[1]['avg_progress'] else 0)
                dept_name, stats = top_dept
                avg_progress = sum(stats['avg_progress']) / len(stats['avg_progress']) if stats['avg_progress'] else 0
                summary_parts.append(f"{dept_name} leads with an average progress of {avg_progress:.1f}%.")
            
            # At-risk warning
            if at_risk > 0:
                summary_parts.append(f"Warning: {at_risk} pledge(s) are at risk and require immediate attention.")
            
            # Specific achievements
            completed_pledges = pledges.filtered(lambda p: p.status == 'completed')
            if completed_pledges:
                summary_parts.append(f"Notable achievements: {', '.join([p.title for p in completed_pledges[:3]])}.")
            
            rec.ai_summary = " ".join(summary_parts)
    
    def action_generate_report(self):
        """Generate the impact report with HTML content"""
        self.ensure_one()
        pledges = self._get_filtered_pledges()
        
        if not pledges:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No pledges found matching the criteria.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Generate summary
        total_pledges = len(pledges)
        completed = len(pledges.filtered(lambda p: p.status == 'completed'))
        in_progress = len(pledges.filtered(lambda p: p.status == 'in_progress'))
        at_risk = len(pledges.filtered(lambda p: p.status == 'at_risk'))
        
        avg_progress = self.impact_score
        
        # Calculate metrics
        energy_pledges = pledges.filtered(lambda p: 'kwh' in (p.unit or '').lower())
        total_energy = sum(energy_pledges.mapped('current_value'))
        
        volunteer_pledges = pledges.filtered(lambda p: 'hour' in (p.unit or '').lower())
        total_volunteer_hours = sum(volunteer_pledges.mapped('current_value'))
        
        summary_html = f"""
        <div class="o_report_csr">
            <h2>Executive Summary</h2>
            <p><strong>Report Date:</strong> {self.report_date}</p>
            <p><strong>Period:</strong> {self.period}</p>
            <p><strong>Total Initiatives:</strong> {total_pledges}</p>
            <p><strong>Completed:</strong> {completed} ({completed/total_pledges*100:.1f}%)</p>
            <p><strong>In Progress:</strong> {in_progress}</p>
            <p><strong>At Risk:</strong> {at_risk}</p>
            <p><strong>Average Progress:</strong> {avg_progress:.1f}%</p>
            <hr/>
            <h3>Key Metrics</h3>
            <ul>
                <li><strong>Total Volunteer Hours:</strong> {total_volunteer_hours:,.0f}</li>
                <li><strong>Total Energy Saved:</strong> {total_energy:,.2f} kWh</li>
            </ul>
            <p><strong>Status:</strong> {self.on_track_status}</p>
        </div>
        """
        
        # Generate detailed analysis
        detailed_html = f"""
        <div class="o_report_csr">
            <h2>Detailed Analysis</h2>
            <h3>By Department</h3>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Department</th>
                        <th># Initiatives</th>
                        <th>Completed</th>
                        <th>Avg Progress</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        Department = self.env['csr.department']
        for dept in Department.search([]):
            dept_pledges = pledges.filtered(lambda p: p.department_id.id == dept.id)
            if dept_pledges:
                avg = sum(dept_pledges.mapped('progress_percent')) / len(dept_pledges)
                completed_count = len(dept_pledges.filtered(lambda p: p.status == 'completed'))
                detailed_html += f"""
                    <tr>
                        <td>{dept.name}</td>
                        <td>{len(dept_pledges)}</td>
                        <td>{completed_count}</td>
                        <td>{avg:.1f}%</td>
                    </tr>
                """
        
        detailed_html += """
                </tbody>
            </table>
            <h3>Top Performing Initiatives</h3>
            <ul>
        """
        
        top_pledges = pledges.sorted(key=lambda p: p.progress_percent, reverse=True)[:5]
        for pledge in top_pledges:
            detailed_html += f"<li><strong>{pledge.title}</strong> - {pledge.progress_percent:.1f}% progress ({pledge.status})</li>"
        
        detailed_html += """
            </ul>
        </div>
        """
        
        # Generate recommendations
        recommendations = []
        if avg_progress < 70:
            recommendations.append("Focus on accelerating progress for initiatives below 70% completion.")
        if completed < total_pledges * 0.5:
            recommendations.append("Increase focus on completing in-progress initiatives.")
        
        low_progress_pledges = pledges.filtered(lambda p: p.progress_percent < 50)
        if low_progress_pledges:
            recommendations.append(f"Review and support {len(low_progress_pledges)} initiative(s) with progress below 50%.")
        
        if at_risk > 0:
            recommendations.append(f"Immediate attention required for {at_risk} at-risk initiative(s).")
        
        if not recommendations:
            recommendations.append("All initiatives are progressing well. Keep up the excellent work!")
        
        self.write({
            'summary': summary_html,
            'detailed_analysis': detailed_html,
            'recommendations': '\n'.join(recommendations),
            'state': 'generated'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Report'),
            'res_model': 'csr.report',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_pledges(self):
        """View the pledges included in this report"""
        self.ensure_one()
        pledges = self._get_filtered_pledges()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pledges'),
            'res_model': 'csr.pledge',
            'view_mode': 'list,form',
            'domain': [('id', 'in', pledges.ids)],
        }
    
    def action_generate_ai_pdf(self):
        """Generate AI-powered PDF report using external API"""
        self.ensure_one()
        
        if self.state != 'generated':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Please generate the report first before creating AI PDF.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        pledges = self._get_filtered_pledges()
        if not pledges:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No pledges found to generate AI report.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Build comprehensive prompt for AI
        total_pledges = len(pledges)
        completed = len(pledges.filtered(lambda p: p.status == 'completed'))
        in_progress = len(pledges.filtered(lambda p: p.status == 'in_progress'))
        at_risk = len(pledges.filtered(lambda p: p.status == 'at_risk'))
        avg_progress = self.impact_score
        
        # Get department breakdown
        dept_info = []
        Department = self.env['csr.department']
        for dept in Department.search([]):
            dept_pledges = pledges.filtered(lambda p: p.department_id.id == dept.id)
            if dept_pledges:
                dept_info.append(f"{dept.name}: {len(dept_pledges)} pledges, {sum(dept_pledges.mapped('progress_percent')) / len(dept_pledges):.1f}% avg progress")
        
        # Build AI prompt
        prompt = f"""Generate a comprehensive CSR (Corporate Social Responsibility) impact report in markdown format about our organization's CSR initiatives.

Report Period: {self.period}
Report Date: {self.report_date}

Key Statistics:
- Total CSR Initiatives: {total_pledges}
- Completed: {completed} ({completed/total_pledges*100:.1f}%)
- In Progress: {in_progress}
- At Risk: {at_risk}
- Average Progress: {avg_progress:.1f}%

Department Performance:
{chr(10).join(f'- {info}' for info in dept_info) if dept_info else '- No department data available'}

Top Performing Initiatives:
{chr(10).join(f'- {p.title}: {p.progress_percent:.1f}% progress ({p.status})' for p in sorted(pledges, key=lambda x: x.progress_percent, reverse=True)[:5])}

AI Summary: {self.ai_summary or 'No summary available'}

Please generate a professional markdown report with:
1. Executive Summary
2. Key Achievements
3. Departmental Analysis
4. Impact Metrics
5. Recommendations for Future Initiatives
6. Conclusion

Format the report professionally with proper headings, bullet points, and clear sections."""
        
        if not URLLIB_AVAILABLE:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('urllib is not available. Cannot generate AI PDF.'),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        try:
            # Call AI API
            api_url = self.ai_api_url or "http://127.0.0.1:5000/generate_report"
            
            filename = f"CSR_Report_{self.period.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            payload = {
                "prompt": prompt,
                "return_file": True,  # Return PDF directly
                "filename": filename
            }
            
            # Prepare request
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                api_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            # Make request with timeout
            try:
                with urllib.request.urlopen(req, timeout=180) as response:
                    content_type = response.headers.get('Content-Type', '')
                    
                    if response.status == 200 and 'application/pdf' in content_type:
                        # Read PDF content
                        pdf_content = response.read()
                        
                        # Save PDF to binary field
                        pdf_data = base64.b64encode(pdf_content).decode('utf-8')
                        
                        self.write({
                            'ai_pdf_filename': filename,
                            'ai_pdf_data': pdf_data,
                            'ai_pdf_generated': True,
                        })
                        
                        # Return success notification and refresh view
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Success'),
                                'message': _('AI PDF generated successfully! Use the Download button to get the file.'),
                                'type': 'success',
                                'sticky': False,
                            }
                        }
                    else:
                        # Try to read error message
                        try:
                            error_content = response.read().decode('utf-8')
                            error_data = json.loads(error_content)
                            error_msg = error_data.get('message', 'Unknown error')
                        except:
                            error_msg = f"API returned status {response.status}"
                        
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Error'),
                                'message': _('Failed to generate AI PDF: %s') % error_msg,
                                'type': 'danger',
                                'sticky': True,
                            }
                        }
            except urllib.error.URLError as e:
                if 'timed out' in str(e).lower() or isinstance(e, urllib.error.HTTPError):
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Timeout'),
                            'message': _('AI service request timed out. Please try again later.'),
                            'type': 'warning',
                            'sticky': True,
                        }
                    }
                else:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Connection Error'),
                            'message': _('Cannot connect to AI service. Please ensure the AI report service is running at %s. Error: %s') % (api_url, str(e)),
                            'type': 'danger',
                            'sticky': True,
                        }
                    }
                
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error generating AI PDF: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_download_ai_pdf(self):
        """Download the AI-generated PDF"""
        self.ensure_one()
        if not self.ai_pdf_data:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No AI PDF available. Please generate it first.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Use Odoo's binary field download mechanism
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=csr.report&id={self.id}&field=ai_pdf_data&filename_field=ai_pdf_filename&download=true',
            'target': 'self',
        }
    
    def action_generate_pdf(self):
        """Generate PDF report for this CSR report"""
        self.ensure_one()
        
        if self.state != 'generated':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Please generate the report first before creating PDF.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        pledges = self._get_filtered_pledges()
        if not pledges:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No pledges found to generate PDF report.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Prepare data for PDF generation
        data = {
            'report_name': self.name,
            'report_date': str(self.report_date),
            'period': self.period,
            'generated_on': self.generated_on.strftime('%Y-%m-%d %H:%M:%S') if self.generated_on else '',
            'impact_score': self.impact_score,
            'on_track_status': self.on_track_status,
            'total_pledges': len(pledges),
            'completed_pledges': len(pledges.filtered(lambda p: p.status == 'completed')),
            'in_progress_pledges': len(pledges.filtered(lambda p: p.status == 'in_progress')),
            'at_risk_pledges': len(pledges.filtered(lambda p: p.status == 'at_risk')),
            'draft_pledges': len(pledges.filtered(lambda p: p.status == 'draft')),
            'avg_progress': self.impact_score,
            'recommendations': self.recommendations or 'No recommendations available.',
            'report_id': self.id,
        }
        
        # Calculate metrics
        energy_pledges = pledges.filtered(lambda p: 'kwh' in (p.unit or '').lower() or 'energy' in (p.unit or '').lower())
        total_energy = sum(energy_pledges.mapped('current_value'))
        
        volunteer_pledges = pledges.filtered(lambda p: 'hour' in (p.unit or '').lower() or 'volunteer' in (p.unit or '').lower())
        total_volunteer_hours = sum(volunteer_pledges.mapped('current_value'))
        
        data['total_energy_saved'] = total_energy
        data['total_volunteer_hours'] = total_volunteer_hours
        
        # Department breakdown
        dept_breakdown = []
        Department = self.env['csr.department']
        for dept in Department.search([]):
            dept_pledges = pledges.filtered(lambda p: p.department_id.id == dept.id)
            if dept_pledges:
                avg_progress = sum(dept_pledges.mapped('progress_percent')) / len(dept_pledges)
                completed = len(dept_pledges.filtered(lambda p: p.status == 'completed'))
                dept_breakdown.append({
                    'name': dept.name,
                    'total': len(dept_pledges),
                    'completed': completed,
                    'avg_progress': avg_progress
                })
        data['department_breakdown'] = dept_breakdown
        
        # Top performing pledges
        top_pledges = pledges.sorted(key=lambda p: p.progress_percent, reverse=True)[:10]
        data['top_pledges'] = [
            {
                'title': p.title,
                'department': p.department_id.name if p.department_id else 'N/A',
                'owner': p.owner_id.name if p.owner_id else 'N/A',
                'progress': p.progress_percent,
                'status': dict(p._fields['status'].selection).get(p.status, p.status),
                'current_value': p.current_value,
                'target_value': p.target_value,
                'unit': p.unit or 'N/A'
            }
            for p in top_pledges
        ]
        
        # Generate PDF
        try:
            pdf_data = self._generate_pdf_report(data)
            
            # Generate filename
            filename = f"SustainHub_Report_{self.period.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            # Store PDF
            self.write({
                'pdf_filename': filename,
                'pdf_report': base64.b64encode(pdf_data),
                'pdf_generated': True,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('PDF report generated successfully! Use the Download PDF button to get the file.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except ImportError as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('ReportLab library is not installed. Please install it using: pip install reportlab'),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error generating PDF: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def _generate_pdf_report(self, data):
        """Internal method to generate PDF using ReportLab"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.units import inch
            from reportlab.pdfgen import canvas
            import io
        except ImportError:
            raise ImportError("ReportLab is not installed. Install it using: pip install reportlab")
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=50, bottomMargin=50, leftMargin=50, rightMargin=50)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title Style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        # Heading Style
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
        )
        
        # Subheading Style
        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#3b82f6'),
            spaceAfter=8,
        )
        
        # Title
        elements.append(Paragraph("SustainHub CSR Impact Report", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Report Information
        elements.append(Paragraph("Report Information", heading_style))
        
        report_info = [
            ['Report Name:', data.get('report_name', 'N/A')],
            ['Period:', data.get('period', 'N/A')],
            ['Report Date:', data.get('report_date', 'N/A')],
            ['Generated On:', data.get('generated_on', 'N/A')],
        ]
        
        info_table = Table(report_info, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Overall Performance
        elements.append(Paragraph("Overall Performance", heading_style))
        
        impact_score = data.get('impact_score', 0)
        score_color = colors.HexColor('#10b981') if impact_score >= 75 else colors.HexColor('#f59e0b') if impact_score >= 50 else colors.HexColor('#ef4444')
        
        performance_data = [
            ['Metric', 'Value'],
            ['Overall Impact Score', f"{impact_score:.2f} / 100"],
            ['Total Initiatives', str(data.get('total_pledges', 0))],
            ['Completed', f"{data.get('completed_pledges', 0)} ({data.get('completed_pledges', 0) / max(data.get('total_pledges', 1), 1) * 100:.1f}%)"],
            ['In Progress', str(data.get('in_progress_pledges', 0))],
            ['At Risk', str(data.get('at_risk_pledges', 0))],
            ['Average Progress', f"{data.get('avg_progress', 0):.1f}%"],
            ['Status', data.get('on_track_status', 'N/A')],
        ]
        
        perf_table = Table(performance_data, colWidths=[3*inch, 3*inch])
        perf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('TEXTCOLOR', (1, 1), (1, 1), score_color),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(perf_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Key Metrics
        elements.append(Paragraph("Key Metrics", heading_style))
        
        metrics_data = [
            ['Metric', 'Value'],
            ['Total Energy Saved', f"{data.get('total_energy_saved', 0):,.2f} kWh"],
            ['Total Volunteer Hours', f"{data.get('total_volunteer_hours', 0):,.0f} hours"],
        ]
        
        metrics_table = Table(metrics_data, colWidths=[3*inch, 3*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Department Breakdown
        if data.get('department_breakdown'):
            elements.append(Paragraph("Department Performance", heading_style))
            
            dept_headers = [['Department', '# Initiatives', 'Completed', 'Avg Progress (%)']]
            dept_rows = [
                [
                    dept['name'],
                    str(dept['total']),
                    str(dept['completed']),
                    f"{dept['avg_progress']:.1f}%"
                ]
                for dept in data['department_breakdown']
            ]
            dept_data = dept_headers + dept_rows
            
            dept_table = Table(dept_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            dept_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            
            elements.append(dept_table)
            elements.append(Spacer(1, 0.3*inch))
        
        # Top Performing Initiatives
        if data.get('top_pledges'):
            elements.append(PageBreak())
            elements.append(Paragraph("Top Performing Initiatives", heading_style))
            
            pledge_headers = [['Initiative', 'Department', 'Owner', 'Progress', 'Status', 'Value']]
            pledge_rows = []
            for pledge in data['top_pledges'][:10]:  # Limit to 10 for PDF
                pledge_rows.append([
                    pledge['title'][:30] + '...' if len(pledge['title']) > 30 else pledge['title'],
                    pledge['department'][:20] if len(pledge['department']) > 20 else pledge['department'],
                    pledge['owner'][:20] if len(pledge['owner']) > 20 else pledge['owner'],
                    f"{pledge['progress']:.1f}%",
                    pledge['status'],
                    f"{pledge['current_value']:.1f} / {pledge['target_value']:.1f} {pledge['unit']}"
                ])
            
            pledge_data = pledge_headers + pledge_rows
            pledge_table = Table(pledge_data, colWidths=[1.2*inch, 1*inch, 1*inch, 0.8*inch, 0.8*inch, 1.2*inch])
            pledge_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ]))
            
            elements.append(pledge_table)
            elements.append(Spacer(1, 0.3*inch))
        
        # Recommendations
        elements.append(Paragraph("Recommendations", heading_style))
        recommendations_text = data.get('recommendations', 'No recommendations available.')
        # Split recommendations by newlines and create paragraphs
        for rec_line in recommendations_text.split('\n'):
            if rec_line.strip():
                elements.append(Paragraph(f"• {rec_line.strip()}", styles['Normal']))
                elements.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def action_download_pdf(self):
        """Download the generated PDF report"""
        self.ensure_one()
        if not self.pdf_report:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No PDF available. Please generate it first.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=csr.report&id={self.id}&field=pdf_report&filename_field=pdf_filename&download=true',
            'target': 'self',
        }

