# Copyright 2024 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import fields, models


class MrpProductionHistoricalScheduledDate(models.Model):
    _name = "mrp.production.historical.scheduled.date"
    _description = "Historico de cambios de fecha programada en OFs"

    production_id = fields.Many2one(
        string="Orden de fabricación", comodel_name="mrp.production", copy=False
    )
    change_date = fields.Datetime(string="Fecha cambio", copy=False)
    user_id = fields.Many2one(
        string="Usuario que ha realizado el cambio",
        comodel_name="res.users",
        copy=False,
    )
    old_date = fields.Datetime(string="Fecha anterior", copy=False)
    new_date = fields.Datetime(string="Nueva fecha", copy=False)
