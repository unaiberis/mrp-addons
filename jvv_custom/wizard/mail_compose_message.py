# -*- coding: utf-8 -*-
# Copyright 2019 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models, api


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self):
        purchase_obj = self.env['purchase.order']
        res = super(MailComposeMessage, self).send_mail()
        for wizard in self:
            if wizard.model and wizard.model == 'purchase.order':
                mass_mode = wizard.composition_mode in ('mass_mail',
                                                        'mass_post')
                if mass_mode and wizard.use_active_domain:
                    res_ids = purchase_obj.search(
                        eval(wizard.active_domain)).ids
                elif (mass_mode and self.env.context.get('active_ids')):
                    res_ids = self.env.context['active_ids']
                else:
                    res_ids = [wizard.res_id]
                purchases = purchase_obj.browse(res_ids)
                purchases.write({'mail_send': 'si'})
        return res
