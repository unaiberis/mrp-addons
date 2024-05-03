# Copyright 2023 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import fields, models


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    certification_id = fields.Many2one(
        string="Calificación proveedor",
        comodel_name="product.supplierinfo.certification",
        related="name.certification_id",
        copy=False,
        store=True,
    )
