# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, api, fields


class WizForecastLine2ToSaleOrder(models.TransientModel):
    _name = 'wiz.forecast.line2.to.sale.order'
    _description ="Forecast to sale order"

    def _get_default_sale_order(self):
        sale = False
        return sale

    sale_order_id = fields.Many2one(
        string="Sale Order", comodel_name="sale.order",
        default=_get_default_sale_order)

    @api.multi
    def create_sale_order_line(self):
        self.ensure_one()
        sale_line_obj = self.env['sale.order.line']
        line = self.env['procurement.sale.forecast.line2'].browse(
            self.env.context['active_id'])
        vals = {'order_id': self.sale_order_id.id,
                'product_id': line.product_id.id,
                'product_tmpl_id': line.product_id.product_tmpl_id.id,
                'product_uom_qty' : line.requested_qty,
                'from_forecast_line2_id': line.id,
                'from_forecast_id': line.forecast_id.id}
        new_sale_line = sale_line_obj.create(vals)
        
        
        result = new_sale_line.product_id_change_with_wh(
            self.sale_order_id.pricelist_id.id,
            line.product_id.id,
            qty=line.requested_qty,
            partner_id = self.sale_order_id.partner_id.id,
            date_order = self.sale_order_id.date_order,
            fiscal_position=self.sale_order_id.fiscal_position.id)
        if "value" in result:
            new_sale_line.write(result.get("value",{}))
        remaining_qty = line.remaining_qty + (line.qty - line.requested_qty)
        vals = {'remaining_qty': remaining_qty,
                'requested_qty': 0}
        if remaining_qty == line.qty:
            vals["completed_line"] = True
        sale_orders = line.sale_order_ids
        if new_sale_line.order_id not in sale_orders:
            sale_orders += new_sale_line.order_id
        vals["sale_order_ids"] = [(6, 0, sale_orders.ids)]
        line.write(vals)
        sale_orders = new_sale_line.order_id
        my_forecast = self.env['procurement.sale.forecast'].browse(
            line.forecast_id.id)
        for forecast_line in my_forecast.forecast_lines2_ids:
            for sale in forecast_line.sale_order_ids:
                if sale not in sale_orders:
                    sale_orders += sale
        my_forecast.write({"sale_order_ids": [(6, 0, sale_orders.ids)]})
