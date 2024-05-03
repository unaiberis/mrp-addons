# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    partner_id = fields.Many2one(
        string="Cliente/Proveedor",
        related="invoice_id.partner_id",
        store=True,
        copy=False,
    )
