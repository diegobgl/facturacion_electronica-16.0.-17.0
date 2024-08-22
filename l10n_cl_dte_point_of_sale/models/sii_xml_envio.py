# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools.translate import _


class SIIXMLEnvio(models.Model):
    _inherit = 'sii.xml.envio'

    order_ids = fields.One2many(
            'pos.order',
            'sii_xml_request',
            string="Ordenes POS",
            readonly=True,
            states={'draft': [('readonly', False)]},
        )

    def get_doc(self):
        for r in self.order_ids:
            return r
        return super(SIIXMLEnvio, self).get_doc()

    def set_childs(self, state, detalle_rep_rech=False):
        super(SIIXMLEnvio, self).set_childs(state, detalle_rep_rech=detalle_rep_rech)
        for r in self.order_ids:
            if r.es_boleta() and detalle_rep_rech:
                state = self.check_estado_boleta(r, detalle_rep_rech, state)
            r.sii_result = state
