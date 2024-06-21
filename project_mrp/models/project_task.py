from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    mrp_production_id = fields.Many2one(
        "mrp.production",
        string="Manufacturing Order",
    )
    product_id = fields.Many2one(
        related="mrp_production_id.product_id", string="Product", store=True
    )
