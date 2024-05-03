# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, fields, api, exceptions, _
from .._common import _convert_to_local_date


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    mrp_production_warn = fields.Selection(
        string='Manufacturing Order', related='product_id.mrp_production_warn')
    mrp_production_warn_msg = fields.Text(
        string='Message for Manufacturing Order',
        related='product_id.mrp_production_warn_msg')
    product_categ_id = fields.Many2one(
        string='Categoría producto', comodel_name='product.category')
    mo_skewback_date = fields.Date(
        string='MO Skewback date')
    manufacturing_blocked = fields.Boolean(
        string="Fabricación bloqueada", default=False)
    permission_to_block_manufacture = fields.Boolean(
        string="Permiso para bloquear fabricación",
        compute="_compute_permission_to_block_manufacture")
    ldm_total_cost = fields.Float(
        string="LdM Total Cost", related="bom_id.total_cost",
        store=True, copy=False)
    ldm_num_lines = fields.Integer(
        string="Num. Líneas en LdM", related="bom_id.num_lines", copy=False,
        store=True)
    historical_scheduled_date_ids = fields.One2many(
        string="Histórico cambio fecha programada",
        comodel_name="mrp.production.historical.scheduled.date",
        inverse_name="production_id", copy=False)

    def _compute_permission_to_block_manufacture(self):
        mrp_manager_group = self.env.ref('mrp.group_mrp_manager')
        permission = (True if self.env.user in mrp_manager_group.users else
                      False)
        for production in self:
            production.permission_to_block_manufacture = permission

    @api.multi
    def block_mrp_production(self):
        mrp_manager_group = self.env.ref('mrp.group_mrp_manager')
        if self.env.user not in mrp_manager_group.users:
            raise exceptions.Warning(
                "No tiene permisos para bloquear órdenes de fabricación") 
        self.write({'manufacturing_blocked': True})

    @api.multi
    def unblock_mrp_production(self):
        mrp_manager_group = self.env.ref('mrp.group_mrp_manager')
        if self.env.user not in mrp_manager_group.users:
            raise exceptions.Warning(
                "No tiene permisos para desbloquear órdenes de fabricación") 
        self.write({'manufacturing_blocked': False})

    @api.multi
    def action_review_serial_numbers(self):
        if self.product_id.generate_serial_numbers  == "yes":
            wiz_obj = self.env['wiz.review.mrp.serial']
            wiz = wiz_obj.with_context(
                {'active_id': self.id,
                 'active_ids': self.ids,
                 'active_model': 'mrp.production'}).create({})
            context = self.env.context.copy()
            context.update({
                'active_id': self.id,
                'active_ids': self.ids,
                'active_model': 'mrp.production',
            })
            return {
                'name': _('Aviso'),
                'type': 'ir.actions.act_window',
                'res_model': 'wiz.review.mrp.serial',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': wiz.id,
                'target': 'new',
                'context': context,
            }                     
        else:
            self.action_assign()

    @api.multi
    def action_assign(self):
        for production in self.filtered(
            lambda x: x.manufacturing_blocked and
                x.state in ('confirmed', 'picking_except')):
            raise exceptions.Warning(
                (u"La órden de fabricación: %s, está bloqueada.")
                % production.name)
        return super(MrpProduction, self).action_assign()

    def _calc_production_attachments_jvv(self):
        for production in self:
            attachments = self.env['ir.attachment']
            if production.product_id:
                cond = [('res_model', '=', 'product.template'),
                        ('res_id', '=', production.product_id.product_tmpl_id.id)]
                attachment = self.env['ir.attachment'].search(cond)
                if attachment:
                    attachments += attachment
            if (production.parent_mrp_production_id and
                    production.parent_mrp_production_id.product_attachments):
                attachments += production.parent_mrp_production_id.product_attachments
            production.product_attachments_jvv = [(6, 0, attachments.ids)]

    def _default_location_dest_id(self):
        cond = [('final_mrp_location', '=', True)]
        location = self.env['stock.location'].search(cond, limit=1)
        if location:
            return location[0]
        return super(MrpProduction, self)._dest_id_default()

    @api.multi
    def _compute_productions_count(self):
        p_obj = self.env['mrp.production']
        for p in self:
            if not p.move_prod_id and p.project_id:
                cond = [('project_id', '=', p.project_id.id),
                        ('id', '!=', p.id)]
                productions = p_obj.search(cond)
                p.productions_count = len(productions)
            if (p.move_prod_id and p.move_prod_id.raw_material_production_id):
                p.productions_count = 1

    @api.multi
    @api.depends('parent_mrp_production_id',
                 'parent_mrp_production_id.sale_line_id',
                 'parent_mrp_production_id.sale_line_id.requested_date',
                 'parent_mrp_production_id.sale_line_id.confirmed_date',
                 'parent_mrp_production_id.sale_line_id.committed_date')
    def _compute_sale_line_dates2(self):
        for p in self.filtered(lambda c: c.parent_mrp_production_id):
            confirmed_date = False
            requested_date = False
            if (p.parent_mrp_production_id.sale_line_id and
                    p.parent_mrp_production_id.sale_line_id.requested_date):
                sale_line = p.parent_mrp_production_id.sale_line_id
                new_date = _convert_to_local_date(
                    sale_line.requested_date, self.env.user.tz)
                requested_date = new_date
                p.sale_line_requested_date = new_date.date()
            if (p.parent_mrp_production_id.sale_line_id and
                    p.parent_mrp_production_id.sale_line_id.confirmed_date):
                sale_line = p.parent_mrp_production_id.sale_line_id
                new_date = _convert_to_local_date(
                    sale_line.confirmed_date, self.env.user.tz)
                confirmed_date = new_date
                p.sale_line_confirmed_date = new_date.date()
            p.sale_line_committed_date = (
                p.parent_mrp_production_id.sale_line_id.committed_date)
            if confirmed_date and requested_date:
                self.env.cr.execute(
                    "UPDATE stock_move SET confirmed_date = %s, confirmed_date_without_hour = %s, requested_date = %s WHERE raw_material_production_id = %s;",
                    (confirmed_date, confirmed_date.date(), requested_date, p.id),)
            if confirmed_date and not requested_date:
                self.env.cr.execute(
                    "UPDATE stock_move SET confirmed_date = %s, confirmed_date_without_hour = %s WHERE raw_material_production_id = %s;",
                    (confirmed_date, confirmed_date.date(), p.id),)
            if not confirmed_date and requested_date:
                self.env.cr.execute(
                    "UPDATE stock_move SET requested_date = %s WHERE raw_material_production_id = %s;",
                    (requested_date, p.id),)

    @api.multi
    @api.depends('parent_mrp_production_id',
                 'parent_mrp_production_id.commitment_date')
    def _compute_parent_commitment_date(self):
        for p in self.filtered(lambda c: c.parent_mrp_production_id):
            if (p.parent_mrp_production_id and
                    p.parent_mrp_production_id.commitment_date):
                p.parent_commitment_date = (
                    p.parent_mrp_production_id.commitment_date)

    @api.multi
    @api.depends('product_id', 'sale_id', 'move_prod_id',
                 'move_prod_id.raw_material_production_id',
                 'move_prod_id.raw_material_production_id.product_code')
    def _compute_product_code(self):
        for p in self.filtered(lambda c: c.sale_id and c.product_id and
                               c.move_prod_id and not
                               c.move_prod_id.raw_material_production_id):
            for s in p.product_id.customer_ids:
                if s.name.id == p.sale_id.partner_id.id:
                    p.product_code = s.product_code
                    break
                if (p.sale_id.partner_id and
                        s.name.id == p.sale_id.partner_id.parent_id.id):
                    p.product_code = s.product_code
                    break
        for p in self.filtered(lambda c: not c.sale_id and
                               c.move_prod_id and
                               c.move_prod_id.raw_material_production_id and
                               c.move_prod_id.raw_material_production_id.product_code):
            p.product_code = p.move_prod_id.raw_material_production_id.product_code

    @api.multi
    @api.depends('product_qty', 'routing_id', 'routing_id.load_time_variable',
                 'load_time_line', 'load_time_variable')
    def _compute_load_time_variable(self):
        for p in self.filtered(lambda c: c.routing_id):
            p.load_time_variable = (
                p.product_qty * p.routing_id.load_time_variable)
            p.total_line_hours = p.load_time_line + p.load_time_variable

    @api.multi
    @api.depends('product_qty', 'routing_id',
                 'routing_id.load_time_variable_warehouse',
                 'load_time_warehouse', 'load_time_variable_warehouse')
    def _compute_load_time_variable_warehouse(self):
        for p in self.filtered(lambda c: c.routing_id):
            p.load_time_variable_warehouse = (
                p.product_qty * p.routing_id.load_time_variable_warehouse)
            p.total_warehouse_time = (
                p.load_time_warehouse + p.load_time_variable_warehouse)

    @api.multi
    @api.depends('date_planned')
    def _compute_date_planned_without_hour(self):
        for p in self.filtered(lambda c: c.date_planned):
            p.date_planned_without_hour = (
                fields.Datetime.from_string(p.date_planned).date())
            p.date_planned_month = (
                str(fields.Datetime.from_string(p.date_planned).month))
            p.date_planned_year = (
                fields.Datetime.from_string(p.date_planned).year)
            p.date_planned_week = (
                int(fields.Datetime.from_string(p.date_planned).strftime("%V")))
            from_date = _convert_to_local_date(
                p.date_planned, self.env.user.tz)
            p.day_of_week = str(from_date.date().weekday())

    @api.multi
    def _compute_mrp_project_task_count(self):
        for p in self.filtered(lambda c: c.project_id):
            p._mrp_project_task_count = len(p.project_id.task_ids)

    @api.multi
    @api.depends('purchase_subcontratacion_ids',
                 'purchase_subcontratacion_ids.state')
    def _compute_purchase_subcontratacion_id(self):
        for production in self.filtered(lambda x: x.purchase_subcontratacion_ids):
            for purchase in production.purchase_subcontratacion_ids:
                production.purchase_subcontratacion_id = purchase.id

    productions_count = fields.Integer(
        string='Producciones relacionadas',
        compute='_compute_productions_count')
    sale_line_id = fields.Many2one(store=True)
    sale_line_requested_date = fields.Date(
        string='Fec.Solicitud línea venta',
        compute='_compute_sale_line_dates2', store=True)
    sale_line_confirmed_date = fields.Date(
        string='Fec.Confirmada línea venta',
        compute='_compute_sale_line_dates2', store=True)
    product_code = fields.Char(
        string='Código producto empresa', compute='_compute_product_code',
        store=True)
    production_line_id = fields.Many2one(
        string='Production line', comodel_name='mrp.routing.production.line',
        related='routing_id.production_line_id', store=True)
    load_time_line = fields.Float(
        string="Load time line", related='routing_id.load_time_line',
        store=True)
    load_time_variable = fields.Float(
        string="Time to load variable", compute='_compute_load_time_variable',
        store=True)
    total_line_hours = fields.Float(
        string="Total line hours", compute='_compute_load_time_variable',
        store=True)
    load_time_warehouse = fields.Float(
        string="Load time warehouse", store=True,
        related='routing_id.load_time_warehouse')
    load_time_variable_warehouse = fields.Float(
        string="Time variable load warehouse", store=True,
        compute='_compute_load_time_variable_warehouse')
    total_warehouse_time = fields.Float(
        string="Total warehouse time", store=True,
        compute='_compute_load_time_variable_warehouse')
    date_planned_without_hour = fields.Date(
        string='Date planned', compute='_compute_date_planned_without_hour',
        store=True)
    sale_line_committed_date = fields.Boolean(
        string='Committed date', compute='_compute_sale_line_dates2', store=True)
    date_planned_month = fields.Selection(
        [('1', _('January')), ('2', _('February')),
         ('3', _('March')), ('4', _('April')),
         ('5', _('May')), ('6', _('June')), ('7', _('July')),
         ('8', _('August')), ('9', _('September')),
         ('10', _('October')), ('11', _('November')),
         ('12', _('December'))], string='Planned month',
        compute='_compute_date_planned_without_hour', store=True)
    date_planned_year = fields.Integer(
        string='Planned year', store=True,
        compute='_compute_date_planned_without_hour')
    date_planned_week = fields.Integer(
        string='Planned week', store=True,
        compute='_compute_date_planned_without_hour')
    mrp_project_task_count = fields.Integer(
        string='Tasks numb.', compute='_compute_mrp_project_task_count')
    purchase_subcontratacion_ids = fields.One2many(
        string='Pedidos de compra subcontratacion',
        comodel_name='purchase.order', inverse_name='mrp_production')
    purchase_subcontratacion_id = fields.Many2one(
        string='Doc. sub.', comodel_name='purchase.order',
        compute='_compute_purchase_subcontratacion_id', store=True)
    parent_mrp_production_id = fields.Many2one(
        string='Parent production', comodel_name='mrp.production',
        index=True)
    parent_commitment_date = fields.Datetime(
        string='Commitment Date', store=True,
        compute='_compute_parent_commitment_date')
    product_attachments_jvv = fields.Many2many(
        comodel_name='ir.attachment',
        string='Product attachments',
        compute='_calc_production_attachments_jvv', readonly=True)
    supplier_customer_material = fields.Boolean(
        string='Supplier/Customer material', default=False)
    count_mrp_productions = fields.Integer(
        string='MRP Productions counter', store=True,
        related='product_id.count_mrp_productions')
    version = fields.Integer(
        string='BoM Version', related="bom_id.version", store=True)
    mo_count = fields.Integer(
        string='# Manufacturing Orders', related='product_tmpl_id.mo_count')
    location_dest_id = fields.Many2one(
        default=_default_location_dest_id)
    manual_requested_date = fields.Date(
        string='Fec.Solicitud manual')
    manual_confirmed_date = fields.Date(
        string='Fec.Confirmada manual')
    day_of_week = fields.Selection(
        selection=[('0', _('Monday')),
                   ('1', _('Tuesday')),
                   ('2', _('Wednesday')),
                   ('3', _('Thursday')),
                   ('4', _('Friday')),
                   ('5', _('Saturday')),
                   ('6', _('Sunday'))],
        string='Day of the week',
        compute='_compute_date_planned_without_hour', store=True)

    @api.multi
    def action_ready(self):
        cond = [('final_mrp_location', '=', True)]
        location = self.env['stock.location'].search(cond, limit=1)
        res = super(MrpProduction, self).action_ready()
        for p in self.filtered(
            lambda c: c.move_prod_id and
            c.move_prod_id.raw_material_production_id and
            c.move_prod_id.raw_material_production_id.location_dest_id.id ==
            location.id and c.move_prod_id.location_id.id ==
                c.move_prod_id.raw_material_production_id.location_dest_id.id):
            p.move_prod_id.location_id = (
                p.move_prod_id.raw_material_production_id.location_src_id.id)
        return res

    @api.multi
    def buttom_show_related_productions(self):
        self.ensure_one()
        p_obj = self.env['mrp.production']
        productions = p_obj
        if not self.move_prod_id:
            cond = [('project_id', '=', self.project_id.id),
                    ('id', '!=', self.id)]
            productions = p_obj.search(cond)
        if (self.move_prod_id and
                self.move_prod_id.raw_material_production_id):
            productions = self.move_prod_id.raw_material_production_id
        if productions:
            return {'name': 'OFs relacionadas',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'tree,form,calendar,graph,gantt',
                    'view_type': 'form',
                    'res_model': 'mrp.production',
                    'domain': [('id', 'in', productions.ids)]}

    @api.multi
    def action_production_end(self):
        res = super(MrpProduction, self).action_production_end()
        for p in self:
            if p.sale_order:
                self.verify_sale_order_out_picking_location(p.sale_order, p)
            if not p.sale_order:
                cond = [('project_id', '=', p.project_id.id),
                        ('sale_order', '!=', False)]
                production = self.env['mrp.production'].search(cond, limit=1)
                if production:
                    self.verify_sale_order_out_picking_location(
                        production.sale_order, production)
        return res

    def verify_sale_order_out_picking_location(self, sale, production):
        cond = [('final_mrp_location', '=', True)]
        location = self.env['stock.location'].search(cond, limit=1)
        if location:
            for p in sale.picking_ids:
                lines = p.mapped('move_lines').filtered(
                    lambda l: l.location_id.id == location.id)
                if lines:
                    lines.write({'location_id': production.location_src_id.id})

    @api.one
    @api.depends('product_id')
    def _calc_production_attachments(self):
        self.product_attachments = None
        if self.product_id:
            cond = [('res_model', '=', 'product.template'),
                    ('res_id', '=', self.product_tmpl_id.id)]
            attachments = self.env['ir.attachment'].search(cond)
            cond = [('res_model', '=', 'product.product'),
                    ('res_id', '=', self.product_id.id)]
            attachments += self.env['ir.attachment'].search(cond)
            self.product_attachments = [(6, 0, attachments.mapped('id'))]

    @api.multi
    def bom_id_change(self, bom_id):
        res = super(MrpProduction, self).bom_id_change(bom_id)
        if bom_id:
            bom = self.env['mrp.bom'].browse(bom_id)
            if bom and bom.notes:
                res['value']['notes'] = bom.notes
        return res

    @api.model
    def create(self, values):
        if 'product_id' in values and values.get('product_id', False):
            product = self.env['product.product'].browse(
                values.get('product_id'))
            values['product_categ_id']= product.categ_id.id
        if values.get('bom_id', False) and 'notes' not in values:
            bom = self.env['mrp.bom'].browse(values.get('bom_id'))
            if bom and bom.notes:
                values['notes'] = bom.notes
        production = super(MrpProduction, self).create(values)
        if production.bom_id:
            lines = production.bom_id.bom_line_ids.filtered(
                lambda x: not x.operation)
            if lines:
                if production.bom_id.product_id:
                    raise exceptions.Warning((
                        "LdM con variante de producto: %s, con componentes que"
                        " les falta el campo CONSUMIDO EN.") %
                            production.bom_id.product_id.name)
                else:
                    raise exceptions.Warning((
                        "LdM con producto: %s, con componentes que les falta "
                        "el campo CONSUMIDO EN.") %
                        production.bom_id.product_tmpl_id.name)
        return production

    @api.multi
    def write(self, values, update=True, mini=True):
        if 'product_id' in values and values.get('product_id', False):
            product = self.env['product.product'].browse(
                values.get('product_id'))
            values['product_categ_id']= product.categ_id.id
            
        if "date_planned" in values:
            for production in self:
                vals = {"production_id": production.id,
                        "change_date": fields.Datetime.now(),
                        "user_id": self.env.user.id,
                        "old_date": production.date_planned,
                        "new_date": values.get("date_planned")}
                self.env["mrp.production.historical.scheduled.date"].create(vals)   
        result = super(MrpProduction, self).write(
            values, update=update, mini=mini)
        if 'bom_id' in values and values.get('bom_id', False):
            for production in self:
                if production.bom_id:
                    lines = production.bom_id.bom_line_ids.filtered(
                        lambda x: not x.operation)
                    if lines:
                        if production.bom_id.product_id:
                            raise exceptions.Warning((
                                "LdM con variante de producto: %s, con componentes que"
                                " les falta el campo CONSUMIDO EN.") %
                                    production.bom_id.product_id.name)
                        else:
                            raise exceptions.Warning((
                                "LdM con producto: %s, con componentes que les falta "
                                "el campo CONSUMIDO EN.") %
                                production.bom_id.product_tmpl_id.name)
        return result

    @api.multi
    def update_related_sale_line(self):
        return True

    @api.multi
    def buttom_show_mrp_project_tasks(self):
        self.ensure_one()
        if self.project_id:
            return {'name': 'Tareas',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'kanban,tree,form,calendar,gantt,graph',
                    'view_type': 'form',
                    'res_model': 'project.task',
                    'domain': [('id', 'in', self.project_id.task_ids.ids)]}

    @api.multi
    def automatic_put_parent_production(self):
        route_id = self.env.ref('mrp.route_warehouse0_manufacture').id
        cond = [('parent_mrp_production_id', '!=', False),
                ('sale_line_id', '!=', False)]
        productions = self.search(cond)
        a = 0
        for production in productions:
            a += 1
            if production.sale_line_id.order_id.mrp_project_id:
                sale = production.sale_line_id.order_id
                project = production.sale_line_id.order_id.mrp_project_id
                count = 0
                for line in sale.order_line:
                    if route_id in line.product_id.route_ids.ids:
                        count += 1
                if count == 1:
                    cond = [('project_id', '=', project.id),
                            ('parent_mrp_production_id', '=', False)]
                    p = self.search(cond)
                    if p:
                        p.write({'parent_mrp_production_id':
                                 production.id})

    @api.multi
    def action_view_mos(self):
        self.ensure_one()
        cond = [('product_tmpl_id', '=', self.product_tmpl_id.id)]
        productions = self.env['mrp.production'].search(cond)
        return {'name': 'Fabricación',
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'mrp.production',
                'domain': [('id', 'in', productions.ids)]}

    @api.multi
    def automatic_put_dates_to_mvtos_from_mo(self):
        cond = [('parent_mrp_production_id', '!=', False)]
        productions = self.search(cond)
        contador = 0
        for p in productions:
            contador += 1
            confirmed_date = False
            requested_date = False
            if (p.parent_mrp_production_id.sale_line_id and
                    p.parent_mrp_production_id.sale_line_id.requested_date):
                sale_line = p.parent_mrp_production_id.sale_line_id
                new_date = _convert_to_local_date(
                    sale_line.requested_date, self.env.user.tz)
                requested_date = new_date
            if (p.parent_mrp_production_id.sale_line_id and
                    p.parent_mrp_production_id.sale_line_id.confirmed_date):
                sale_line = p.parent_mrp_production_id.sale_line_id
                new_date = _convert_to_local_date(
                    sale_line.confirmed_date, self.env.user.tz)
                confirmed_date = new_date
            if confirmed_date and requested_date:
                self.env.cr.execute(
                    "UPDATE stock_move SET confirmed_date = %s, confirmed_date_without_hour = %s, requested_date = %s WHERE raw_material_production_id = %s;",
                    (confirmed_date, confirmed_date.date(), requested_date, p.id),)
            if confirmed_date and not requested_date:
                self.env.cr.execute(
                    "UPDATE stock_move SET confirmed_date = %s, confirmed_date_without_hour = %s WHERE raw_material_production_id = %s;",
                    (confirmed_date, confirmed_date.date(), p.id),)
            if not confirmed_date and requested_date:
                self.env.cr.execute(
                    "UPDATE stock_move SET requested_date = %s WHERE raw_material_production_id = %s;",
                    (requested_date, p.id),)

    @api.multi
    def action_confirm(self):
        sequence_obj = self.env['ir.sequence']
        move_obj = self.env['stock.move']
        sequence = self.env.ref(
            'jvv_custom.move_num_serie_sequence', False)
        for production in self.filtered(lambda c: not c.date_planned):
            raise exceptions.Warning(
                _("You must enter the scheduled date."))
        result = super(MrpProduction, self).action_confirm()
        for production in self:
            for move in production.move_lines:
                move.name = u"{} - {}".format(
                    production.name, production.product_id.name)
            lines = production.move_created_ids.filtered(
                lambda l: l.product_id.generate_serial_numbers == 'yes' and
                not l.serial_numbers)
            for line in lines:
                i = 1
                numbers = ''
                while i <= line.product_uom_qty:
                    if not line.product_id.serial_numbers_sequence_id:
                        serial = sequence_obj.next_by_id(sequence.id)
                    else:
                        serial = sequence_obj.next_by_id(
                            line.product_id.serial_numbers_sequence_id.id)
                    numbers += (
                        serial if not numbers else ", {}".format(serial))
                    i += 1
                if numbers:
                    line.serial_numbers = numbers
                if (numbers and line.sale_id and line.production_id and
                        line.production_id.sale_line_id):
                    cond = [('sale_order_line', '=',
                             line.production_id.sale_line_id.id)]
                    move2 = move_obj.search(cond, limit=1)
                    if move2:
                        move2.serial_numbers = numbers
            if not production.origin:
                cond = [('project_id', '=', production.project_id.id)]
                productions = self.search(cond)
                if productions:
                    productions.write(
                        {'parent_mrp_production_id': production.id})
        print ('*** he terminado de poner serials')
        return result


class MrpProductionWorkcenterLine(models.Model):
    _inherit = 'mrp.production.workcenter.line'

    @api.multi
    @api.depends('date_planned')
    def _compute_date_planned_without_hour(self):
        for p in self.filtered(lambda c: c.date_planned):
            p.date_planned_without_hour = (
                fields.Datetime.from_string(p.date_planned).date())
            p.date_planned_month = (
                str(fields.Datetime.from_string(p.date_planned).month))
            p.date_planned_year = (
                fields.Datetime.from_string(p.date_planned).year)
            p.date_planned_week = (
                int(fields.Datetime.from_string(p.date_planned).strftime("%V")))

    @api.depends('date_planned')
    def _compute_day(self):
        for line in self.filtered('date_planned'):
            from_date = _convert_to_local_date(
                line.date_planned, self.env.user.tz)
            line.day = str(from_date.date().weekday())

    @api.depends('hour', 'production_id', 'production_id.routing_id',
                 'production_id.routing_id.workcenter_lines',
                 'production_id.routing_id.workcenter_lines.op_wc_lines',
                 'production_id.routing_id.workcenter_lines.op_wc_lines.time_start',
                 'production_id.routing_id.workcenter_lines.op_wc_lines.time_stop')
    def _compute_total_phase_time(self):
        for line in self:
            hours = line.hour
            boot_time = False
            stopping_time = False
            if (line.production_id and line.production_id.routing_id and
                    line.production_id.routing_id.workcenter_lines):
                workcenters = line.production_id.routing_id.mapped(
                    'workcenter_lines').filtered(
                        lambda l: l.sequence == line.sequence and
                        l.workcenter_id == line.workcenter_id)
                if workcenters:
                    for work in workcenters:
                        if work.op_wc_lines:
                            op_wc_lines = work.op_wc_lines.filtered(
                                lambda l: l.workcenter == line.workcenter_id)
                            if op_wc_lines:
                                boot_time = sum(
                                    op_wc_lines.mapped('time_start'))
                                hours += boot_time
                                stopping_time = sum(
                                    op_wc_lines.mapped('time_stop'))
                                hours += stopping_time
            line.total_phase_time = hours
            if boot_time:
                line.boot_time = boot_time
            if stopping_time:
                line.stopping_time = stopping_time

    def _calc_workcenter_attachments_jvv(self):
        for line in self:
            attachments = self.env['ir.attachment']
            if line.workcenter_id:
                cond = [('res_model', '=', 'mrp.workcenter'),
                        ('res_id', '=', line.workcenter_id.id)]
                attachment = self.env['ir.attachment'].search(cond)
                if attachment:
                    attachments += attachment
            if (line.production_id and
                    line.production_id.product_attachments_jvv):
                attachments += line.production_id.product_attachments_jvv
            line.workcenter_attachments_jvv = [(6, 0, attachments.ids)]

    user_id = fields.Many2one(
        string='User', comodel_name='res.users')
    date_planned_without_hour = fields.Date(
        string='Scheduled date', compute='_compute_date_planned_without_hour',
        store=True)
    day = fields.Selection(
        selection=[('0', _('Monday')),
                   ('1', _('Tuesday')),
                   ('2', _('Wednesday')),
                   ('3', _('Thursday')),
                   ('4', _('Friday')),
                   ('5', _('Saturday')),
                   ('6', _('Sunday'))],
        string='Day of the week', compute='_compute_day', store=True)
    total_phase_time = fields.Float(
        string='Total phase time', compute='_compute_total_phase_time',
        store=True)
    boot_time = fields.Float(
        string='Boot time', compute='_compute_total_phase_time',
        store=True)
    boot_time = fields.Float(
        string='Boot time', compute='_compute_total_phase_time',
        store=True)
    stopping_time = fields.Float(
        string='Stopping time', compute='_compute_total_phase_time',
        store=True)
    date_planned_month = fields.Selection(
        [('1', _('January')), ('2', _('February')),
         ('3', _('March')), ('4', _('April')),
         ('5', _('May')), ('6', _('June')), ('7', _('July')),
         ('8', _('August')), ('9', _('September')),
         ('10', _('October')), ('11', _('November')),
         ('12', _('December'))], string='Planned month',
        compute='_compute_date_planned_without_hour', store=True)
    date_planned_year = fields.Integer(
        string='Planned year', store=True,
        compute='_compute_date_planned_without_hour')
    date_planned_week = fields.Integer(
        string='Planned week', store=True,
        compute='_compute_date_planned_without_hour')
    workcenter_attachments_jvv = fields.Many2many(
        comodel_name='ir.attachment',
        string='Product attachments',
        compute='_calc_workcenter_attachments_jvv', readonly=True)
    origin = fields.Char(
        string='Origen producción', related='production_id.origin', store=True,
        copy=False)
