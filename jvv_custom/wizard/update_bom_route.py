# Copyright 2019 Daniel Campos - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, api, fields, models


class UpdateBomRoute(models.TransientModel):
    _name = "update.bom.route"

    message = fields.Char(string="Response", readonly=True)

    def update_bom_route(self):
        update_ids = self.env.context.get("active_ids")
        update_num = 0
        bom_obj = self.env["mrp.bom"]
        for bom_id in update_ids:
            bom = bom_obj.browse(bom_id)
            if bom.product_tmpl_id.prefix_code and bom.routing_id:
                update_num += 1
                route = bom.routing_id.copy(
                    {
                        "name": "{}_{}".format(
                            bom.routing_id.name, bom.product_tmpl_id.prefix_code
                        )
                    }
                )
                if route:
                    bom.routing_id = route.id
                    bom.onchange_routing_id()
        view_id = self.env.ref("jvv_custom.update_bom_done_view").id
        return {
            "type": "ir.actions.act_window",
            "res_model": "update.bom.route",
            "view_mode": "form",
            "view_type": "form",
            "target": "new",
            "name": _("Message"),
            "view_id": view_id,
            "context": {"default_message": "{} BoM updated!".format(update_num)},
        }
