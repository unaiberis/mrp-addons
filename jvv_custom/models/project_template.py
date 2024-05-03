# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, fields


class ProjectTemplate(models.Model):
    _name = 'project.template'
    _description = 'Project template'

    name = fields.Char(string='Description')
    task_ids = fields.One2many(
        comodel_name='project.template.task', inverse_name='template_id',
        string='Tasks')


class ProjectTemplateTask(models.Model):
    _name = 'project.template.task'
    _description = 'Project template task'

    template_id = fields.Many2one(
        comodel_name='project.template', string='Project template')
    name = fields.Char(string='Description')
