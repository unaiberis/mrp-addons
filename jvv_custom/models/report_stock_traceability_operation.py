# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import api, fields, models


class ReportStockTraceabilityOperation(models.TransientModel):
    _inherit = "report.stock.traceability_operation"
    _order = "date desc, move_id, operation_id"

    inventory_description = fields.Char(string="Inventory description")

    @api.model
    def create(self, values):
        if values.get("move_id", False) and values.get("move_id"):
            move = self.env["stock.move"].browse(values.get("move_id"))
            if move.inventory_description:
                values["inventory_description"] = move.inventory_description
            return super().create(values)
