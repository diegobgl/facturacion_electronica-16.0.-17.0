from odoo import http
from odoo.addons.l10n_cl_fe.controllers import downloader

class Binary(downloader.Binary):

    @http.route(["/download/xml/cesion/<model('account.move'):rec_id>"], type='http', auth='user')
    def download_cesion(self, rec_id, **post):
        filename = ('CES_%s_%s.xml' % (rec_id.document_class_id.sii_code, rec_id.sii_document_number)).replace(' ','_')
        filecontent = rec_id.sii_cesion_request.xml_envio
        return self.document(filename, filecontent)
