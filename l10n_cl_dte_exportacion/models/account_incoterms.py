# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class Incoterms(models.Model):
    _inherit = "account.incoterms"

    aduanas_code = fields.Integer(
            string="Código de aduanas"
        )

    def name_get(self):
        res = []
        for i in self:
            res.append((i.id, '%s.-[%s] %s' %(i.aduanas_code, i.code, i.name)))
        return res
