# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import api, models


class WizCancelStockPicking(models.TransientModel):
    _name = "wiz.cancel.stock.picking"
    _description = "Asistente para cancelar albaranes"

    def cancel_picking(self):
        self.ensure_one()
        pickings = self.env["stock.picking"].browse(self.env.context.get("active_ids"))
        for picking in pickings:
            picking.action_cancel()
