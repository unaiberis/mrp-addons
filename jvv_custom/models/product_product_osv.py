# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp.osv import fields, osv,  expression
import re


class product_product(osv.osv):
    _inherit = 'product.product'

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        result = super(product_product, self).name_search(
            cr, user, name=name, args=args, operator=operator, context=context, limit=100)
        ids2 = []
        if result:
            for l in result:
                ids2.append(l[0])
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            ids = []
            if operator in positive_operators:
                ids = self.search(cr, user, ['|',('product_category','=',name), ('default_code','=',name)]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('ean13','=',name)]+ args, limit=limit, context=context)
            if not ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                ids = self.search(cr, user, args + ['|', ('default_code', operator, name),('default_code', operator, name)], limit=limit, context=context)
                if not limit or len(ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(ids)) if limit else False
                    ids += self.search(cr, user, args + [('name', operator, name), ('id', 'not in', ids)], limit=limit2, context=context)
            elif not ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                ids = self.search(cr, user, args + ['&', ('product_category', operator, name), ('default_code', operator, name), ('name', operator, name)], limit=limit, context=context)
            if not ids and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user, ['|', ('product_category','=', res.group(2)),('default_code','=', res.group(2))] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)

        for my_id in ids:
            if not ids2 or my_id not in ids2:
                ids2.append(my_id)
        result = self.name_get(cr, user, ids2, context=context)
        return result
