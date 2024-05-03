# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo.osv import fields, osv


class mrp_production(osv.osv):
    _inherit = "mrp.production"

    _columns = {
        "date_planned": fields.datetime(
            "Scheduled Date",
            required=False,
            select=1,
            readonly=False,
            states={"done": [("readonly", True)]},
            copy=False,
        )
    }

    _defaults = {
        "date_planned": False,
    }
