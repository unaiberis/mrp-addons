# -*- coding: utf-8 -*-
# Copyright 2022 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, api
from openerp.osv import expression


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        results = super(ResUsers, self).name_search(
            name=name, args=args, operator=operator, limit=limit)
        if not args:
            args = []
        domain = expression.OR([[('name', operator, name)],
                                [('register_pass', operator, name)]])
        domain = expression.AND([domain, args or []])
        more_results = self.search(domain, limit=limit)
        return more_results and more_results.name_get() or results
