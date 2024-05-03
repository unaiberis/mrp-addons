# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import api, fields, models


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    my_counter = fields.Integer(string="Numeración", readonly="1")

    @api.model
    def create(self, values):
        bom_line = super().create(values)
        bom = max(bom_line.bom_id.bom_line_ids, key=lambda x: x.my_counter)
        bom_line.my_counter = bom.my_counter + 1
        return bom_line

    @api.multi
    def automatic_put_consumido_en_in_bom_lines(self):
        cond = [("operation", "=", False)]
        lines = self.search(cond)
        for line in lines:
            cond = [
                ("product_id", "=", line.product_id.id),
                ("raw_material_production_id", "!=", False),
                (
                    "raw_material_production_id.product_tmpl_id",
                    "=",
                    line.bom_id.product_tmpl_id.id,
                ),
                ("work_order", "!=", False),
                ("work_order.routing_wc_line", "!=", False),
            ]
            moves = self.env["stock.move"].search(cond)
            if moves:
                work_order = 0
                my_id = 0
                for move in moves:
                    if my_id == 0 or move.id > my_id:
                        my_id = move.id
                        work_order = move.work_order.routing_wc_line.id
                line.operation = work_order
            self.env.cr.commit()
