from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class DTECAF(models.Model):
    _inherit = "dte.caf"

    def _get_tables(self):
        if self.document_class_id.es_guia():
            return ['stock_picking']
        return super(DTECAF, self)._get_tables()

    def _stock_picking_where_string_and_param(self):
        where_string = """WHERE
            state IN ('done', 'cancel')
            AND document_class_id = %(document_class_id)s
            AND use_documents
        """
        param = {
            'document_class_id': self.document_class_id.id
        }
        return where_string, param

    def _join_inspeccionar(self):
        if self.document_class_id.es_guia():
            return ' LEFT JOIN stock_picking sp on s = sp.sii_document_number and sp.document_class_id = %s' % self.sequence_id.sii_document_class_id.id
        return super(DTECAF, self)._join_inspeccionar()

    def _where_inspeccionar(self):
        if self.document_class_id.es_guia():
            return ' sp.sii_document_number is null'
        return super(DTECAF, self)._where_inspeccionar()
