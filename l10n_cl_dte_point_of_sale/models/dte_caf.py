from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class DTECAF(models.Model):
    _inherit = "dte.caf"

    def _get_tables(self):
        vals = super(DTECAF, self)._get_tables()
        if self.document_class_id.es_boleta() or self.document_class_id.es_nc():
            vals.append('pos_order')
        return vals

    def _pos_order_where_string_and_param(self):
        where_string = """WHERE
            state IN ('done', 'cancel', 'paid')
            AND document_class_id = %(document_class_id)s
        """
        param = {
            'document_class_id': self.document_class_id.id
        }
        return where_string, param

    def _join_inspeccionar(self):
        join = super(DTECAF, self)._join_inspeccionar()
        if self.document_class_id.es_boleta() or self.document_class_id.es_nc():
            join += ' LEFT JOIN pos_order p on s = p.sii_document_number and p.document_class_id = %s' % self.document_class_id.id
        return join

    def _where_inspeccionar(self):
        where = super(DTECAF, self)._where_inspeccionar()
        if self.document_class_id.es_boleta() or self.document_class_id.es_nc():
            where += ' AND p.sii_document_number is null'
        return where
