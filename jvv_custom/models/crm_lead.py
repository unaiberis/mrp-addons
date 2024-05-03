# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    offer_number = fields.Char(string="Offer number")
