# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import api, models


class CrmMakeSale(models.TransientModel):
    _inherit = "crm.make.sale"

    def makeOrder(self):
        oport_obj = self.env["crm.lead"]
        result = super().makeOrder()
        oport_ids = self.env.context.get("active_ids", [])
        for oport in oport_obj.browse(oport_ids).filtered(
            lambda c: c.offer_number and c.ref and str(c.ref._model) == "sale.order"
        ):
            oport.ref.write(
                {"offer_number": oport.offer_number, "opportunity_id": oport.id}
            )
            self._transfer_attachments_from_opportunity_to_sale_order(oport, oport.ref)
        return result

    def _transfer_attachments_from_opportunity_to_sale_order(self, oport, sale):
        attachment_obj = self.env["ir.attachment"]
        cond = [("res_model", "=", "crm.lead"), ("res_id", "=", oport.id)]
        attachments = attachment_obj.search(cond)
        attachments.copy({"res_model": "sale.order", "res_id": sale.id})
        cond = [("res_model", "=", "sale.order"), ("res_id", "=", sale.id)]
        attachments = attachment_obj.search(cond)
        for attachment in attachments:
            attachment.name = attachment.name.replace(" (copia)", "")
