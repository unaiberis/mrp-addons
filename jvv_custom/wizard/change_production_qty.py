# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, api


class ChangeProductionQty(models.TransientModel):
    _inherit = 'change.production.qty'

    @api.multi
    def change_prod_qty(self):
        res = super(ChangeProductionQty, self).change_prod_qty()
        if self.env.context.get('active_id', False):
            p = self.env['mrp.production'].browse(
                self.env.context.get('active_id'))
            lines = p.mapped('workcenter_lines').filtered(
                lambda l: l.external and not l.purchase_order)
            for line in lines:
                origin = u"%{}%{}%".format(p.name, line.name)
                cond = [('origin', 'ilike', origin)]
                purchase = self.env['purchase.order'].search(cond, limit=1)
                if purchase:
                    purchase.write({'mrp_operation': line.id,
                                    'mrp_production': p.id})
                    line.purchase_order = purchase.id
                    if (len(purchase.order_line) == 1 and purchase.state == 'draft'):
                        purchase.order_line[0].with_context(
                            no_call_wizard=True).write(
                            {'product_qty': p.product_qty})
            if p.move_prod_id and not p.move_prod_id.raw_material_production_id:
                cond = [('move_prod_id.raw_material_production_id', '=', p.id)]
                ofs = self.env['mrp.production'].search(cond)
                for of in ofs:
                    of.write({'product_qty': self.product_qty,
                              'product_uos_qty': self.product_qty})
                    cond = [('mrp_production', '=', of.id),
                            ('production_qty', '>', 0),
                            ('picking_type_id.code', '=', 'outgoing')]
                    pickings = self.env['stock.picking'].search(cond)
                    for picking in pickings:
                        picking.production_qty = self.product_qty
                cond = [('mrp_production', '=', p.id),
                        ('production_qty', '>', 0),
                        ('picking_type_id.code', '=', 'outgoing')]
                pickings = self.env['stock.picking'].search(cond)
                for picking in pickings:
                    picking.production_qty = self.product_qty
            if p.state == 'confirmed':
                p.un_book_mo()
                p.action_assign()
        return res
