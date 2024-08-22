# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class PG(models.Model):
    _inherit = 'procurement.group'

    precio_unitario = fields.Float(
            string='Precio Unitario',
            digits='Product Price',
        )
    move_line_tax_ids = fields.Many2many(
            'account.tax',
            string='Taxes',
            domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False), ('active', '=', True)],
        )
    discount = fields.Float(
            digits='Discount',
            string='Discount (%)',
        )
    currency_id = fields.Many2one(
            'res.currency',
            string='Currency',
            states={'draft': [('readonly', False)]},
            default=lambda self: self.env.user.company_id.currency_id.id,
        )