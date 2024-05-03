# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, fields, api, exceptions, _
from openerp.addons import decimal_precision as dp
from __builtin__ import True


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    @api.depends('lot_id', 'lot_id.life_date')
    def _compute_life_date(self):
        for quant in self.filtered(lambda c: c.lot_id and c.lot_id.life_date):
            quant.life_date = quant.lot_id.life_date
            quant.life_date_without_hour = (
                fields.Datetime.from_string(quant.lot_id.life_date).date())

    manual_value = fields.Float(
        string="Manual Value", store=True, compute=False,
        digits=dp.get_precision('Product Price'))
    real_value = fields.Float(
        string="Real Value", store=True, compute=False,
        digits=dp.get_precision('Product Price'))
    reserved_quant_for_especial_lot_ids = fields.Many2many(
        string='Especial lots for reserved quant', comodel_name='stock.quant',
        relation="rel_ope_operation_quant_reserved",
        column1="quant_id", column2="operation_id")
    free_quant_for_especial_lot_ids = fields.Many2many(
        string='Especial lots for free quant', comodel_name='stock.quant',
        relation="rel_ope_especial_quant_free",
        column1="quant_id", column2="operation_id")
    life_date = fields.Datetime(
        string='Expiry Date', related=False,
        compute='_compute_life_date',
        store=True, copy=False)
    life_date_without_hour = fields.Date(
        string='Expiry Date', compute='_compute_life_date',
        store=True, copy=False)
    product_tmpl_id = fields.Many2one(
        string='Product template', comodel_name='product.template')

    @api.model
    def create(self, values):
        if ('qty' in values and values.get('qty', 0) and 'cost' in values and
                values.get('cost', 0)):
            values['real_value'] = values.get('qty', 0) * values.get('cost', 0)
        if ('product_id' in values and values.get('product_id', False) and
                'qty' in values and values.get('qty', 0)):
            product = self.env['product.product'].browse(values.get('product_id'))
            values['manual_value'] = (
                product.manual_standard_cost * values.get('qty', 0))
        if 'product_id' in values and values.get('product_id', False):
            product = self.env['product.product'].browse(
                values.get('product_id'))
            values['product_tmpl_id'] = product.product_tmpl_id.id
        return super(StockQuant, self).create(values)

    @api.multi
    def write(self, values):
        if (len(self) == 1 and 'cost' in values and values.get('cost', 0) and
            'qty' in values and values.get('qty', 0)):
            values['real_value'] = values.get('qty', 0) * values.get('cost', 0)
            if self.product_id:
                values['manual_value'] = (
                    self.product_id.manual_standard_cost * values.get('qty', 0))
        if 'product_id' in values and values.get('product_id', False):
            product = self.env['product.product'].browse(
                values.get('product_id'))
            values['product_tmpl_id'] = product.product_tmpl_id.id
        return super(StockQuant, self).write(values)
