# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class IRSequence(models.Model):
    _inherit = 'ir.sequence'

