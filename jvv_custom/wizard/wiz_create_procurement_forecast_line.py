# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import api, models


class WizCreateProcurementForecastLine(models.TransientModel):
    _name = "wiz.create.procurement.forecast.line"

    @api.multi
    def create_procurements(self):
        line_obj = self.env["procurement.sale.forecast.line"]
        procurement_obj = self.env["procurement.order"]
        procure_lst = []
        lines = line_obj.browse(self.env.context.get("active_ids"))
        if lines:
            lines = lines.filtered(lambda x: x.product_id and not x.procurement_id)
            for line in lines:
                procure_id = procurement_obj.create(
                    {
                        "name": (
                            "MPS: "
                            + line.forecast_id.name
                            + " ("
                            + line.forecast_id.date_from
                            + "."
                            + line.forecast_id.date_to
                            + ") "
                            + line.forecast_id.warehouse_id.name
                        ),
                        "date_planned": line.date,
                        "product_id": line.product_id.id,
                        "product_qty": line.qty,
                        "product_uom": line.product_id.uom_id.id,
                        "location_id": line.forecast_id.warehouse_id.lot_stock_id.id,
                        "company_id": line.forecast_id.warehouse_id.company_id.id,
                        "warehouse_id": line.forecast_id.warehouse_id.id,
                    }
                )
                procure_id.signal_workflow("button_confirm")
                procure_lst.append(procure_id.id)
                line.procurement_id = procure_id.id
        return {
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "procurement.order",
            "res_ids": procure_lst,
            "domain": [("id", "in", procure_lst)],
            "type": "ir.actions.act_window",
        }
