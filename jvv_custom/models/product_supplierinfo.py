# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    def _get_default_product_id(self):
        try:
            if "default_product_tmpl_id" in self.env.context and self.env.context.get(
                "default_product_tmpl_id", False
            ):
                cond = [
                    (
                        "product_tmpl_id",
                        "=",
                        self.env.context.get("default_product_tmpl_id"),
                    )
                ]
                product = self.env["product.product"].search(cond, limit=1)
                if product:
                    return product.id
                else:
                    return False
            else:
                id = False
        except Exception:
            id = False
        return id

    prefix_code = fields.Char(
        string="Ref. interna producto",
        related="product_tmpl_id.prefix_code",
        store=True,
    )
    date_validity = fields.Date(string="Date validity")
    expiration_date = fields.Date(string="Expiration date")
    offer_number = fields.Char(string="Offer number")
    property_product_pricelist = fields.Many2one(
        string="Tarifa venta",
        comodel_name="product.pricelist",
        domain="[('type','=','sale')]",
        company_dependent=True,
        related="name.property_product_pricelist",
    )
    property_product_pricelist_purchase = fields.Many2one(
        string="Tarifa compra",
        comodel_name="product.pricelist",
        domain="[('type','=','purchase')]",
        company_dependent=True,
        related="name.property_product_pricelist_purchase",
    )
    product_id = fields.Many2one(default=_get_default_product_id)
    my_sequence = fields.Integer(string="Sequence", related="sequence")

    @api.onchange("date_validity")
    def onchange_date_validity(self):
        if not self.date_validity:
            self.expiration_date = False
        if self.date_validity:
            self.expiration_date = fields.Date.to_string(
                fields.Date.from_string(self.date_validity) + relativedelta(months=12)
            )
