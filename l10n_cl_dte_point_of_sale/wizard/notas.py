# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError
import time
import logging
_logger = logging.getLogger(__name__)


class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""

    _name = "pos.order.refund"

    tipo_nota = fields.Many2one(
            'sii.document_class',
            string="Tipo De nota",
            required=True,
            domain=[('document_type','in',['debit_note','credit_note']), ('dte','=',True)],
        )
    filter_refund = fields.Selection(
            [
                ('1','Anula Documento de Referencia'),
                ('2','Corrige texto Documento Referencia'),
                ('3','Corrige montos'),
            ],
            default='1',
            string='Refund Method',
            required=True, help='Refund base on this type. You can not Modify and Cancel if the invoice is already reconciled',
        )
    motivo = fields.Char("Motivo")
    date_order = fields.Date(string="Fecha de Documento")


    def confirm(self):
        """Create a copy of order  for refund order"""
        clone_list = self.env['pos.order']
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for order in self.env['pos.order'].browse(active_ids):
            if not order.document_class_id or not order.sii_document_number:
                raise UserError("Por esta área solamente se puede crear Nota de Crédito a Boletas validamente emitidas, si es un pedido simple, debe presionar en retornar simple")
            current_session = self.env['pos.session'].search(
                    [
                        ('state', '!=', 'closed'),
                        ('user_id', '=', self.env.uid),
                    ],
                    limit=1
                )
            if not current_session:
                raise UserError(_('To return product(s), you need to open a session that will be used to register the refund.'))
            if not current_session.config_id.habilita_nc:
                raise UserError(_('Debe habilitar NC en la configuración del PDV %s' % current_session.config_id.name))
            seq = current_session.config_id.secuencia_nc
            if not seq:
                raise UserError(_("Debe crear una secuencia de Nota de Crédito"))
            res = order.refund()
            refund = self.env['pos.order'].browse(res['res_id'])
            refund.write({
                'sequence_id': seq.id,
                'document_class_id': seq.sii_document_class_id.id,
                'sii_document_number': 0,
                'signature': False,
                'referencias': [[0,0, {
                    'origen': int(order.sii_document_number),
                    'sii_referencia_TpoDocRef': order.document_class_id.id,
                    'sii_referencia_CodRef': self.filter_refund,
                    'motivo': self.motivo,
                    'fecha_documento': self.date_order
                }]],
            })
            return res
