from odoo import SUPERUSER_ID, api
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, installed_version):
    _logger.warning("Post Migrating l10n_cl_dte_point_of_sale from version %s to 16.0.0.30.5" % installed_version)
    def zero_pad(num, size):
        s = str(num)
        while len(s) < size:
            s = "0" + s
        return s
    env = api.Environment(cr, SUPERUSER_ID, {})
    for r in env['pos.order'].search([('pos_reference','=', False), ('state', '!=', 'draft')]):
        for ref in r.referencias:
            if ref.sii_referencia_CodRef in ['1', '2', '3']:
                order = env['pos.order'].search([('sii_document_number', '=', ref.origen), ('document_class_id', '=', ref.sii_referencia_TpoDocRef.id)], limit=1)
                r.pos_reference = order.pos_reference
