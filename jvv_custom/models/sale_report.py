# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp.osv import fields, osv


class SaleReport(osv.osv):
    _inherit = 'sale.report'

    _columns = {
        'customer_product_code': fields.char(string='Customer product code'),
    }

    def _select(self):
        select = super(SaleReport, self)._select()
        new_select = "{}, {} ".format(
            select, 'l.customer_product_code_with_deno as customer_product_code')
        return new_select

    def _group_by(self):
        group_by = super(SaleReport, self)._group_by()
        new_group_by = "{}, {} ".format(
            group_by, 'l.customer_product_code_with_deno')
        return new_group_by
