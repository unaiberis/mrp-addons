##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from openerp import api, exceptions, fields, models


class SaleLineForecastLoad(models.TransientModel):
    _name = "sale.line.forecast.load"

    def _get_default_partner(self):
        model = self.env.context.get("active_model", False)
        record = self.env[model].browse(self.env.context.get("active_id"))
        partner = False
        if model == "sale.order":
            partner = record.partner_id
        return partner

    def _get_default_sale(self):
        model = self.env.context.get("active_model", False)
        record = self.env[model].browse(self.env.context.get("active_id"))
        sale = False
        if model == "sale.order":
            sale = record.id
        return sale

    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Cliente", default=_get_default_partner
    )
    sale_id = fields.Many2one(
        comodel_name="sale.order", string="Pedido venta", default=_get_default_sale
    )
    product_id = fields.Many2one(comodel_name="product.product", string="Producto")

    @api.multi
    def load_sales_lines(self):
        self.ensure_one()
        cond = [("product_id", "=", self.product_id.id), ("completed_line", "=", False)]
        lines = self.env["procurement.sale.forecast.line2"].search(cond)
        forecasts = self.env["procurement.sale.forecast"]
        for line in lines:
            if line.forecast_id not in forecasts:
                forecasts += line.forecast_id
        if not forecasts:
            raise exceptions.Warning(
                "No se ha encontrado ninguna previsión de venta para este producto"
            )
        return {
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "procurement.sale.forecast",
            "res_ids": forecasts.ids,
            "domain": [("id", "in", forecasts.ids)],
            "type": "ir.actions.act_window",
        }

    @api.onchange("product_id")
    def onchange_product_id(self):
        if self.product_id and self.partner_id:
            print("*******************")
            print("*** self.partner_id: " + str(self.partner_id))
            print(
                "*** self.product_id.customer_ids: " + str(self.product_id.customer_ids)
            )
            found = False
            if self.product_id.customer_ids:
                for line in self.product_id.customer_ids:
                    if line.name == self.partner_id:
                        found = True
            if not found:
                raise exceptions.Warning(
                    "No se ha encontrado relacion para la venta producto/cliente."
                )
