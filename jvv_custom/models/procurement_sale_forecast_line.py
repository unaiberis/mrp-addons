# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import _, api, exceptions, fields, models


class ProcurementSaleForecastLine(models.Model):
    _inherit = "procurement.sale.forecast.line"

    @api.depends(
        "partner_id",
        "product_tmpl_id",
        "product_tmpl_id.customer_ids",
        "product_tmpl_id.customer_ids.name",
        "product_tmpl_id.customer_ids.product_code",
    )
    def _compute_product_code(self):
        for line in self:
            product_code = ""
            if line.partner_id:
                for supinf in line.product_tmpl_id.customer_ids.filtered(
                    lambda x: x.name == line.partner_id and x.type == "customer"
                ):
                    if supinf.product_code:
                        product_code = supinf.product_code
            line.product_code = product_code

    product_category_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        related="product_id.categ_id",
        store=True,
        readonly="1",
    )
    product_tmpl_id = fields.Many2one(
        string="Product template", related="product_id.product_tmpl_id", store=True
    )
    product_code = fields.Char(
        string="Código producto para empresa",
        copy=False,
        store=True,
        compute="_compute_product_code",
        readonly="1",
    )
    procurement_state = fields.Selection(
        string="Estado abastecimiento",
        store=True,
        copy=False,
        related="procurement_id.state",
    )

    def request_procurement(self):
        self.ensure_one()
        res = super().request_procurement()
        context = self.env.context.copy()
        context.update({"mps_line_id": self.id})
        res["context"] = context
        return res

    @api.model
    def create(self, values):
        line = super().create(values)
        line._create_forectas_lines2()
        return line

    def _create_forectas_lines2(self):
        vals = {
            "forecast_id": self.forecast_id.id,
            "date": self.date,
            "product_id": self.product_id.id,
            "qty": self.qty,
        }
        self.env["procurement.sale.forecast.line2"].create(vals)


class ProcurementSaleForecastLine2(models.Model):
    _name = "procurement.sale.forecast.line2"
    _order = "product_id"

    forecast_id = fields.Many2one(
        comodel_name="procurement.sale.forecast", string="Forecast"
    )
    product_id = fields.Many2one(
        comodel_name="product.product", string="Product", required=True
    )
    product_tmpl_id = fields.Many2one(
        string="Product template", related="product_id.product_tmpl_id", store=True
    )
    date = fields.Date(string="Fecha")
    product_category_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        related="product_id.categ_id",
        store=True,
        readonly=True,
    )
    qty = fields.Float(
        string="Quantity",
        default=1,
        digits_compute=dp.get_precision("Product Unit of Measure"),
    )
    requested_qty = fields.Float(
        string="Requested Quantity",
        default=0,
        digits_compute=dp.get_precision("Product Unit of Measure"),
    )
    remaining_qty = fields.Float(
        string="Remaining Quantity",
        default=0,
        digits_compute=dp.get_precision("Product Unit of Measure"),
        readonly=True,
    )
    completed_line = fields.Boolean(
        string="Completed line", default=False, readonly="1"
    )
    sale_order_ids = fields.Many2many(
        string="In sale orders", comodel_name="sale.order", copy=False, readonly=True
    )

    def request_sale_order(self):
        self.ensure_one()
        if self.completed_line:
            raise exceptions.Warning(_("Completed line."))
        if not self.requested_qty:
            raise exceptions.Warning(_("You must enter Requested quantity."))
        if self.requested_qty > self.qty:
            raise exceptions.Warning(_("Requested quantity greater than quantity."))
        if self.remaining_qty > 0 and self.requested_qty > self.remaining_qty:
            raise exceptions.Warning(
                _("Requested quantity greater than Remaining quantity.")
            )

        wiz_obj = self.env["wiz.forecast.line2.to.sale.order"]
        wiz = wiz_obj.with_context(
            {
                "active_id": self.id,
                "active_ids": self.ids,
                "active_model": "procurement.sale.forecast.line2",
            }
        ).create({})
        context = self.env.context.copy()
        context.update(
            {
                "active_id": self.id,
                "active_ids": self.ids,
                "active_model": "procurement.sale.forecast.line2",
            }
        )
        return {
            "name": _("Forecast lines to sale order"),
            "type": "ir.actions.act_window",
            "res_model": "wiz.forecast.line2.to.sale.order",
            "view_type": "form",
            "view_mode": "form",
            "res_id": wiz.id,
            "target": "new",
            "context": context,
        }

    def unlink(self):
        forecasts = self.env["procurement.sale.forecast"]
        sale_line_obj = self.env["sale.order.line"]
        sale_lines = sale_line_obj
        for line in self:
            if line.forecast_id not in forecasts:
                forecasts += line.forecast_id
            cond = [("from_forecast_line2_id", "=", line.id)]
            salelines = sale_line_obj.search(cond)
            if salelines:
                for saleline in salelines:
                    if saleline.order_id.state != "draft":
                        raise exceptions.Warning(
                            _(
                                "You cannot delete this forecast line because it"
                                " is associated with the sales order: %s, that is"
                                " not in draft status."
                            )
                            % (saleline.order_id.name)
                        )
                    if saleline not in sale_lines:
                        sale_lines += saleline
        result = super().unlink()
        for forecast in forecasts:
            sale_orders = self.env["sale.order"]
            for forecast_line in forecast.forecast_lines2_ids:
                for sale in forecast_line.sale_order_ids:
                    if sale not in sale_orders:
                        sale_orders += sale
            forecast.write({"sale_order_ids": [(6, 0, sale_orders.ids)]})
        sale_orders = self.env["sale.order"]
        if sale_lines:
            sale_lines.unlink()
        return result
