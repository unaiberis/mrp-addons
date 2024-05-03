# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, api, fields


class ProcurementPlan(models.Model):
    _inherit = 'procurement.plan'

    client_order_ref = fields.Char(
        string="Referencia cliente", store=True, copy=False,
        compute="_compute_client_order_ref")
    customer_product_code = fields.Char(
        string='Código producto cliente', store=True, copy=False,
        related="sale_line_id.customer_product_code")

    @api.depends("sale_line_id", "sale_line_id.order_id",
                 "sale_line_id.order_id.client_order_ref")
    def _compute_client_order_ref(self):
        for plan in self:
            client_order_ref = ""
            if (plan.sale_line_id and plan.sale_line_id.order_id and
                    plan.sale_line_id.order_id.client_order_ref):
                client_order_ref = plan.sale_line_id.order_id.client_order_ref
            plan.client_order_ref = client_order_ref
