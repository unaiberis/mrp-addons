# -*- coding: utf-8 -*-
# Copyright 2020 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, fields, api


class AssignManualQuants(models.TransientModel):
    _inherit = 'assign.manual.quants'

    @api.model
    def default_get(self, var_fields):
        result = super(AssignManualQuants, self).default_get(var_fields)
        quants_lines = []
        if 'quants_lines' in result:
            quants_lines = result.get('quants_lines', [])
            if quants_lines == None:
                quants_lines = []
        for line in quants_lines:
            if 'location_id' in line and line.get('location_id', 0):
                location = self.env['stock.location'].browse(
                    line.get('location_id'))
                line['location_name'] = location.name
        return result

    @api.multi
    def assign_quants(self):
        move = self.env['stock.move'].browse(self.env.context['active_id'])
        if move.picking_id.purchase_subcontratacion:
            return super(
                AssignManualQuants,
                self.with_context(no_delete_operations=True)).assign_quants()
        return super(AssignManualQuants, self).assign_quants()


class AssignManualQuantsLines(models.TransientModel):
    _inherit = 'assign.manual.quants.lines'
    _order = 'location_name, in_date asc'

    location_name = fields.Char(
        string='Location')
