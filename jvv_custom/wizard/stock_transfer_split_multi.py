# -*- coding: utf-8 -*-
# Copyright 2020 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, fields, api


class StockTransferSplitMulti(models.TransientModel):
    _inherit = 'stock.transfer.split.multi'

    manufacturer_id = fields.Char(
        string="ID Manufacturer", copy=False)

    @api.multi
    def split_multi_quantities(self):
        self.ensure_one()
        if self[0].lot_id_auto and self[0].manufacturer_id:
            trf_line = self.env['stock.transfer_details_items'].browse(
                self.env.context['active_id'])
            trf_line.manufacturer_id = self[0].manufacturer_id
            return super(
                StockTransferSplitMulti, self.with_context(
                    default_manufacturer_id=self[0].manufacturer_id)).split_multi_quantities()
        return super(StockTransferSplitMulti, self). split_multi_quantities()
