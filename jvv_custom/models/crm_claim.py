# Copyright 2020 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import fields, models


class CrmClaim(models.Model):
    _inherit = "crm.claim"

    amount_to_return = fields.Char(string="Amount to return")
    price = fields.Char(string="Price")
