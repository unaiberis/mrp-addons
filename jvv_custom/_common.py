# -*- coding: utf-8 -*-
# Copyright 2020 Alfredo de la Fuente - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from pytz import timezone, utc
from openerp import fields

str2datetime = fields.Datetime.from_string
date2str = fields.Date.to_string


def _convert_to_local_date(date, tz=u'UTC'):
    if not date:
        return False
    if not tz:
        tz = u'UTC'
    new_date = str2datetime(date) if isinstance(date, str) else date
    new_date = new_date.replace(tzinfo=utc)
    local_date = new_date.astimezone(timezone(tz)).replace(tzinfo=None)
    return local_date
