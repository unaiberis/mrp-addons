# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, fields, api, exceptions, _
from openerp.addons import decimal_precision as dp
from .._common import _convert_to_local_date


class StockLocation(models.Model):
    _inherit = 'stock.location'

    final_mrp_location = fields.Boolean(
        string="Location for MRP finished products", default=False)
    run_mrp_scheduler = fields.Boolean(
        string="Usar en planificador MRP", default=False)


class StockLocationRoute(models.Model):
    _inherit = 'stock.location.route'

    assemtronic_product = fields.Boolean(
        string="Assemtronic product", default=False)


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.depends('quant_ids', 'quant_ids.qty')
    def _compute_qty(self):
        for lot in self:
            lot.qty = sum(x.qty for x in lot.quant_ids)

    qty = fields.Float(
        string='Quantity', compute='_compute_qty', store=True)
    manufacturer_id = fields.Char(
        string="ID Manufacturer", copy=False)

    @api.model
    def create(self, values):
        if ("default_manufacturer_id" in self.env.context and
                self.env.context.get("default_manufacturer_id", False)):
            values["manufacture_id"] = (
                self.env.context.get("default_manufacturer_id"))
        lot = super(StockProductionLot, self).create(values)
        return lot


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    @api.depends('date_done')
    def _compute_date_done_without_hour(self):
        for picking in self:
            date_done_without_hour = False
            if picking.date_done:
                year = fields.Datetime.from_string(picking.date_done).year
                if year >= 1900:
                    new_date = _convert_to_local_date(
                        picking.date_done, self.env.user.tz)
                    date_done_without_hour = new_date.date()
            picking.date_done_without_hour = date_done_without_hour

    @api.multi
    @api.depends('date')
    def _compute_date_without_hour(self):
        for picking in self:
            date_without_hour = False
            if picking.date:
                new_date = _convert_to_local_date(
                    picking.date, self.env.user.tz)
                date_without_hour = new_date.date()
            picking.date_without_hour = date_without_hour

    @api.multi
    @api.depends('min_date')
    def _compute_min_date_without_hour(self):
        for picking in self:
            min_date_without_hour = False
            if picking.min_date:
                year = fields.Datetime.from_string(picking.min_date).year
                if year >= 1900:
                    new_date = _convert_to_local_date(
                        picking.min_date, self.env.user.tz)
                    min_date_without_hour = new_date.date()
            picking.min_date_without_hour = min_date_without_hour

    @api.multi
    @api.depends('purchase_subcontratacion',
                 'purchase_subcontratacion.mrp_production')
    def _compute_recorde_serial_number(self):
        for picking in self:
            record_serial_number = False
            if (picking.purchase_subcontratacion and
                    picking.purchase_subcontratacion.mrp_production):
                p = picking.purchase_subcontratacion.mrp_production
                if p.product_id.generate_serial_numbers == 'yes':
                    record_serial_number = True
            picking.recorded_serial_number = record_serial_number

    @api.multi
    @api.depends('mrp_production', 'mrp_production.product_code',
                 'move_lines', 'move_lines.product_id',
                 'move_lines.product_id.customer_ids')
    def _compute_product_code(self):
        for picking in self.filtered(lambda x: x.mrp_production):
            picking.product_code = picking.mrp_production.product_code
        for picking in self.filtered(lambda x: not x.mrp_production and
                                     x.picking_type_id and
                                     x.picking_type_id.code == 'outgoing'):
            code = ''
            for move in picking.move_lines:
                for s in move.product_id.customer_ids:
                    if (s.name.id == picking.partner_id.id and s.product_code):
                        code = (s.product_code if not code else
                                "{}, {}".format(code, s.product_code))
                        break
                    if (picking.partner_id and s.product_code and
                            s.name.id == picking.partner_id.parent_id.id):
                        code = (s.product_code if not code else
                                "{}, {}".format(code, s.product_code))
                        break
            if code:
                picking.product_code = code

    purchase_subcontratacion = fields.Many2one(
        string='Doc.Sub.', comodel_name='purchase.order')
    production_qty = fields.Float(
        string='Cantidad OF: ',
        digits_compute=dp.get_precision('Product Unit of Measure'))
    sale_line_requested_date = fields.Date(
        string='Fec.Solicitud línea venta', store=True)
    sale_line_confirmed_date = fields.Date(
        string='Fec.Confirm.línea venta', store=True)
    product_code = fields.Char(
        string='Código producto empresa',
        compute='_compute_product_code', store=True)
    date_done_without_hour = fields.Date(
        string="Transfer date", compute='_compute_date_done_without_hour',
        store=True)
    recorded_serial_number = fields.Boolean(
        string='Recorded serial number', store=True,
        compute='_compute_recorde_serial_number')
    shipping_address_in_pickings = fields.Boolean(
        string='Request shipping address in pickings', store=True,
        related='picking_type_id.shipping_address_in_pickings')
    mrp_production_notes = fields.Html(
        string='MRP production notes', related='mrp_production.notes')
    date_without_hour = fields.Date(
        string="Fecha creación", compute='_compute_date_without_hour',
        store=True)
    min_date_without_hour = fields.Date(
        string="Fecha prevista", compute='_compute_min_date_without_hour',
        store=True)

    @api.cr_uid_ids_context
    def do_enter_transfer_details(self, cr, uid, picking, context=None):
        move_obj = self.pool.get('stock.move')
        wiz_obj = self.pool.get('assign.manual.quants')
        wiz_line_obj = self.pool.get('assign.manual.quants.lines')
        if not picking:
            result = super(StockPicking, self).do_enter_transfer_details(
                cr, uid, picking, context=context)
            return result
        p = self.pool.get('stock.picking').browse(cr, uid, picking)
        if (not p or (p and not p.purchase_subcontratacion)):
            result = super(StockPicking, self).do_enter_transfer_details(
                cr, uid, picking, context=context)
            return result
        if p.state == 'assigned':
            moves = p.mapped('move_lines').filtered(
                lambda x: x.state == 'assigned' and x.selected_lots)
            move_obj.do_unreserve(cr, uid, moves.ids, context=context)
            opes = p.pack_operation_ids.filtered(lambda x: x.lot_id)
            products = opes.mapped('product_id')
            for product in products:
                my_operations = []
                for ope in p.pack_operation_ids.filtered(
                        lambda x: x.product_id.id == product.id and x.lot_id):
                    my_operations.append(ope)
                my_move = p.move_lines.filtered(
                    lambda x: x.product_id.id == product.id and
                    x.state == 'confirmed')
                if len(my_move) == 0:
                    my_move = p.move_lines.filtered(
                        lambda x: x.product_id.id == product.id and
                        x.state == 'assigned')
                    if len(my_move) == 0:
                        raise exceptions.Warning(
                            _("No se ha encontrado el movimiento para el "
                              "producto: %s") % product.name)
                if len(my_move) > 1:
                    raise exceptions.Warning(
                        _("Se ha encontrado mas de un movimiento para el "
                          "producto: %s") % product.name)
                for ope in my_operations:
                    if (ope.especial_lot and
                        (ope.reserved_quant_for_especial_lot_ids or
                            ope.free_quant_for_especial_lot_ids)):
                        for q in ope.reserved_quant_for_especial_lot_ids:
                            if (q.reservation_id and
                                    q.reservation_id.state == 'assigned'):
                                move_obj.do_unreserve(
                                    cr, uid, q.reservation_id.ids,
                                    context=context)
                        for q in ope.free_quant_for_especial_lot_ids:
                            if (q.reservation_id and
                                    q.reservation_id.state == 'assigned'):
                                move_obj.do_unreserve(
                                    cr, uid, q.reservation_id.ids,
                                    context=context)
                    vals = {'name': my_move.product_id.name,
                            'lines_qty': 0.0,
                            'move_qty': ope.product_qty}
                    my_context = context.copy()
                    my_context['active_id'] = my_move.id
                    wiz = wiz_obj.create(cr, uid, vals, context=my_context)
                    wiz = wiz_obj.browse(cr, uid, wiz)
                    wiz.quants_lines.unlink()
                    qty_to_found = ope.product_qty
                    if ope.reserved_quant_for_especial_lot_ids:
                        for q in ope.reserved_quant_for_especial_lot_ids:
                            my_qty = 0
                            if qty_to_found > 0 and q.qty <= qty_to_found:
                                qty_to_found -= q.qty
                                my_qty = q.qty
                            else:
                                if qty_to_found > 0 and q.qty > qty_to_found:
                                    my_qty = qty_to_found
                                    qty_to_found = 0
                            if my_qty > 0:
                                vals = {'assign_wizard': wiz.id,
                                        'selected': True,
                                        'qty': my_qty,
                                        'quant': q.id,
                                        'lot_id': ope.lot_id.id,
                                        'location_id': q.location_id.id}
                                line = wiz_line_obj.create(cr, uid, vals)
                    if (qty_to_found > 0 and
                            ope.free_quant_for_especial_lot_ids):
                        for q in ope.free_quant_for_especial_lot_ids:
                            my_qty = 0
                            if qty_to_found > 0 and q.qty <= qty_to_found:
                                qty_to_found -= q.qty
                                my_qty = q.qty
                            else:
                                if qty_to_found > 0 and q.qty > qty_to_found:
                                    my_qty = qty_to_found
                                    qty_to_found = 0
                            if my_qty > 0:
                                vals = {'assign_wizard': wiz.id,
                                        'selected': True,
                                        'qty': my_qty,
                                        'quant': q.id,
                                        'lot_id': ope.lot_id.id,
                                        'location_id': q.location_id.id}
                                line = wiz_line_obj.create(cr, uid, vals)
                    if (not ope.free_quant_for_especial_lot_ids and not
                            ope.free_quant_for_especial_lot_ids):
                        quant = False
                        available_quant = self.pool.get('stock.quant').search(
                            cr, uid, [
                                ('location_id.usage', '=', 'internal'),
                                ('lot_id', '=', ope.lot_id.id),
                                ('location_id', 'child_of',
                                 ope.location_id.id),
                                ('reservation_id', '=', False),
                                ('product_id', '=', ope.product_id.id),
                                ('qty', '>=', ope.product_qty)], limit=1)
                        if available_quant:
                            quant = self.pool.get('stock.quant').browse(
                                cr, uid, available_quant)
                        if quant:
                            vals = {'assign_wizard': wiz.id,
                                    'selected': True,
                                    'qty': ope.product_qty,
                                    'quant': quant.id,
                                    'lot_id': ope.lot_id.id,
                                    'location_id': quant.location_id.id}
                            line = wiz_line_obj.create(cr, uid, vals)
                    quants = []
                    wiz = wiz_obj.browse(cr, uid, wiz.id)
                    for line in wiz.quants_lines:
                        quants.append([line.quant, line.qty])
                    self.pool['stock.quant'].quants_reserve(
                        cr, uid, quants, my_move, context=context)
        if p.state == 'confirmed':
            p.action_assign()
        if p.state in ('confirmed', 'waiting', 'partially_available'):
            p.force_assign()
        if p.state in ('assigned', 'partially_available'):
            for ope in p.pack_operation_ids:
                moves_qty = 0
                moves = ope.picking_id.move_lines.filtered(
                    lambda a: a.product_id.id == ope.product_id.id)
                if moves:
                    moves_qty = sum(moves.mapped('product_uom_qty'))
                opes_qty = 0
                cond = [('id', '!=', ope.id),
                        ('picking_id', '=', ope.picking_id.id),
                        ('product_id', '=', ope.product_id.id)]
                opes_ids = self.pool.get('stock.pack.operation').search(
                    cr, uid, cond)
                if opes_ids:
                    opes = self.pool.get('stock.pack.operation').browse(
                        cr, uid, opes_ids)
                    opes_qty = sum(opes.mapped('product_qty'))
                if (opes_qty + ope.product_qty) > moves_qty:
                    raise exceptions.Warning(
                        _('For the product %s, are needed one amount of %s, '
                          'and in operations have been introduced %s.') %
                        (ope.product_id.name, moves_qty,
                         opes_qty + ope.product_qty))
            result = super(StockPicking, self).do_enter_transfer_details(
                cr, uid, picking, context=context)
            return result

    @api.multi
    def do_transfer(self):
        res = super(StockPicking, self.with_context(
            from_alfredo=True)).do_transfer()
        for picking in self.filtered(lambda c: c.group_id and
                                     c.picking_type_id and
                                     c.picking_type_id.code == 'outgoing'):
            cond = [('procurement_group_id', '=', picking.group_id.id)]
            sale = self.env['sale.order'].search(cond, limit=1)
            if sale and sale.picking_ids:
                pickings = self.env['stock.picking']
                for picking in sale.picking_ids:
                    pickings += picking
                if pickings:
                    sale.out_picking_ids = [(6, 0, pickings.ids)]
        for picking in self.filtered(
                lambda c: c.picking_type_id and
                c.picking_type_id.code == 'incoming'):
            purchases = self.env['purchase.order']
            for move in picking.move_lines.filtered(
                    lambda c: c.purchase_line_id):
                if (move.purchase_line_id.order_id and
                        move.purchase_line_id.order_id not in purchases):
                    purchases += move.purchase_line_id.order_id
            if purchases:
                for purchase in purchases:
                    pickings = self.env['stock.picking']
                    if purchase.picking_ids:
                        for picking in purchases.picking_ids:
                            pickings += picking
                    if pickings:
                        purchase.in_picking_ids = [(6, 0, pickings.ids)]
        return res

    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        for picking in self.filtered(lambda c: c.picking_type_id):
            if picking.picking_type_id.subcontract_operation:
                picking.move_type = 'one'

    @api.onchange('shipping_address_in_pickings')
    def onchange_shipping_address_in_pickings(self):
        domain = {}
        self.ensure_one()
        if self.shipping_address_in_pickings:
            domain = {'domain': {'partner_id': [('type', '=', 'delivery')]}}
        return domain

    @api.model
    def create(self, vals):
        type_obj = self.env['stock.picking.type']
        if 'picking_type_id' in vals and vals.get('picking_type_id', False):
            type = type_obj.browse(vals.get('picking_type_id'))
            if type and type.subcontract_operation:
                vals['move_type'] = 'one'
        return super(StockPicking, self).create(vals)

    @api.multi
    def action_assign(self):
        if self.purchase_subcontratacion:
            result = super(
                StockPicking, self.with_context(
                    no_delete_operations=True)).action_assign()
        else:
            result = super(StockPicking, self).action_assign()
        return result

    @api.multi
    def write(self, values):
        if ('purchase_subcontratacion' in values and
                values.get('purchase_subcontratacion', False)):
            values['move_type'] = 'direct'
        res = super(StockPicking, self).write(values)
        return res

    @api.multi
    def create_all_move_packages(self):
        if 'from_subcontratacion' not in self.env.context:
            return super(StockPicking, self).create_all_move_packages()
        return self.env['stock.pack.operation']

    @api.multi
    def jvv_action_cancel(self):
        wiz_obj = self.env['wiz.cancel.stock.picking']
        wiz = wiz_obj.with_context(
            {'active_id': self.id,
             'active_ids': self.ids,
             'active_model': 'stock.picking'}).create({})
        context = self.env.context.copy()
        context.update({
            'active_id': self.id,
            'active_ids': self.ids,
            'active_model': 'stock.picking',
        })
        return {
            'name': 'Cancelar albarán',
            'type': 'ir.actions.act_window',
            'res_model': 'wiz.cancel.stock.picking',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wiz.id,
            'target': 'new',
            'context': context,
        }

    @api.model
    def _prepare_pack_ops(self, picking, quants, forced_qties):
        result = super(StockPicking, self)._prepare_pack_ops(
            picking, quants, forced_qties)
        if result:
            for line in result:
                lines = picking.move_lines.filtered(
                    lambda x: x.product_id.id == line.get('product_id') and
                    x.location_dest_id.id == line.get('location_dest_id') and
                    x.location_id == line.get('location_id') and
                    x.product_uom_qty == line.get('product_qty'))
                if lines and len(lines) == 1:
                    if lines.date_expected_without_hour:
                        line['date_expected'] = lines.date_expected_without_hour
        return result


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends('procurement_id', 'procurement_id.sale_line_id',
                 'procurement_id.sale_line_id.committed_date')
    def _compute_committed_date(self):
        for move in self.filtered(lambda c: c.procurement_id and
                                  c.procurement_id.sale_line_id):
            move.committed_date = (
                move.procurement_id.sale_line_id.committed_date)

    @api.multi
    @api.depends('picking_id', 'picking_id.picking_type_id',
                 'picking_id.partner_id', 'product_id',
                 'product_id.supplier_ids', 'product_id.customer_ids')
    def _compute_partner_product_code(self):
        for move in self.filtered(lambda c: c.picking_id and
                                  c.picking_type_id):
            line = False
            if move.picking_type_id.code == 'incoming':
                line = move.product_id.supplier_ids.filtered(
                    lambda c: c.name.id == move.picking_id.partner_id.id)
            if move.picking_type_id.code == 'outgoing':
                line = move.product_id.customer_ids.filtered(
                    lambda c: c.name.id == move.picking_id.partner_id.id)
            if line and len(line) == 1:
                move.partner_product_code = line.product_code
            if line and len(line) > 1:
                move.partner_product_code = line[0].product_code

    @api.multi
    @api.depends('purchase_line_id', 'purchase_line_id.order_id',
                 'purchase_line_id.order_id.mrp_production_product_id')
    def _compute_production_product_id(self):
        for move in self.filtered(lambda c: c.purchase_line_id):
            product = move.purchase_line_id.order_id.mrp_production_product_id
            if product:
                move.production_product_id = product.id

    @api.multi
    @api.depends('product_id', 'product_id.route_ids',
                 'product_id.route_ids.assemtronic_product')
    def _compute_assemtronic_product(self):
        for move in self.filtered(
                lambda c: c.product_id and c.product_id.route_ids):
            assemtronic_product = False
            if any(p.assemtronic_product for p in move.product_id.route_ids):
                assemtronic_product = True
            move.assemtronic_product = assemtronic_product

    def _compute_lots_description(self):
        for move in self:
            desc = ''
            desc_bin = ''
            for lot in move.lot_ids:
                desc = (lot.name if not desc else
                        u"{}, {}".format(desc, lot.name))
                if lot.ref:
                    desc_bin = (
                        lot.ref if not desc_bin else u"{}, {}".format(
                            desc_bin, lot.ref))
            if desc:
                move.lots_description = desc
            if desc_bin:
                move.bins_description = desc_bin

    committed_date = fields.Boolean(
        string='Committed date', compute='_compute_committed_date', store=True)
    product_internal_reference = fields.Char(
        string='Internal reference', related='product_id.default_code',
        store=True)
    partner_product_code = fields.Char(
        string='Partner product code', store=True,
        compute='_compute_partner_product_code')
    serial_numbers = fields.Text(
        string='Serial numbers', copy=False)
    production_product_id = fields.Many2one(
        string='Product to produce', comodel_name='product.product',
        compute='_compute_production_product_id', store=True)
    inventory_description = fields.Char(
        string='Inventory description')
    notes2 = fields.Text(string='Notes 2', translate=True)
    sale_id = fields.Many2one(
        string='Sale order', commodel_name='sale.order',
        related='production_id.sale_id', store=True)
    assemtronic_product = fields.Boolean(
        string='Assemtronic product', compute='_compute_assemtronic_product',
        store=True)
    lots_description = fields.Char(
        string='Lots', compute='_compute_lots_description')
    bins_description = fields.Char(
        string='BINs', compute='_compute_lots_description')
    bar_code_status = fields.Selection(
        string="Reader bar code status", selection=[
            ('no', _('No control')),
            ('nocompleted', 'No completed'),
            ('completed', 'Completed'),
        ], compute='_compute_bar_code_status', store=True)
    qty_available_not_res = fields.Float(
        string='Qty Available Not Reserved',
        digits=dp.get_precision('Product Unit of Measure'),
        related='product_tmpl_id.qty_available_not_res')
    qty_available = fields.Float(
        string='Quantity On Hand',
        digits=dp.get_precision('Product Unit of Measure'),
        related='product_tmpl_id.qty_available')
    immediately_usable_qty = fields.Float(
        digits=dp.get_precision('Product Unit of Measure'),
        string='No reserved',
        related='product_tmpl_id.immediately_usable_qty')
    qty_locked = fields.Float(
        string="Cantidad bloqueada",
        related="product_id.qty_locked")
    lot_locked_ids = fields.Many2many(
        string="Lotes bloqueados", comodel_name="stock.production.lot",
        relation="rel_stock_move_locked_lot",
        column1="move_id", column2="lot_id",
        compute="_compute_qty_lot_locked")

    def _compute_qty_lot_locked(self):
        for move in self:
            lots_locked = self.env["stock.production.lot"]
            if move.product_id and move.product_id.stock_quant_ids:
                quants = move.product_id.stock_quant_ids.filtered(
                    lambda x: x.locked and x.location_id.usage == "internal")
                if quants:
                    for quant in quants:
                        if quant.lot_id and quant.lot_id not in lots_locked:
                            lots_locked += quant.lot_id
            move.lot_locked_ids = [(6, 0, lots_locked.ids)]

    @api.multi
    @api.depends('reserved_quant_ids', 'reserved_quant_ids.lot_id',
                 'reserved_quant_ids.qty',
                 'picking_id', 'picking_id.purchase_subcontratacion',
                 'picking_id.pack_operation_ids',
                 'picking_id.pack_operation_ids.product_lot_from_barcode',
                 'picking_id.pack_operation_ids.product_id',
                 'picking_id.pack_operation_ids.lot_id',
                 'picking_id.pack_operation_ids.product_qty',)
    def _compute_bar_code_status(self):
        for move in self.filtered(lambda c: not c.picking_id or
                                  (c.picking_id and not
                                   c.picking_id.purchase_subcontratacion)):
            move.bar_code_status = 'no'
        for move in self.filtered(lambda c: c.picking_id and
                                  c.picking_id.purchase_subcontratacion):
            if move.product_id.type != 'consu':
                if (not move.reserved_quant_ids or not
                        move.picking_id.pack_operation_ids):
                    move.bar_code_status = 'nocompleted'
            else:
                if move.lot_ids:
                    move.bar_code_status = 'nocompleted'
                else:
                    move.product_uom_qty
                    operations = move.picking_id.pack_operation_ids.filtered(
                        lambda c: c.product_id.id == move.product_id.id and
                        not c.lot_id)
                    if not operations:
                        move.bar_code_status = 'nocompleted'
                    else:
                        if (move.product_uom_qty ==
                                sum(operations.mapped('product_qty'))):
                            move.bar_code_status = 'completed'
                        else:
                            move.bar_code_status = 'nocompleted'
            if move.reserved_quant_ids:
                quantkey = {}
                for quant in move.reserved_quant_ids:
                    key = 'sinlote' if not quant.lot_id else quant.lot_id.name
                    if key not in quantkey:
                        quantkey[key] = quant.qty
                    else:
                        quantkey[key] += quant.qty
                for key in quantkey.keys():
                    quantity = float(quantkey.get(key))
                    pack_operation_ids = move.picking_id.pack_operation_ids
                    if key == 'sinlote':
                        operations = pack_operation_ids.filtered(
                            lambda c: c.product_id.id == move.product_id.id and
                            not c.lot_id)
                    else:
                        operations = pack_operation_ids.filtered(
                            lambda c: c.product_id.id == move.product_id.id and
                            c.lot_id and c.lot_id.name == key)
                    if (not operations or
                        (operations and quantity != sum(
                            operations.mapped('product_qty')))):
                        move.bar_code_status = 'nocompleted'
                    else:
                        move.bar_code_status = 'completed'

    @api.model
    def create(self, values):
        production_obj = self.env['mrp.production']
        if ('purchase_line_id' in values and
                values.get('purchase_line_id', False)):
            line = self.env['purchase.order.line'].browse(
                values.get('purchase_line_id'))
            if line and line.notes2:
                values['notes2'] = line.notes2
        if 'procurement_id' in values and values.get('procurement_id', False):
            proc = self.env['procurement.order'].browse(
                values.get('procurement_id'))
            if proc and proc.sale_line_id and proc.sale_line_id.notes2:
                values['notes2'] = proc.sale_line_id.notes2
        if ('raw_material_production_id' in values and
                values.get('raw_material_production_id', False)):
            production = production_obj.browse(
                values.get('raw_material_production_id'))
            if production and production.sale_order:
                values['sale_id'] = production.sale_order.id
        return super(StockMove, self).create(values)

    @api.multi
    def write(self, values):
        production_obj = self.env['mrp.production']
        if ('purchase_line_id' in values and
                values.get('purchase_line_id', False)):
            line = self.env['purchase.order.line'].browse(
                values.get('purchase_line_id'))
            if line and line.notes2:
                values['notes2'] = line.notes2
        if 'procurement_id' in values and values.get('procurement_id', False):
            proc = self.env['procurement.order'].browse(
                values.get('procurement_id'))
            if proc and proc.sale_line_id and proc.sale_line_id.notes2:
                values['notes2'] = proc.sale_line_id.notes2
        if ('raw_material_production_id' in values and
                values.get('raw_material_production_id', False)):
            production = production_obj.browse(
                values.get('raw_material_production_id'))
            if production and production.sale_order:
                values['sale_id'] = production.sale_order.id
        return super(StockMove, self).write(values)

    @api.model
    def _get_invoice_line_vals(self, move, partner, inv_type):
        vals = super(StockMove, self)._get_invoice_line_vals(
            move, partner, inv_type)
        if move.serial_numbers:
            vals['serial_numbers'] = move.serial_numbers
        return vals


class StockPackOperation(models.Model):
    _inherit = "stock.pack.operation"
    _order = "product_id"

    product_lot_from_barcode = fields.Char(string='Barcode reader')
    created_from_barcode = fields.Boolean(
        string='Created from barcorde readeer', default=False)
    product_qty_lot = fields.Float(
        string='Quantity',
        digits_compute=dp.get_precision('Product Unit of Measure'))
    product_qty_in_lot = fields.Float(
        string='Total quantity in lot NOT RESERVED')
    product_qty_in_lot2 = fields.Float(
        string='Total quantity in lot NOT RESERVED')
    product_qty_available_not_res = fields.Float(
        string='Total quantity NOT RESERVED in product',
        digits_compute=dp.get_precision('Product Unit of Measure'),
        related='product_id.qty_available_not_res')
    especial_lot = fields.Boolean(
        string='Lote especial', default=False)
    reserved_quant_for_especial_lot_ids = fields.Many2many(
        string='Reserved quant para lote especial', comodel_name='stock.quant',
        relation="rel_ope_operation_quant_reserved",
        column1="operation_id", column2="quant_id")
    free_quant_for_especial_lot_ids = fields.Many2many(
        string='Free quant para lote especial', comodel_name='stock.quant',
        relation="rel_ope_especial_quant_free",
        column1="operation_id", column2="quant_id")
    date_expected = fields.Date(string="Fecha prevista")

    @api.onchange('product_lot_from_barcode')
    def onchange_product_lot_from_barcode(self):
        if self.product_lot_from_barcode:
            especial_lot = False
            cond = [('default_code', '=', self.product_lot_from_barcode)]
            pos = self.product_lot_from_barcode.find(" ")
            if pos > 0:
                default_code = self.product_lot_from_barcode[0:pos]
                cond = [('default_code', '=', default_code)]
            product = self.env['product.product'].search(cond, limit=1)
            if not product:
                raise exceptions.Warning(_('Product not found'))
            if product:
                self.product_id = product.id
            lot = False
            if pos > 0:
                name = self.product_lot_from_barcode[
                    pos+1:len(self.product_lot_from_barcode)]
                cond = [('name', '=', name),
                        ('product_id', '=', product.id)]
                lot = self.env['stock.production.lot'].search(cond, limit=1)
                if not lot:
                    raise exceptions.Warning(_('Lot not exist.'))
            if lot:
                self.lot_id = lot.id
            if lot:
                move = self.picking_id.move_lines.filtered(
                    lambda l: l.product_id.id == product.id and
                    lot.name in l.selected_lots)
            else:
                moves = self.picking_id.move_lines.filtered(
                    lambda l: l.product_id.id == product.id)
                move = False
                for m in moves:
                    for quant in m.reserved_quant_ids.filtered(
                        lambda l: l.product_id.id == product.id and not
                            l.lot_id):
                        move = m
                        break
            if not move and not lot and product.type != 'consu':
                raise exceptions.Warning(
                    _('Product without lot not found in picking'))
            quants = False
            if lot and move:
                quants = move.reserved_quant_ids.filtered(
                    lambda l: l.product_id.id == product.id and
                    l.lot_id.id == lot.id)
            elif lot and not move:
                quants = False
            else:
                if move:
                    quants = move.reserved_quant_ids.filtered(
                        lambda l: l.product_id.id == product.id and not
                        l.lot_id)
            quants2 = False
            qty_from_especial_lot = 0.0
            pending_qty = 0.0
            reserved_quants = self.env['stock.quant']
            free_quants = self.env['stock.quant']
            if lot and move:
                cond = [('location_id.usage', '=', 'internal'),
                        ('product_id', '=', product.id),
                        ('reservation_id', '=', move.id),
                        ('lot_id', '=', lot.id)]
                quants2 = self.env['stock.quant'].search(cond)
            if lot and not move:
                especial_lot = True
                qty_moves = self.picking_id.move_lines.filtered(
                    lambda l: l.product_id.id == product.id)
                qty_from_especial_lot = sum(
                    qty_moves.mapped('product_uom_qty'))
                if 'default_picking_id' in self.env.context:
                    picking = self.env['stock.picking'].browse(
                        self.env.context.get('default_picking_id'))
                    operations = picking.pack_operation_ids.filtered(
                        lambda l: l.product_id.id == product.id and
                        l.product_lot_from_barcode !=
                        self.product_lot_from_barcode)
                    if operations:
                        qty_operations = sum(
                            operations.mapped('product_qty'))
                        qty_from_especial_lot -= qty_operations
                pending_qty, quants2, reserved_quants, free_quants = (
                    self.search_new_quant_for_new_lot(
                        product, lot, qty_from_especial_lot))
            if not quants and not lot and product.type != 'consu':
                raise exceptions.Warning(
                    _('Quant not fount for introduce product.'))
            if (not quants and lot and not quants2 and
                    qty_from_especial_lot == pending_qty):
                raise exceptions.Warning(
                    _('Quant not found for introduced product/lot.'))
            self.created_from_barcode = True
            if quants2:
                qty = sum(quants2.mapped('qty'))
                self.product_qty_in_lot = qty
                self.product_qty_in_lot2 = qty
                if especial_lot:
                    if reserved_quants:
                        self.reserved_quant_for_especial_lot_ids = [
                            (6, 0, reserved_quants.ids)]
                    if free_quants:
                        self.free_quant_for_especial_lot_ids = [
                            (6, 0, free_quants.ids)]
                    if (self.product_qty > 0 and qty > qty_from_especial_lot):
                        self.product_qty = qty_from_especial_lot
                    else:
                        if self.product_qty == 0:
                            if pending_qty == 0:
                                if qty > qty_from_especial_lot:
                                    self.product_qty = qty_from_especial_lot
                                else:
                                    self.product_qty = qty
                            else:
                                self.product_qty = qty_from_especial_lot - pending_qty
            if quants:
                if not especial_lot:
                    self.product_qty = sum(quants.mapped('qty'))
            if (move and move.reserved_quant_ids and
                len(move.reserved_quant_ids) == 1 and not lot and
                    quants and not quants2):
                self.location_id = move.reserved_quant_ids[0].location_id.id
            if lot and not move and not quants and quants2:
                self.location_id = quants2[0].location_id.id
            if product.type == 'consu' and not lot and len(moves) == 1:
                self.product_qty = moves[0].product_uom_qty
                cond = [('product_id', '=', product.id),
                        ('location_id.usage', '=', 'internal')]
                myquant = self.env['stock.quant'].search(cond, limit=1)
                if myquant:
                    self.location_id = myquant.location_id.id
            self.especial_lot = especial_lot

    def search_new_quant_for_new_lot(self, product, lot, qty_to_found):
        my_qty_to_found = qty_to_found
        quant_obj = self.env['stock.quant']
        reserved_quants = self.env['stock.quant']
        free_quants = self.env['stock.quant']
        cond = [('location_id.usage', '=', 'internal'),
                ('product_id', '=', product.id),
                ('reservation_id', '!=', False),
                ('lot_id', '=', lot.id),
                ('reserved_quant_for_especial_lot_ids', '=', False),
                ('free_quant_for_especial_lot_ids', '=', False)]
        quants = self.env['stock.quant'].search(cond)
        for quant in quants:
            if qty_to_found > 0 and quant.qty <= qty_to_found:
                reserved_quants += quant
                qty_to_found -= quant.qty
            else:
                if qty_to_found > 0 and quant.qty > qty_to_found:
                    reserved_quants += quant
                    qty_to_found = 0
            if qty_to_found == 0:
                break
        if qty_to_found > 0:
            cond = [('location_id.usage', '=', 'internal'),
                    ('product_id', '=', product.id),
                    ('reservation_id', '=', False),
                    ('lot_id', '=', lot.id),
                    ('reserved_quant_for_especial_lot_ids', '=', False),
                    ('free_quant_for_especial_lot_ids', '=', False)]
            quants = self.env['stock.quant'].search(cond)
            for quant in quants:
                if qty_to_found > 0 and quant.qty <= qty_to_found:
                    free_quants += quant
                    qty_to_found -= quant.qty
                else:
                    if qty_to_found > 0 and quant.qty > qty_to_found:
                        free_quants += quant
                        qty_to_found = 0
                if qty_to_found == 0:
                    break
        if qty_to_found > 0 and qty_to_found == my_qty_to_found:
            return quant_obj, quant_obj, quant_obj
        else:
            total_quants = reserved_quants + free_quants
            return qty_to_found, total_quants, reserved_quants, free_quants

    @api.onchange('product_qty')
    def onchange_product_qty(self):
        for operation in self:
            if (operation.picking_id.purchase_subcontratacion and
                operation.product_qty > operation.product_qty_lot and
                    operation.product_qty_lot > 0):
                operation.product_qty = operation.product_qty_lot
                raise exceptions.Warning(
                    _("Amount has been exceeded, maximum quantity: %s") %
                    operation.product_qty_lot)

    @api.onchange('lot_id')
    def onchange_lot_id(self):
        for operation in self.filtered(lambda x: x.lot_id):
            if (operation.picking_id.purchase_subcontratacion and
                    operation.lot_id.quant_ids):
                quants = operation.lot_id.mapped('quant_ids').filtered(
                    lambda l: l.product_id == operation.product_id and
                    l.qty == operation.product_qty and
                    l.location_id.usage == 'internal')
                if quants:
                    locations = quants.mapped('location_id')
                    if len(locations) == 1:
                        operation.location_id = locations.id
                    else:
                        operation.location_id = locations[0].id
            else:
                if (operation.picking_id.purchase_subcontratacion and
                    operation.product_id and
                        operation.product_id.type == 'consu'):
                    cond = [('product_id', '=', operation.product_id.id)]
                    myquant = self.env['stock.quant'].search(cond, limit=1)
                    if myquant:
                        operation.location_id = myquant.location_id.id

    @api.multi
    def unlink(self):
        result = True
        if 'no_delete_operations' not in self.env.context:
            result = super(StockPackOperation, self).unlink()
        return result

    @api.model
    def create(self, values):
        if ('product_qty_in_lot2' in values and
                values.get('product_qty_in_lot2', False)):
            values['product_qty_in_lot'] = values.get('product_qty_in_lot2')
        operation = super(StockPackOperation, self).create(values)
        if (operation.picking_id and not
            operation.picking_id.purchase_subcontratacion and not
                operation.date_expected):
            move = operation.picking_id.move_lines.filtered(
                lambda x: x.product_id == operation.product_id and
                x.location_id == operation.location_id and
                x.location_dest_id == operation.location_dest_id and
                x.product_qty == operation.product_qty)
            if len(move) == 1 and move.date_expected:
                operation.date_expected = move.date_expected
        return operation

    @api.multi
    def write(self, values):
        if ('product_qty_in_lot2' in values and
                values.get('product_qty_in_lot2', False)):
            values['product_qty_in_lot'] = values.get('product_qty_in_lot2')
        return super(StockPackOperation, self).write(values)


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    @api.multi
    def action_done(self):
        result = super(StockInventory, self).action_done()
        for inventory in self:
            if inventory.move_ids:
                inventory.move_ids.write(
                    {'inventory_description': inventory.name})
        return result


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    shipping_address_in_pickings = fields.Boolean(
        string='Request shipping address in pickings', default=False)
    subcontract_operation = fields.Boolean(
        string='It is subcontract operation', default=False)
