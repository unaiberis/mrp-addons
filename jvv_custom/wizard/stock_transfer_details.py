# Copyright 2020 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
import openerp.addons.decimal_precision as dp
from openerp import _, api, fields, models


class StockTransferDetails(models.TransientModel):
    _inherit = "stock.transfer_details"

    @api.model
    def default_get(self, fields):
        picking_ids = self.env.context.get("active_ids", [])
        self.env.context.get("active_model")
        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return super().default_get(fields)
        picking = self.env["stock.picking"].browse(picking_ids)
        if not picking.purchase_subcontratacion:
            res = super().default_get(fields)
        else:
            res = super(
                StockTransferDetails, self.with_context(from_subcontratacion=True)
            ).default_get(fields)
        if "item_ids" in res and res.get("item_ids", False):
            for line in res.get("item_ids"):
                if "packop_id" in line and line.get("packop_id", False):
                    pack = self.env["stock.pack.operation"].browse(
                        line.get("packop_id")
                    )
                    if pack.date_expected:
                        line["date_expected"] = pack.date_expected
        if not picking.purchase_subcontratacion:
            return res
        if not "item_ids" in res or not res.get("item_ids", False):
            return res
        item_ids2 = []
        item_ids = res.get("item_ids")
        for item in item_ids:
            if "packop_id" in item and item.get("packop_id", False):
                packop = self.env["stock.pack.operation"].browse(item.get("packop_id"))
                if packop.created_from_barcode:
                    item_ids2.append(item)
                else:
                    packop.unlink()
        res["item_ids"] = item_ids2
        return res


class StockTransferDetailsItems(models.TransientModel):
    _inherit = "stock.transfer_details_items"

    operation_quantity = fields.Float(
        string="Operation Quantity",
        related="packop_id.product_qty",
        digits=dp.get_precision("Product Unit of Measure"),
    )
    operation_picking_id = fields.Many2one(
        string="Operation picking",
        comodel_name="stock.picking",
        related="packop_id.picking_id",
    )
    date_expected = fields.Date(string="Fecha prevista")
    manufacturer_id = fields.Char(string="ID Manufacturer", copy=False)

    @api.onchange("quantity")
    def onchange_quantity(self):
        if self.quantity and self.operation_picking_id.purchase_subcontratacion:
            if self.quantity != self.operation_quantity:
                self.quantity = self.operation_quantity
                return {
                    "warning": {
                        "title": _("Quantity error"),
                        "message": _(
                            "Cannot exceed quantity defined in "
                            "operation by barcode reader."
                        ),
                    }
                }
        return {}

    @api.onchange("manufacturer_id")
    def onchange_manufacturer_id(self):
        if self.lot_id:
            if self.manufacturer_id:
                self.lot_id.manufacturer_id = self.manufacturer_id
            else:
                self.lot_id.manufacturer_id = ""
