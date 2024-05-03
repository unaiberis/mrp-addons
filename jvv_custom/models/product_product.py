# Copyright 2020 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.depends(
        "stock_quant_ids",
        "stock_quant_ids.location_id",
        "stock_quant_ids.location_id.usage",
        "stock_quant_ids.locked",
        "stock_quant_ids.qty",
    )
    def _compute_qty_lot_locked(self):
        for product in self:
            qty_locked = 0
            if product.stock_quant_ids:
                quants = product.stock_quant_ids.filtered(
                    lambda x: x.locked and x.location_id.usage == "internal"
                )
                if quants:
                    qty_locked = sum(quants.mapped("qty"))
            product.qty_locked = qty_locked

    mrp_production_ids = fields.One2many(
        string="MRP Productions",
        comodel_name="mrp.production",
        inverse_name="product_id",
    )
    count_mrp_productions = fields.Integer(
        string="MRP Productions counter",
        compute="_compute_count_mrp_productions",
        store=True,
    )
    last_ldm_total_cost = fields.Float(
        string="Last Manufacturing LdM Total Cost",
        related="last_mrp_id.ldm_total_cost",
        store=True,
        copy=False,
    )
    product_category = fields.Char(
        sring="Categoría producto", related="categ_id.name", store=True, copy=False
    )
    stock_quant_ids = fields.One2many(
        string="Quants",
        comodel_name="stock.quant",
        inverse_name="product_id",
        copy=False,
    )
    qty_locked = fields.Float(
        string="Cantidad bloqueada",
        copy=False,
        store=True,
        compute="_compute_qty_lot_locked",
    )

    @api.depends("mrp_production_ids")
    def _compute_count_mrp_productions(self):
        for product in self:
            product.count_mrp_productions = len(product.mrp_production_ids)

    def action_open_quants_locked(self):
        quants = self.env["stock.quant"]
        if self.stock_quant_ids:
            quants = self.stock_quant_ids.filtered(
                lambda x: x.locked and x.location_id.usage == "internal"
            )
        action = self.env.ref("stock.product_open_quants")
        action_dict = action.read()[0] if action else {}
        action_dict["domain"] = "[('id', 'in', {})]".format(quants.ids)
        action_dict["context"] = {"search_default_internal_loc": 1}
        return action_dict
