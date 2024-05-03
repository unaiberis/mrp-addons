# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import api, fields, models


class WizChangeProductCategory(models.TransientModel):
    _name = "wiz.change.product.category"
    _description = "Asistente para cambiar categoria a productos"

    category_id = fields.Many2one(
        comodel_name="product.category", string="Nueva categoría"
    )

    @api.multi
    def change_category(self):
        self.ensure_one()
        products = self.env["product.product"].browse(
            self.env.context.get("active_ids")
        )
        products.write({"categ_id": self.category_id.id})
