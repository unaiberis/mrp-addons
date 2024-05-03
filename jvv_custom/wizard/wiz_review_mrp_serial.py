# Copyright 2024 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models


class WizReviewMrpSerial(models.TransientModel):
    _name = "wiz.review.mrp.serial"

    production_id = fields.Many2one(string="Fabricacion", comodel_name="mrp.production")

    @api.model
    def default_get(self, var_fields):
        result = super().default_get(var_fields)
        production_id = self.env.context.get("active_id", [])
        result["production_id"] = production_id
        return result

    def check_mrp_availability(self):
        if self.production_id:
            return self.production_id.action_assign()
