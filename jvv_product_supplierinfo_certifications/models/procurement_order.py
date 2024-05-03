# -*- coding: utf-8 -*-
# Copyright 2023 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import api, models, fields


class ProcuremenOrder(models.Model):
    _inherit = "procurement.order"

    @api.multi
    @api.depends("partner_id", "product_id",
                 "product_id.supplier_ids",
                 "product_id.supplier_ids.name",
                 "product_id.supplier_ids.name.certification_id")
    def _compute_certification_id(self):
        for proc in self:
            certification_id = self.env["product.supplierinfo.certification"]
            if proc.product_id and proc.partner_id:
                lines = proc.product_id.supplier_ids.filtered(
                    lambda x: x.name.id == proc.partner_id.id)
                line = False
                if lines and len(lines) == 1:
                    line = lines
                if lines and len(lines) > 1:
                    line = min(lines, key=lambda x: x.sequence)
                if line and line.name.certification_id:
                    certification_id = line.name.certification_id.id
            proc.certification_id = certification_id

    certification_id = fields.Many2one(
        string="Calificación proveedor",
        comodel_name="product.supplierinfo.certification",
        compute="_compute_certification_id", copy=False,
        store=True)
