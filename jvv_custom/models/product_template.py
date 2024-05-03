# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('template_cost_price_history_ids',
                 'template_cost_price_history_ids.datetime',
                 'template_cost_price_history_ids.cost')
    def _compute_last_date_cost(self):
        for template in self.filtered(
                lambda l: l.template_cost_price_history_ids):
            c = max(template.template_cost_price_history_ids,
                    key=lambda x: x.datetime)
            if c:
                template.last_date_cost = c.datetime

    @api.depends('manual_standard_cost')
    def _compute_last_date_manual_cost(self):
        for template in self.filtered(lambda l: l.manual_standard_cost):
            template.last_date_manual_cost = fields.Datetime.now()

    @api.depends('mrp_bom_ids', 'mrp_bom_ids.active', 'mrp_bom_ids.version')
    def _compute_bom_version(self):
        for template in self:
            if template.mrp_bom_ids:
                boms = template.mapped('mrp_bom_ids').filtered(
                    lambda x: x.active and x.state == 'active')
                if boms and len(boms) == 1:
                    template.bom_version = boms.version
                if boms and len(boms) > 1:
                    template.bom_version = max(boms, key=lambda x: x.version)

    @api.depends('procurement_sale_forecast_line_ids',
                 'procurement_sale_forecast_line_ids.product_tmpl_id')
    def _compute_forecast_ids(self):
        for template in self:
            forecasts = self.env['procurement.sale.forecast']
            for line in template.procurement_sale_forecast_line_ids:
                if line.forecast_id not in forecasts:
                    forecasts += line.forecast_id
            if forecasts:
                template.forecast_ids = [(6, 0, forecasts.ids)]

    @api.depends('procurement_sale_forecast_line2_ids',
                 'procurement_sale_forecast_line2_ids.product_tmpl_id')
    def _compute_forecast2_ids(self):
        for template in self:
            forecasts = self.env['procurement.sale.forecast']
            for line in template.procurement_sale_forecast_line2_ids:
                if line.forecast_id not in forecasts:
                    forecasts += line.forecast_id
            if forecasts:
                template.forecast2_ids = [(6, 0, forecasts.ids)]

    @api.depends("stock_quant_ids", "stock_quant_ids.location_id",
                 "stock_quant_ids.location_id.usage",
                 "stock_quant_ids.locked", "stock_quant_ids.qty")
    def _compute_qty_lot_locked(self):
        for template in self:
            qty_locked = 0
            if template.stock_quant_ids:
                quants = template.stock_quant_ids.filtered(
                    lambda x: x.locked and x.location_id.usage == "internal")
                if quants:
                    qty_locked = sum(quants.mapped("qty"))
            template.qty_locked = qty_locked

    template_notes = fields.Text(string='Notas plantilla')
    generate_serial_numbers = fields.Selection(
        selection=[('yes', 'Yes'),
                   ('no', 'No')],
        string='Generate serial numbers', required=True, default='no')
    serial_numbers_sequence_id = fields.Many2one(
        comodel_name='ir.sequence', string='Serial numbers sequence')
    project_template_id = fields.Many2one(
        string='Project template', comodel_name='project.template')
    fix_negative_stock = fields.Boolean(
        string='Fix negative stock', default=False)
    template_cost_price_history_ids = fields.One2many(
        string='Cost price history', comodel_name='product.price.history',
        inverse_name='product_template_id')
    last_date_cost = fields.Datetime(
        string='Last date cost price', compute='_compute_last_date_cost',
        store=True)
    last_date_manual_cost = fields.Datetime(
        string='Last date manual cost price', store=True,
        compute='_compute_last_date_manual_cost')
    state = fields.Selection(
        selection=[('',''),
                   ('draft', _('In Development')),
                   ('sellable',_('Normal')),
                   ('end', _('End of Lifecycle')),
                   ('obsolete',_('Obsolete')),
                   ('favourite',_('Favourite')),
                   ('little',_('Little used')),
                   ('unutilized',_('Unutilized'))])
    mrp_bom_ids = fields.One2many(
        string='MRP BoMs', comodel_name='mrp.bom',
        inverse_name='product_tmpl_id')
    bom_version = fields.Integer(
        string='BoM Version', compute='_compute_bom_version', store=True)
    procurement_sale_forecast_line_ids = fields.One2many(
        string="Sale forecasts lines from sale orders",
        comodel_name="procurement.sale.forecast.line",
        inverse_name="product_tmpl_id")
    procurement_sale_forecast_line2_ids = fields.One2many(
        string="Sale forecasts lines to sale orders",
        comodel_name="procurement.sale.forecast.line2",
        inverse_name="product_tmpl_id")
    forecast_ids = fields.Many2many(
        comodel_name="procurement.sale.forecast",
        relation="rel_product_template_sale_forectast",
        column1="product_tmpl_id", column2="forectas_id",
        string="Sale forecasts from sale orders",
        copy=False, compute='_compute_forecast_ids', store=True)
    forecast2_ids = fields.Many2many(
        comodel_name="procurement.sale.forecast",
        relation="rel_product_template_sale_forectast2",
        column1="product_tmpl_id", column2="forectas_id",
        string="Sale forecasts to sale orders",
        copy=False, compute='_compute_forecast2_ids', store=True)
    robot = fields.Boolean(
        string="Robot", default=False)
    stock_quant_ids = fields.One2many(
        string='Quants', comodel_name='stock.quant',
        inverse_name='product_tmpl_id', copy=False)
    qty_locked = fields.Float(
        string="Cantidad bloqueada", copy=False, store=True,
        compute="_compute_qty_lot_locked")

    @api.multi
    def action_open_quants_locked(self):
        quants = self.env["stock.quant"]
        if self.stock_quant_ids:
            quants = self.stock_quant_ids.filtered(
                lambda x: x.locked and x.location_id.usage == "internal")
        result = self._get_act_window_dict("stock.product_open_quants")
        result["domain"] = "[('id', 'in', {})]".format(quants.ids)
        result['context'] = {'search_default_internal_loc': 1}
        return result

    @api.multi
    def write(self, values):
        res = super(ProductTemplate, self).write(values)
        if values.get('manual_standard_cost', False):
            for template in self:
                cond = [('product_tmpl_id', '=', template.id)]
                p = self.env['product.product'].search(cond, limit=1)
                if p:
                    p.manual_standard_cost = template.manual_standard_cost
        return res

    @api.multi
    def automatic_fix_product_negative_stock(self):
        wiz_obj = self.env['stock.change.product.qty']
        cond = [('fix_negative_stock', '=', True)]
        templates = self.search(cond)
        for template in templates:
            try:
                data = ['product_id', 'delete_negative_quants', 'lot_id',
                        'new_quantity', 'location_id']
                res = wiz_obj.with_context(
                    active_id=template.id,
                    active_model='product.template').default_get(data)
                product = self.env['product.product'].browse(res.get('product_id'))
                if product.qty_available < 0:
                    vals = {'location_id': res.get('location_id'),
                            'product_id': product.id,
                            'delete_negative_quants': True,
                            'new_quantity': product.qty_available * -1}
                    wiz = wiz_obj.create(vals)
                    res = wiz.change_product_qty()
                    template.fix_negative_stock = False
                self.env.cr.commit()
            except Exception:
                continue
