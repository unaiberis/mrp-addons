# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import api, models


class MakeProcurement(models.TransientModel):
    _inherit = "make.procurement"

    @api.multi
    def make_procurement(self):
        result = super().make_procurement()
        if (
            self.env.context.get("mps_line_id", False)
            and result.get("res_model", False)
            and result.get("res_model") == "procurement.order"
        ):
            line = self.env["procurement.sale.forecast.line"].browse(
                self.env.context.get("mps_line_id")
            )
            proc = self.env["procurement.order"].browse(result.get("res_id"))
            if proc.production_id:
                proc.production_id.origin = "MPS: {}".format(line.forecast_id.name)
            if not proc.origin:
                proc.origin = "MPS: {}".format(line.forecast_id.name)
        return result
