# Copyright 2024 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models


class WizChangeSerialNumbers(models.TransientModel):
    _name = "wiz.change.serial.numbers"

    move_id = fields.Many2one(string="Movimiento", comodel_name="stock.move")
    old_serial_numbers = fields.Text(string="Números de serie actuales", copy=False)
    new_serial_numbers = fields.Text(string="Nuevos números de serie", copy=False)

    @api.model
    def default_get(self, var_fields):
        result = super().default_get(var_fields)
        move = self.env["stock.move"].browse(self.env.context.get("active_id", []))
        result["move_id"] = move.id
        if move.serial_numbers:
            result["old_serial_numbers"] = move.serial_numbers
            result["new_serial_numbers"] = move.serial_numbers
        return result

    def change_serial_numbers(self):
        self.move_id.serial_numbers = self.new_serial_numbers
        if (
            self.move_id.sale_id
            and self.move_id.production_id
            and self.move_id.production_id.sale_line_id
        ):
            cond = [
                ("sale_order_line", "=", self.move_id.production_id.sale_line_id.id),
                ("product_uom_qty", "=", self.move_id.product_uom_qty),
            ]
            move2 = self.env["stock.move"].search(cond, limit=1)
            if move2:
                move2.serial_numbers = self.new_serial_numbers
