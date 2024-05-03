# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, fields, api, exceptions, _
from .._common import _convert_to_local_date
from openerp.addons import decimal_precision as dp


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    @api.depends('in_picking_ids', 'in_picking_ids.date_done')
    def _compute_dates_transfer_in_pickings(self):
        for p in self:
            desc = ''
            for picking in p.in_picking_ids:
                if picking.date_done:
                    date_done = _convert_to_local_date(
                        picking.date_done, self.env.user.tz).date()
                    desc = (
                        u"{}: {}".format(picking.name, date_done) if not
                        desc else u"{}, {}: {}".format(desc, picking.name,
                                                       date_done))
            p.dates_transfer_in_pickings = desc

    mail_send = fields.Selection(
        selection=[('no', 'No'),
                   ('si', 'Si')], string='Email enviado', default='no',
        copy=False)
    mrp_production_product_id = fields.Many2one(
        comodel_name='product.product', related='mrp_production.product_id',
        string='Product to produce', store=True)
    in_picking_ids = fields.Many2many(
        string='In pickings', comodel_name='stock.picking', copy=False)
    dates_transfer_in_pickings = fields.Char(
        string='In pickings dates transfer', store=True,
        compute='_compute_dates_transfer_in_pickings', copy=False)

    @api.multi
    def wkf_confirm_order(self):
        picking_obj = self.env['stock.picking']
        for purchase in self:
            for line in purchase.order_line:
                lines2 = purchase.order_line.filtered(lambda x: x.id != line.id)
                for tax in line.taxes_id:
                    for line2 in lines2:
                        if line2.taxes_id and tax not in line2.taxes_id:
                            raise exceptions.Warning(
                                "Se han encontrado líneas con impuestos diferentes")
        res = super(PurchaseOrder, self).wkf_confirm_order()
        for p in self.filtered(lambda c: c.state == 'confirmed' and
                               c.mrp_production):
            cond = [('mrp_production', '=', p.mrp_production.id)]
            pickings = picking_obj.search(cond).filtered(
                lambda x: x.picking_type_id.code == 'outgoing')
            for pi in pickings:
                pi.purchase_subcontratacion = p.id
            move = p.mrp_production.move_prod_id
            if p.mrp_operation.out_picking:
                p.mrp_operation.out_picking.production_qty = (
                    p.mrp_production.product_qty)
                if (move and move.raw_material_production_id and
                        p.mrp_operation and p.mrp_operation.out_picking):
                    production = move.raw_material_production_id
                    p.mrp_operation.out_picking.sale_line_requested_date = (
                        production.sale_line_requested_date)
                    p.mrp_operation.out_picking.sale_line_confirmed_date = (
                        production.sale_line_confirmed_date)
                if (move and not move.raw_material_production_id and
                        p.mrp_operation and p.mrp_operation.out_picking):
                    p.mrp_operation.out_picking.sale_line_requested_date = (
                        p.mrp_production.sale_line_requested_date)
                    p.mrp_operation.out_picking.sale_line_confirmed_date = (
                        p.mrp_production.sale_line_confirmed_date)
            else:
                for pi in pickings:
                    pi.production_qty = (
                        p.mrp_production.product_qty)
                    if (move and move.raw_material_production_id and
                            p.mrp_operation and p.mrp_operation.out_picking):
                        production = move.raw_material_production_id
                        pi.sale_line_requested_date = (
                            production.sale_line_requested_date)
                        pi.sale_line_confirmed_date = (
                            production.sale_line_confirmed_date)
                    if (move and not move.raw_material_production_id and
                            p.mrp_operation and p.mrp_operation.out_picking):
                        pi.sale_line_requested_date = (
                            p.mrp_production.sale_line_requested_date)
                        pi.sale_line_confirmed_date = (
                            p.mrp_production.sale_line_confirmed_date)
            pickings = self.env['stock.picking']
            if p.picking_ids:
                for picking in p.picking_ids:
                    pickings += picking
            if pickings:
                p.in_picking_ids = [(6, 0, pickings.ids)]
        return res

    @api.multi
    def automatic_catch_picking_transfer_dates(self):
        cond = []
        purchases = self.search(cond)
        for purchase in purchases:
            try:
                pickings = self.env['stock.picking']
                if purchase.picking_ids:
                    for picking in purchase.picking_ids:
                        pickings += picking
                if pickings:
                    purchase.in_picking_ids = [(6, 0, pickings.ids)]
                    self.env.cr.commit()
            except Exception:
                continue

    @api.multi
    def wkf_send_rfq(self):
        for purchase in self.filtered(lambda x: x.partner_id):
            if not purchase.partner_id.email:
                raise exceptions.Warning(
                    _("Partner %s without email.") % self.partner_id.name)
            if '@' not in purchase.partner_id.email:
                raise exceptions.Warning(
                    _("Partner %s with no recognizable email.") %
                    self.partner_id.name)
        return super(PurchaseOrder, self).wkf_send_rfq()

    @api.multi
    def write(self, values):
        if 'mrp_production' in values and not values.get('mrp_production'):
            for purchase in self.filtered(lambda x: x.mrp_production):
                raise exceptions.Warning(
                    _('You are trying to unlink the purchase order %s from the'
                      ' manufacturing order %s.') % (
                          purchase.name, purchase.mrp_production.name))
        return super(PurchaseOrder, self).write(values)

    @api.multi
    def copy(self, default=None):
        purchases = super(PurchaseOrder, self).copy(default=default)
        for purchase in purchases:
            for line in purchase.order_line:
                dummy, name = line.product_id.name_get()[0]
                if line.product_id.description_purchase:
                    name += '\n' + line.product_id.description_purchase
                line.write({'name': name,
                            'date_planned': fields.Date.context_today(self)})
        return purchases


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.multi
    @api.depends('partner_id', 'product_id', 'product_id.supplier_ids',
                 'product_id.supplier_ids.product_code',
                 'product_id.supplier_ids.product_name')
    def _compute_supplier_product_code(self):
        for line in self.filtered(lambda x: x.product_id and x.partner_id):
            supplierinfo = line.product_id.supplier_ids.filtered(
                lambda x: x.name.id == line.partner_id.id)
            if supplierinfo:
                if len(supplierinfo) > 1:
                    supplierinfo = supplierinfo[0]
                code = u"[{}] {} ".format(
                    supplierinfo.product_code or ' ',
                    supplierinfo.product_name or line.product_id.name)
                line.supplier_product_code = code

    supplier_product_code = fields.Char(
        string='Supplier product code', store=True,
        compute='_compute_supplier_product_code')
    notes2 = fields.Text(string='Notes 2', translate=True)
    currency_id = fields.Many2one(
        comodel_name='res.currency', string='Currency', store=True,
        readonly=True, related='order_id.currency_id', copy=False)
    virtual_available = fields.Float(
        string='Cantidad prevista',
        digits_compute=dp.get_precision('Product Unit of Measure'))

    @api.model
    def create(self, values):
        if ('product_id' in values and values.get('product_id', False) and
                'virtual_availble' not in values):
            p = self.env['product.product'].browse(values.get('product_id'))
            values['virtual_available'] = p.product_tmpl_id.virtual_available
        line = super(PurchaseOrderLine, self).create(values)
        return line

    @api.multi
    def write(self, values):
        wiz_obj = self.env['change.production.qty']
        if ('product_id' in values and values.get('product_id', False) and
                'virtual_availble' not in values):
            p = self.env['product.product'].browse(values.get('product_id'))
            values['virtual_available'] = p.product_tmpl_id.virtual_available
        res = super(PurchaseOrderLine, self).write(values)
        if (not self.env.context.get('no_call_wizard', False) and
            values.get('product_qty', False) and
                values.get('product_qty') > 0):
            for line in self.filtered(
                lambda c: c.product_id.type == 'product' and
                    c.order_id.mrp_production):
                wiz = wiz_obj.create({'product_qty': line.product_qty})
                production = line.order_id.mrp_production
                wiz.with_context(active_id=production.id).change_prod_qty()
        return res

    @api.model
    def run_load_supplier_product_code(self):
        lines = self.search([])
        lines._compute_supplier_product_code()

    @api.multi
    def onchange_product_id(self, pricelist_id, product_id, qty, uom_id,
                            partner_id, date_order=False,
                            fiscal_position_id=False, date_planned=False,
                            name=False, price_unit=False, state='draft'):
        res = super(PurchaseOrderLine, self).onchange_product_id(
            pricelist_id, product_id, qty, uom_id, partner_id,
            date_order=date_order, fiscal_position_id=fiscal_position_id,
            date_planned=date_planned, name=name, price_unit=price_unit,
            state=state)
        if product_id:
            p = self.env['product.product'].browse(product_id)
            res['value'].update(
                {'virtual_available': p.product_tmpl_id.virtual_available})
        if product_id and partner_id:
            mydate = fields.Date.context_today(self)
            supplierinfo = p.supplier_ids.filtered(
                lambda x: x.name.id == partner_id)
            if (supplierinfo and supplierinfo.expiration_date and
                    mydate >= supplierinfo.expiration_date):
                if ('warning' in res and
                        res.get('warning').get('message', False)):
                    if ('with expired rate' not in
                            res.get('warning').get('message')):
                        message = res.get('warning').get('message')
                        message += _(', product with expired rate.')
                        res['warning']['message'] = message
                else:
                    warning = {'title': _('Price Error!'),
                               'message': _('Product with expired rate.')}
                    res['warning'] = warning
        return res
