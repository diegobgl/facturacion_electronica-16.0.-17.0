# -*- coding: utf-8 -*-
from odoo import api, fields, models
from lxml import etree
from base64 import b64decode
import logging


_logger = logging.getLogger(__name__)


class ProccessMail(models.Model):
    _name = "mail.message.dte"
    _description = "DTE Recibido"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Nombre Envío", readonly=True,)
    mail_id = fields.Many2one("mail.message", string="Email", readonly=True, ondelete="cascade",)
    document_ids = fields.One2many("mail.message.dte.document", "dte_id", string="Documents", readonly=True,)
    company_id = fields.Many2one("res.company", string="Compañía", readonly=True,)
    xml_id = fields.Many2one("ir.attachment", string="XML",)

    _order = "create_date DESC"

    def _parse_xml(self, xml_string):
        string_xml = b64decode(xml_string).decode("ISO-8859-1")
        xml = string_xml.replace('<?xml version="1.0" encoding="ISO-8859-1"?>', "").replace(
            '<?xml version="1.0" encoding="ISO-8859-1" ?>', ""
        )
        xml = xml.replace(' xmlns="http://www.sii.cl/SiiDte"', "")
        parser = etree.XMLParser(remove_blank_text=True)
        return etree.fromstring(xml, parser=parser)

    def parsed_xml(self):
        att = self.xml_id
        return self._parse_xml(att.datas)

    def pre_process(self):
        self.process_message(pre=True)

    def process_message(self, pre=True, option='upload', dte_receipt_method=False):
        created = []
        if not dte_receipt_method:
            ICPSudo = self.env["ir.config_parameter"].sudo()
            dte_receipt_method = ICPSudo.get_param("account.dte_receipt_method", default='manual')
        for r in self:
            if r.xml_id:
                vals = {
                    "xml_file": r.xml_id.datas,
                    "filename": r.xml_id.name,
                    "pre_process": pre,
                    "dte_id": r.id,
                    "option": option,
                    "action": dte_receipt_method
                }
                val = self.env["sii.dte.upload_xml.wizard"].with_user(self.env.ref("base.user_admin").id).create(vals)
                created.extend(val.confirm(ret=True))
        if dte_receipt_method == "create_po":
            xml_id = "purchase.purchase_order_tree"
            target_model = "purchase.order"
        elif dte_receipt_method == "create_move":
            xml_id = "account.view_invoice_tree"
            target_model = "account.move"
        else:
            xml_id = "l10n_cl_fe.action_dte_process"
            target_model = "mail.message.dte.document"
        result = self.env.ref("%s" % (xml_id)).read()[0]
        result["res_model"] = target_model
        if created:
            domain = eval(result.get("domain", "[]"))
            domain.append(("id", "in", created))
            result["domain"] = domain
        return result
