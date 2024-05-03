# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import _, api, exceptions, fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.depends("reviewer_id")
    def _compute_department_id(self):
        for task in self.filtered(lambda l: l.reviewer_id):
            cond = [("user_id", "=", task.reviewer_id.id)]
            employee = self.env["hr.employee"].search(cond, limit=1)
            if employee and employee.department_id:
                task.department_id = employee.department_id.id

    @api.depends("project_id", "project_id.productions")
    def _compute_project_from_mrp(self):
        for task in self.filtered(lambda l: l.project_id):
            project_from_mrp = False
            if task.project_id.productions:
                project_from_mrp = True
            task.project_from_mrp = project_from_mrp

    department_id = fields.Many2one(
        string="Department",
        comodel_name="hr.department",
        compute="_compute_department_id",
        store=True,
    )
    project_from_mrp = fields.Boolean(
        string="Project from mrp", compute="_compute_project_from_mrp", store=True
    )

    @api.model
    def create(self, values):
        production_obj = self.env["mrp.production"]
        if "project_id" in values and values.get("project_id", False):
            cond = [("project_id", "=", values.get("project_id"))]
            production = production_obj.search(cond, limit=1)
            if production:
                cond = [("mrp_production_id", "=", production.id)]
                line = self.env["sale.order.line"].search(cond, limit=1)
                if line:
                    name = "{} - {} - {}".format(
                        line.order_id.name,
                        production.product_id.name,
                        production.product_id.product_manager.name,
                    )
                    values["name"] = name
                if not line:
                    cond = [
                        ("id", "!=", production.id),
                        ("analytic_account_id", "=", production.analytic_account_id.id),
                    ]
                    production = production_obj.search(cond, limit=1)
                    if production:
                        cond = [("mrp_production_id", "=", production.id)]
                        line = self.env["sale.order.line"].search(cond, limit=1)
                        if line:
                            name = "{} - {} - {}".format(
                                line.order_id.name,
                                production.product_id.name,
                                production.product_id.product_manager.name,
                            )
                            values["name"] = name
        return super().create(values)


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    active = fields.Boolean(string="Active", default=True)

    def unlink(self):
        for type in self:
            raise exceptions.Warning(
                _(
                    "You cannot delete the task stage %s, what you can do is "
                    "deactivate it."
                )
                % type.name
            )
