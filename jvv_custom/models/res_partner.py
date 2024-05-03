# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.multi
    def _compute_count_customer_products(self):
        for partner in self:
            templates = self.env["product.template"]
            for line in partner.customer_product_supplierinfo_ids:
                if line.product_tmpl_id not in templates:
                    templates += line.product_tmpl_id
            partner.count_customer_products = len(templates)

    customer_product_supplierinfo_ids = fields.One2many(
        string="Customer products",
        comodel_name="product.supplierinfo",
        inverse_name="name",
        domain=[("type", "=", "customer")],
    )
    count_customer_products = fields.Integer(
        string="Customer products", compute="_compute_count_customer_products"
    )
    claims = fields.One2many(domain=[("nonconformity", "=", False)])
    non_conformities = fields.One2many(
        "crm.claim",
        "partner_id",
        string="Non Conformities",
        domain=[("nonconformity", "=", True)],
    )

    @api.multi
    def button_customer_product_template(self):
        templates = self.env["product.template"]
        for line in self.customer_product_supplierinfo_ids:
            if line.product_tmpl_id not in templates:
                templates += line.product_tmpl_id
        return {
            "name": _("Customer products"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "kanban,tree,form",
            "res_model": "product.template",
            "domain": [("id", "in", templates.ids)],
        }
