# Copyright 2022 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp.osv import osv


class procurement_order(osv.osv):
    _inherit = "procurement.order"

    def _get_po_line_values_from_proc(
        self, cr, uid, procurement, partner, company, schedule_date, context=None
    ):
        if context is None:
            context = {}
        warn_product = False
        warn_partner = False
        if (
            procurement
            and procurement.product_id
            and procurement.product_id.variant_seller_ids
            and partner
        ):
            for line in procurement.product_id.variant_seller_ids:
                if line.name == partner:
                    if not partner.is_company:
                        error = "'El producto: {}, con proveedor: {}, y dicho proveedor no es compañía.".format(
                            procurement.product_id.name, partner.name
                        )
                        raise osv.except_osv("Error!", error)
                    if partner.purchase_warn:
                        if partner.purchase_warn == "block":
                            error = "'El proveedor: {}, tiene un aviso de bloqueo para las compras.".format(
                                partner.name
                            )
                            raise osv.except_osv("Error!", error)
                        else:
                            warn_partner = partner.purchase_warn
                            partner.purchase_warn = "no-message"
        if procurement and procurement.product_id:
            if procurement.product_id.purchase_line_warn:
                if procurement.product_id.purchase_line_warn == "block":
                    error = "'El producto: {}, tiene un aviso de bloqueo para las compras.".format(
                        procurement.product_id.name
                    )
                    raise osv.except_osv("Error!", error)
                else:
                    warn_product = procurement.product_id.purchase_line_warn
                    procurement.product_id.purchase_line_warn = "no-message"
        result = super()._get_po_line_values_from_proc(
            cr, uid, procurement, partner, company, schedule_date, context=context
        )
        if procurement and procurement.product_id and warn_product:
            procurement.product_id.purchase_line_warn = warn_product
        if partner and warn_partner:
            partner.purchase_warn = warn_partner
        return result
