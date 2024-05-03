# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, api, fields


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    num_lines = fields.Integer(
        string="Num. Líneas", compute="_compute_num_lines", copy=False,
        store=True)

    @api.depends('bom_line_ids')
    def _compute_num_lines(self):
        for bom in self:
            bom.num_lines = len(bom.bom_line_ids)

    @api.multi
    def automatic_numeration_ldm(self):
        boms = self.env['mrp.bom'].search([])
        for bom in boms:
            line_contador = 0
            for line in bom.bom_line_ids:
                line_contador += 1
                line.my_counter = line_contador
            self.env.cr.commit()
