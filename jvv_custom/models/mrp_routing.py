# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import _, api, exceptions, fields, models


class MrpRouting(models.Model):
    _inherit = "mrp.routing"

    production_line_id = fields.Many2one(
        string="Production line", comodel_name="mrp.routing.production.line"
    )
    load_time_line = fields.Float(string="Load time line")
    load_time_variable = fields.Float(string="Time to load variable")
    load_time_warehouse = fields.Float(string="Load time warehouse")
    load_time_variable_warehouse = fields.Float(string="Time variable load warehouse")

    def unlink(self):
        for routing in self:
            cond = [("routing_id", "=", routing.id)]
            production = self.env["mrp.production"].search(cond, limit=1)
            if production:
                raise exceptions.Warning(
                    _(
                        "You cannot delete this production route, because it is"
                        " already associated with a production order, what you"
                        " can do is deactivate it."
                    )
                )
        return super().unlink()


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    def unlink(self):
        for bom in self:
            cond = [("bom_id", "=", bom.id)]
            production = self.env["mrp.production"].search(cond, limit=1)
            if production:
                raise exceptions.Warning(
                    _(
                        "You cannot delete this material's list, because it is"
                        " already associated with a production order, what you"
                        " can do is deactivate it."
                    )
                )
        return super().unlink()


class MrpRoutingProductionLine(models.Model):
    _name = "mrp.routing.production.line"
    _description = "Production line"

    name = fields.Char(string="Description", required=True)


class MrpRoutingWorkcenter(models.Model):
    _inherit = "mrp.routing.workcenter"

    op_wc_lines = fields.One2many(copy=True)
