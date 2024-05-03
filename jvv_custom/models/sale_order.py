# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from dateutil.relativedelta import relativedelta
from odoo import _, api, exceptions, fields, models

from .._common import _convert_to_local_date


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends("out_picking_ids", "out_picking_ids.date_done")
    def _compute_dates_transfer_out_pickings(self):
        for sale in self:
            desc = ""
            for picking in sale.out_picking_ids:
                if picking.date_done:
                    date_done = _convert_to_local_date(
                        picking.date_done, self.env.user.tz
                    ).date()
                    desc = (
                        "{}: {}".format(picking.name, date_done)
                        if not desc
                        else "{}, {}: {}".format(desc, picking.name, date_done)
                    )
            if desc:
                sale.dates_transfer_out_pickings = desc

    offer_number = fields.Char(string="Offer number")
    opportunity_id = fields.Many2one(string="Opportunity", comodel_name="crm.lead")
    mrp_project_id = fields.Many2one(
        string="Manufacturing project", comodel_name="project.project", copy=False
    )
    out_picking_ids = fields.Many2many(
        string="Out pickings", comodel_name="stock.picking"
    )
    dates_transfer_out_pickings = fields.Char(
        string="Out pickings dates transfer",
        store=True,
        compute="_compute_dates_transfer_out_pickings",
    )
    procurement_sale_forecast_ids = fields.Many2many(
        string="With lines created from sale forecast",
        comodel_name="procurement.sale.forecast",
        relation="rel_sale_forecast_sale_order",
        column1="sale_order_id",
        column2="forecast_id",
        copy=False,
        readonly=True,
    )

    def action_button_confirm(self):
        production_obj = self.env["mrp.production"]
        for sale in self:
            for line in sale.order_line:
                if not line.requested_date and "assemtronic" not in self.env.cr.dbname:
                    raise exceptions.Warning(
                        "Para confirmar un pedido de venta, todas sus línea deben de tener la fecha solicitada introducida."
                    )
                lines2 = sale.order_line.filtered(lambda x: x.id != line.id)
                for tax in line.tax_id:
                    for line2 in lines2:
                        if line2.tax_id and tax not in line2.tax_id:
                            raise exceptions.Warning(
                                "Se han encontrado líneas con impuestos diferentes"
                            )
        sales = self.filtered(lambda x: x.main_project_id)
        if sales:
            sales.write({"main_project_id": False})
        res = super().action_button_confirm()
        for sale in self:
            pickings = self.env["stock.picking"]
            if sale.picking_ids:
                sale.order_line.write({"out_picking_id": sale.picking_ids[0].id})
                for picking in sale.picking_ids:
                    pickings += picking
            if pickings:
                sale.out_picking_ids = [(6, 0, pickings.ids)]
            for line in sale.order_line.filtered(lambda x: x.delay and x.delay > 1):
                confirmed_date = fields.Datetime.to_string(
                    fields.Datetime.from_string(fields.Datetime.now())
                    + relativedelta(days=int(line.delay))
                )
                if line.confirmed_date:
                    line.confirmed_date = confirmed_date
            cond = [("sale_order", "=", sale.id)]
            p = production_obj.search(cond, limit=1)
            if p and p.sale_line_id and not p.sale_line_id.mrp_production_id:
                p.sale_line_id.mrp_production_id = p.id
            if p and p.sale_line and not p.sale_line.mrp_production_id:
                p.sale_line.mrp_production_id = p.id
            if p and p.project_id:
                sale.write({"mrp_project_id": p.project_id.id})
                if p.product_id and p.product_id.project_template_id:
                    lines = []
                    for line in p.product_id.project_template_id.task_ids:
                        lines.append((0, 0, {"name": line.name}))
                    p.project_id.tasks = lines
        for sale in self.filtered(lambda x: x.mrp_project_id):
            cond = [("project_id", "=", sale.mrp_project_id.id)]
            all_productions = production_obj.search(cond)
            if all_productions:
                production_with_sale_line = all_productions.filtered(
                    lambda x: x.sale_line_id
                )
                if production_with_sale_line:
                    all_productions.write(
                        {"parent_mrp_production_id": production_with_sale_line.id}
                    )
        return res

    def automatic_catch_picking_transfer_dates(self):
        cond = []
        sales = self.search(cond)
        for sale in sales:
            try:
                pickings = self.env["stock.picking"]
                if sale.picking_ids:
                    for picking in sale.picking_ids:
                        pickings += picking
                if pickings:
                    sale.out_picking_ids = [(6, 0, pickings.ids)]
                    self.env.cr.commit()
            except Exception:
                continue

    def onchange_partner_id(self, part):
        result = super().onchange_partner_id(part)
        if not part:
            return result
        part = self.env["res.partner"].browse(part)
        commercial = False
        if part.user_id:
            commercial = part.user_id.id
        result["value"]["user_id"] = commercial
        return result

    @api.model
    def create(self, vals):
        partner_obj = self.env["res.partner"]
        partner = False
        if "partner_id" in vals and (
            "user_id" not in vals or not vals.get("user_id", False)
        ):
            partner = partner_obj.browse(vals.get("partner_id"))
            if partner and partner.user_id:
                vals["user_id"] = partner.user_id.id
        if (
            "origin" in vals
            and vals.get("origin", False)
            and (
                "Opportunity" in vals.get("origin", False)
                or "Oportunidad" in vals.get("origin", False)
            )
        ):
            if not partner:
                partner = partner_obj.browse(vals.get("partner_id"))
            if partner.customer_payment_mode:
                vals["payment_mode_id"] = partner.customer_payment_mode.id
        return super().create(vals)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends(
        "order_partner_id",
        "product_id",
        "product_id.customer_ids",
        "product_id.customer_ids.product_code",
        "product_id.customer_ids.product_name",
    )
    def _compute_customer_product_code_with_deno(self):
        for line in self.filtered(lambda x: x.product_id and x.order_partner_id):
            supplierinfo = line.product_id.customer_ids.filtered(
                lambda x: x.name.id == line.order_partner_id.id
            )
            if supplierinfo:
                if len(supplierinfo) > 1:
                    supplierinfo = supplierinfo[0]
                code = "[{}] {} ".format(
                    supplierinfo.product_code or " ",
                    supplierinfo.product_name or line.product_id.name,
                )
                line.customer_product_code_with_deno = code

    @api.depends("out_picking_id", "out_picking_id.date_done")
    def _compute_out_picking_date_done(self):
        for line in self.filtered(
            lambda x: x.out_picking_id and x.out_picking_id.date_done
        ):
            my_date = fields.Datetime.from_string(line.out_picking_id.date_done)
            line.out_picking_date_done = my_date.date()

    committed_date = fields.Boolean(string="Committed date", default=False)
    client_order_ref = fields.Char(
        string="Order reference", related="order_id.client_order_ref", store=True
    )
    customer_product_code = fields.Char(string="Customer product code")
    customer_product_code_with_deno = fields.Char(
        string="Customer product code",
        store=True,
        compute="_compute_customer_product_code_with_deno",
    )
    notes2 = fields.Text(string="Notes 2", translate=True)
    out_picking_id = fields.Many2one(string="Out picking", comodel_name="stock.picking")
    out_picking_date_done = fields.Date(
        string="Transfer date out picking",
        store=True,
        compute="_compute_out_picking_date_done",
    )
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string="Pricelist",
        store=True,
        readonly=True,
        related="order_id.pricelist_id",
        copy=False,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        store=True,
        readonly=True,
        related="pricelist_id.currency_id",
        copy=False,
    )
    from_forecast_id = fields.Many2one(
        string="Created from sale forecast",
        comodel_name="procurement.sale.forecast",
        readonly=True,
        copy=False,
    )
    from_forecast_line2_id = fields.Many2one(
        string="Created from sale forecast line",
        comodel_name="procurement.sale.forecast.line2",
        readonly=True,
        copy=False,
    )

    def product_id_change_with_wh(
        self,
        pricelist,
        product,
        qty=0,
        uom=False,
        qty_uos=0,
        uos=False,
        name="",
        partner_id=False,
        lang=False,
        update_tax=True,
        date_order=False,
        packaging=False,
        fiscal_position=False,
        flag=False,
        warehouse_id=False,
    ):
        res = super().product_id_change_with_wh(
            pricelist,
            product,
            qty=qty,
            uom=uom,
            qty_uos=qty_uos,
            uos=uos,
            name=name,
            partner_id=partner_id,
            lang=lang,
            update_tax=update_tax,
            date_order=date_order,
            packaging=packaging,
            fiscal_position=packaging,
            flag=flag,
            warehouse_id=warehouse_id,
        )
        if product and partner_id:
            mydate = fields.Date.context_today(self)
            p = self.env["product.product"].browse(product)
            customerinfo = p.customer_ids.filtered(lambda x: x.name.id == partner_id)
            customerinfo2 = self.env["product.supplierinfo"]
            for l in p.customer_ids.filtered(
                lambda x: x.name.id == partner_id and x.delay and x.date_validity
            ):
                if (
                    mydate >= l.date_validity
                    and (not l.expiration_date or l.expiration_date) >= mydate
                ):
                    customerinfo2 += l
            if customerinfo2 and customerinfo2.round_quantity_sale:
                customerinfo = customerinfo2
            if customerinfo:
                res["value"]["customer_product_code"] = customerinfo.product_code
                if (
                    customerinfo.expiration_date
                    and mydate >= customerinfo.expiration_date
                ):
                    if "warning" in res and res.get("warning").get("message", False):
                        if "with expired rate" not in res.get("warning").get("message"):
                            message = res.get("warning").get("message")
                            message += _(", product with expired rate.")
                            res["warning"]["message"] = message
                    else:
                        warning = {
                            "title": _("Price Error!"),
                            "message": _("Product with expired rate."),
                        }
                        res["warning"] = warning
            customerinfo2 = p.customer_ids.filtered(
                lambda x: x.name.id == partner_id
                and x.delay
                and x.date_validity
                and x.date_validity >= mydate
                and (not x.expiration_date or x.expiration_date <= mydate)
            )
            if customerinfo2:
                value = res.get("value")
                name = value.get("delay")
                res["value"]["delay"] = customerinfo2.delay
            else:
                if customerinfo and customerinfo.delay:
                    value = res.get("value")
                    name = value.get("delay")
                    res["value"]["delay"] = customerinfo.delay
            if p.default_code:
                value = res.get("value")
                name = value.get("name")
                if name and p.default_code not in name:
                    res["value"]["name"] = "[{}] {}".format(p.default_code, name)
                else:
                    res["value"]["name"] = name
            cond = [("product_id", "=", p.id), ("completed_line", "=", False)]
            lines = self.env["procurement.sale.forecast.line2"].search(cond)
            forecasts = self.env["procurement.sale.forecast"]
            for line in lines:
                if line.forecast_id not in forecasts:
                    forecasts += line.forecast_id
            if forecasts:
                forecast_lit = False
                for forecast in forecasts:
                    forecast_lit = (
                        forecast.name
                        if not forecast_lit
                        else "{}, {}".format(forecast_lit, forecast.name)
                    )
                message = (
                    "El producto: {}, se encuentra en las siguientes "
                    "previsiones: {}".format(p.name, forecast_lit)
                )
                if "warning" in res and res.get("warning").get("message", False):
                    if "with expired rate" not in res.get("warning").get("message"):
                        old_message = res.get("warning").get("message")
                        new_mesaje = "{}\n{}".format(old_message, message)
                        res["warning"]["message"] = new_mesaje
                else:
                    if "assemtronic" not in self.env.cr.dbname:
                        warning = {
                            "title": "Producto en previsiones",
                            "message": message,
                        }
                        res["warning"] = warning
            if (
                not forecasts
                and not p.include_in_forecast
                and "assemtronic" not in self.env.cr.dbname
            ):
                message = "El producto: {}, no se incluye en previsiones".format(p.name)
                if "warning" in res and res.get("warning").get("message", False):
                    if "with expired rate" not in res.get("warning").get("message"):
                        old_message = res.get("warning").get("message")
                        new_mesaje = "{}\n{}".format(old_message, message)
                        res["warning"]["message"] = new_mesaje
                else:
                    if "assemtronic" not in self.env.cr.dbname:
                        warning = {
                            "title": "Producto en previsiones",
                            "message": message,
                        }
                        res["warning"] = warning
        return res

    @api.model
    def run_load_customer_product_code(self):
        lines = self.search([])
        lines._compute_customer_product_code_with_deno()

    def automatic_put_out_picking_in_lines(self):
        cond = [("out_picking_id", "=", False)]
        lines = self.search(cond)
        for line in lines.filtered(lambda x: x.order_id):
            try:
                if line.order_id.picking_ids:
                    line.out_picking_id = line.order_id.picking_ids[0].id
                    self.env.cr.commit()
            except Exception:
                continue

    def unlink(self):
        forecast_lines = self.env["procurement.sale.forecast.line2"]
        for line in self:
            if (
                line.from_forecast_line2_id
                and line.from_forecast_line2_id not in forecast_lines
            ):
                forecast_lines += line.from_forecast_line2_id
        result = super().unlink()
        if forecast_lines:
            self.forecast_lines_after_unlink_sale_order_line(forecast_lines)
        return result

    def forecast_lines_after_unlink_sale_order_line(self, forecast_lines):
        forecasts = self.env["procurement.sale.forecast"]
        for forecast_line in forecast_lines:
            if forecast_line.forecast_id not in forecasts:
                forecasts += forecast_line.forecast_id
            sale_orders = self.env["sale.order"]
            cond = [
                ("from_forecast_line2_id", "!=", False),
                ("from_forecast_line2_id", "=", forecast_line.id),
            ]
            sale_lines = self.env["sale.order.line"].search(cond)
            qty_in_sale_lines = 0
            if sale_lines:
                for sale_line in sale_lines:
                    qty_in_sale_lines += sale_line.product_uom_qty
                    if sale_line.order_id not in sale_orders:
                        sale_orders += sale_line.order_id
            if sale_orders:
                forecast_line.write(
                    {
                        "sale_order_ids": [(6, 0, sale_orders.ids)],
                        "remaining_qty": forecast_line.qty - qty_in_sale_lines,
                    }
                )
            else:
                forecast_line.sale_order_ids = [(6, 0, [])]
                forecast_line.write({"remaining_qty": 0, "completed_line": False})
        for forecast in forecasts:
            sale_orders = self.env["sale.order"]
            for forecast_line in forecast.forecast_lines2_ids:
                for sale in forecast_line.sale_order_ids:
                    if sale not in sale_orders:
                        sale_orders += sale
            if sale_orders:
                forecast.sale_order_ids = [(6, 0, sale_orders.ids)]
            else:
                forecast.sale_order_ids = [(6, 0, [])]
