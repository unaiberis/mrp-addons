# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import fields, models


class MrpRepairCustomerLot(models.Model):
    _inherit = "mrp.repair.customer.lot"

    serial_number = fields.Char(string="Serial number")
    quantity_2_digits = fields.Float(
        string="Quantity",
        compute="_compute_quantity_2_digits",
        digits="Discount",
    )

    def _compute_quantity_2_digits(self):
        for line in self:
            line.quantity_2_digits = line.quantity


class MrpRepairLine(models.Model):
    _inherit = "mrp.repair.line"

    product_uom_qty_2_digits = fields.Float(
        string="Quantity",
        compute="_compute_product_uom_qty_2_digits",
        digits="Discount",
    )

    def _compute_product_uom_qty_2_digits(self):
        for line in self:
            line.product_uom_qty_2_digits = line.product_uom_qty


class MrpRepairFee(models.Model):
    _inherit = "mrp.repair.fee"

    product_uom_qty_2_digits = fields.Float(
        string="Quantity",
        compute="_compute_product_uom_qty_2_digits",
        digits="Discount",
    )

    def _compute_product_uom_qty_2_digits(self):
        for line in self:
            line.product_uom_qty_2_digits = line.product_uom_qty
