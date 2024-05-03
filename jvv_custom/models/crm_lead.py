# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, fields, api
from openerp.addons import decimal_precision as dp


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    offer_number = fields.Char(string='Offer number')
