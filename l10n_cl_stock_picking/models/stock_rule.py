# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_custom_move_fields(self):
        vals = super(StockRule, self)._get_custom_move_fields()
        vals += [
                'precio_unitario',
                'discount',
                'move_line_tax_ids',
                'currency_id',
            ]
        return vals

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        move_values = super(StockRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        if move_values.get('sale_line_id') and values.get('picking_description'):
            move_values['description_picking'] = values.get('picking_description')
        return move_values
