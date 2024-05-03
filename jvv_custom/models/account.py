# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import _, api, exceptions, fields, models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.depends("picking_ids")
    def _compute_sale_order_ids(self):
        for invoice in self.filtered(lambda l: l.type == "out_invoice"):
            sales = self.env["sale.order"]
            for picking in invoice.picking_ids:
                if picking.sale_id not in sales:
                    sales += picking.sale_id
            invoice.sale_order_ids = [(6, 0, sales.ids)]

    @api.depends("picking_ids")
    def _compute_purchase_order_ids(self):
        for invoice in self.filtered(lambda l: l.type == "in_invoice"):
            purchases = self.env["purchase.order"]
            for picking in invoice.picking_ids:
                if picking.purchase_id not in purchases:
                    purchases += picking.purchase_id
            invoice.purchase_order_ids = [(6, 0, purchases.ids)]

    @api.depends("name")
    def _compute_mrp_repair_id(self):
        repair_obj = self.env["mrp.repair"]
        for invoice in self.filtered(lambda l: l.name):
            cond = [("name", "=", invoice.name)]
            repair = repair_obj.search(cond, limit=1)
            if repair:
                invoice.mrp_repair_id = repair.id

    def _compute_delivery_address_id(self):
        for invoice in self.filtered(lambda l: l.partner_id):
            partner = (
                invoice.partner_id
                if not invoice.partner_id.parent_id
                else invoice.partner_id.parent_id
            )
            if partner.child_ids:
                p = partner.mapped("child_ids").filtered(lambda l: l.type == "delivery")
                if p:
                    if len(p) == 1:
                        invoice.delivery_address_id = p.id
                    else:
                        invoice.delivery_address_id = p[0].id

    sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        relation="rel_account_invoice_sale_order",
        column1="invoice_id",
        column2="sale_id",
        string="Sale orders",
        copy=False,
        compute="_compute_sale_order_ids",
        store=True,
    )
    purchase_order_ids = fields.Many2many(
        comodel_name="purchase.order",
        relation="rel_account_invoice_purchase_order",
        column1="invoice_id",
        column2="purchase_id",
        string="Purchase orders",
        copy=False,
        compute="_compute_purchase_order_ids",
        store=True,
    )
    supplier_invoice_number = fields.Char(copy=False)
    reference = fields.Char(copy=False)
    internal_number = fields.Char(copy=False)
    move_name = fields.Char(copy=False)
    invoice_number = fields.Char(copy=False)
    mrp_repair_id = fields.Many2one(
        string="Repair order",
        comodel_name="mrp.repair",
        compute="_compute_mrp_repair_id",
        store=True,
        copy=False,
    )
    crm_claim_id = fields.Many2one(
        string="Claim",
        comodel_name="crm.claim",
        store=True,
        related="mrp_repair_id.claim",
    )
    delivery_address_id = fields.Many2one(
        string="Delivery address",
        comodel_name="res.partner",
        compute="_compute_delivery_address_id",
    )

    def invoice_validate(self):
        for invoice in self.filtered(
            lambda l: l.reference_type and l.type == "in_invoice"
        ):
            if invoice.reference:
                cond = [
                    ("reference", "=", invoice.reference),
                    ("type", "=", "in_invoice"),
                    ("id", "!=", invoice.id),
                ]
                i = self.search(cond, limit=1)
                if i:
                    raise exceptions.Warning(
                        _("Payment Reference used in Supplier Invoice Number:" " %s")
                        % i.supplier_invoice_number
                    )
        res = super().invoice_validate()
        for invoice in self.filtered(lambda c: c.move_id):
            invoice.move_id.write({"invoice_id": invoice.id})
            invoice.move_id.line_id.write({"invoice_id": invoice.id})
        return res

    def invoice_pay_customer(self):
        res = super().invoice_pay_customer()
        if self.reference and self.type == "in_invoice":
            res["context"]["default_reference"] = self.reference
        return res

    @api.model
    def create(self, values):
        if "invoice_number" in values:
            values.pop("invoice_number")
        res = super().create(values)
        return res


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    invoice_number = fields.Char(
        string="Invoice number", related="invoice_id.invoice_number", store=True
    )
    type = fields.Selection(related="invoice_id.type", store=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner", related="invoice_id.partner_id", store=True
    )
    serial_numbers = fields.Text(string="Serial numbers", copy=False)

    @api.model
    def create(self, values):
        if "invoice_number" in values:
            values.pop("invoice_number")
        res = super().create(values)
        return res


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("date")
    def onchange_date(self):
        if self.date:
            cond = [
                ("date_start", "<=", self.date),
                ("date_stop", ">=", self.date),
                ("special", "=", False),
            ]
            period = self.env["account.period"].search(cond, limit=1)
            if period:
                self.period_id = period.id
