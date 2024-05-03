# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import _, api, fields, models


class ProcurementSaleForecast(models.Model):
    _inherit = "procurement.sale.forecast"

    @api.depends("forecast_lines2_ids", "forecast_lines2_ids.completed_line")
    def _compute_state(self):
        for forecast in self:
            state = "draft"
            if forecast.forecast_lines2_ids:
                lines_finished = forecast.forecast_lines2_ids.filtered(
                    lambda x: x.completed_line
                )
                no_lines_finished = forecast.forecast_lines2_ids.filtered(
                    lambda x: not x.completed_line
                )
                if len(forecast.forecast_lines2_ids) == len(no_lines_finished):
                    state = "pending"
                elif len(forecast.forecast_lines2_ids) != len(lines_finished):
                    state = "partial"
                else:
                    state = "finalized"
            forecast.state = state

    forecast_lines2_ids = fields.One2many(
        comodel_name="procurement.sale.forecast.line2",
        inverse_name="forecast_id",
        string="Forecast Lines to sale orders",
    )
    sale_order_ids = fields.Many2many(
        string="Forecast lines in sale orders",
        comodel_name="sale.order",
        relation="rel_sale_forecast_sale_order",
        column1="forecast_id",
        column2="sale_order_id",
        copy=False,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", _("Draft")),
            ("pending", _("Pending")),
            ("partial", _("Partial")),
            ("finalized", _("Finalized")),
        ],
        string="State",
        compute="_compute_state",
        store=True,
        copy=False,
    )
