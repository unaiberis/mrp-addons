# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import api, fields, models
from pytz import timezone, utc

str2datetime = fields.Datetime.from_string
date2str = fields.Date.to_string


class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    @api.depends("date_planned")
    def _compute_date_planned_without_hour(self):
        tz = self.env.user.tz
        for procurement in self.filtered(lambda x: x.date_planned):
            date = self._convert_to_local_date(procurement.date_planned, tz=tz)
            procurement.date_planned_without_hour = date
            procurement.date_planned_year = date.year
            date_planned_month = ""
            if date.month == 1:
                date_planned_month = "Enero"
            if date.month == 2:
                date_planned_month = "Febrero"
            if date.month == 3:
                date_planned_month = "Marzo"
            if date.month == 4:
                date_planned_month = "Abril"
            if date.month == 5:
                date_planned_month = "Mayo"
            if date.month == 6:
                date_planned_month = "Junio"
            if date.month == 7:
                date_planned_month = "Julio"
            if date.month == 8:
                date_planned_month = "Agosto"
            if date.month == 9:
                date_planned_month = "Septiembre"
            if date.month == 10:
                date_planned_month = "Octubre"
            if date.month == 11:
                date_planned_month = "Noviembre"
            if date.month == 12:
                date_planned_month = "Diciembre"
            procurement.date_planned_month = date_planned_month

    date_planned_without_hour = fields.Date(
        string="Fecha planificada sin hora",
        store=True,
        compute="_compute_date_planned_without_hour",
    )
    date_planned_year = fields.Integer(
        string="Año planificacion",
        store=True,
        compute="_compute_date_planned_without_hour",
    )
    date_planned_month = fields.Selection(
        selection=[
            ("Enero", "Enero"),
            ("Febrero", "Febrero"),
            ("Marzo", "Marzo"),
            ("Abril", "Abril"),
            ("Mayo", "Mayo"),
            ("Junio", "Junio"),
            ("Julio", "Julio"),
            ("Agosto", "Agosto"),
            ("Septiembre", "Septiembre"),
            ("Octubre", "Octubre"),
            ("Noviembre", "Noviembre"),
            ("Diciembre", "Diciembre"),
        ],
        string="Año planificacion",
        store=True,
        compute="_compute_date_planned_without_hour",
    )
    product_categ_id = fields.Many2one(
        string="Product internal category",
        comodel_name="product.category",
        related="product_id.categ_id",
        store=True,
        copy=False,
    )
    product_tmpl_id = fields.Many2one(
        string="Plantilla producto",
        comodel_name="product.template",
        related="product_id.product_tmpl_id",
        store=True,
        copy=False,
    )
    product_internal_reference = fields.Char(
        string="Ref. Interna producto",
        related="product_id.default_code",
        store=True,
        copy=False,
    )
    product_standard_price = fields.Float(
        string="Precio coste",
        related="product_id.standard_price",
        digits="Product Price",
        store=True,
        copy=False,
    )
    product_manual_standard_cost = fields.Float(
        string="Coste standard manual",
        digits="Product Price",
        related="product_id.manual_standard_cost",
        store=True,
        copy=False,
    )
    product_state_copy = fields.Selection(
        String="Estado producto", related="product_id.state", store=True, copy=False
    )
    product_manager = fields.Many2one(
        string="Responsable producto",
        related="product_id.product_manager",
        store=True,
        copy=False,
    )

    def _convert_to_local_date(self, date, tz="UTC"):
        if not date:
            return False
        if not tz:
            tz = "UTC"
        new_date = str2datetime(date) if isinstance(date, str) else date
        new_date = new_date.replace(tzinfo=utc)
        local_date = new_date.astimezone(timezone(tz)).replace(tzinfo=None)
        return local_date

    @api.model
    def create(self, values):
        if values.get("name", False):
            if "MPS: " in values.get("name"):
                pos = values.get("name").find(" (")
                if pos > 0:
                    values["origin"] = values.get("name")[0:pos]
        return super().create(values)

    def write(self, values):
        if values.get("production_id", False):
            production = self.env["mrp.production"].browse(values.get("production_id"))
            cond = [("final_mrp_location", "=", True)]
            location = self.env["stock.location"].search(cond, limit=1)
            if location and production.location_dest_id != location.id:
                production.location_dest_id = location.id
        return super().write(values)

    @api.model
    def run_scheduler_assemtronic(self):
        cond = [("run_mrp_scheduler", "=", True)]
        locations = self.env["stock.location"].search(cond)
        try:
            dom = [("state", "=", "confirmed"), ("location_id", "in", locations.ids)]
            prev_ids = []
            while True:
                ids = self.search(dom)
                if not ids or prev_ids == ids:
                    break
                else:
                    prev_ids = ids
                ids.sudo().run(autocommit=False)
            offset = 0
            dom = [("state", "=", "running"), ("location_id", "in", locations.ids)]
            prev_ids = []
            while True:
                ids = self.search(dom, offset=offset)
                if not ids or prev_ids == ids:
                    break
                else:
                    prev_ids = ids
                ids.check(autocommit=False)
        except Exception:
            pass
