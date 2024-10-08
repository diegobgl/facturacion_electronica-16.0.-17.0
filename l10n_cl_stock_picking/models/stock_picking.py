# -*- coding: utf-8 -*-
from odoo import osv, models, fields, api, _
from odoo.exceptions import except_orm, UserError
import odoo.addons.decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from datetime import datetime, timedelta, date
import logging
_logger = logging.getLogger(__name__)

from odoo.addons.l10n_cl_fe.models.bigint import BigInt
from six import string_types
try:
    from facturacion_electronica import facturacion_electronica as fe
except Exception as e:
    _logger.warning("Problema al cargar Facturación electrónica: %s" % str(e))
try:
    from io import BytesIO
except:
    _logger.warning("no se ha cargado io")
try:
    import pdf417gen
except ImportError:
    _logger.info('Cannot import pdf417gen library')
try:
    import base64
except ImportError:
    _logger.info('Cannot import base64 library')
try:
    from PIL import Image, ImageDraw, ImageFont
except:
    _logger.warning("no se ha cargado PIL")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.onchange('currency_id', 'move_ids', 'move_reason')
    @api.depends('currency_id', 'move_ids', 'move_reason')
    def _compute_amount(self):
        for rec in self:
            amount_untaxed = 0
            amount_tax = 0
            if rec.move_reason not in ['5']:
                taxes = rec.get_taxes_values()
                for k, v in taxes.items():
                    amount_tax += v['amount']
                amount_tax = rec.currency_id.round(amount_tax)
                for line in rec.move_ids:
                    amount_untaxed += line.price_untaxed
            rec.amount_tax = amount_tax
            rec.amount_untaxed = amount_untaxed
            rec.amount_total = amount_untaxed + amount_tax

    def _prepare_tax_line_vals(self, line, tax):
        """ Prepare values to create an account.move.tax line

        The line parameter is an account.move.line, and the
        tax parameter is the output of account.tax.compute_all().
        """
        t = self.env['account.tax'].browse(tax['id'])
        vals = {
            'picking_id': self.id,
            'description': t.with_context(**{'lang': self.partner_id.lang} if self.partner_id else {}).description,
            'tax_id': tax['id'],
            'amount': tax['amount'] if tax['amount'] > 0 else (tax['amount'] * -1),
            'base': tax['base'],
            'manual': False,
            'sequence': tax['sequence'],
            'amount_retencion': tax.get('retencion', 0)
        }
        return vals

    def get_grouping_key(self, vals):
        return str(vals['tax_id'])

    def _get_grouped_taxes(self, line, taxes, tax_grouped={}):
        for tax in taxes:
            val = self._prepare_tax_line_vals(line, tax)
            key = self.get_grouping_key(val)
            if key not in tax_grouped:
                tax_grouped[key] = val
                tax_grouped[key]['base'] = self.currency_id.round(val['base'])
            else:
                tax_grouped[key]['amount'] += val['amount']
                tax_grouped[key]['amount_retencion'] += val['amount_retencion']
                tax_grouped[key]['base'] += self.currency_id.round(val['base'])
        return tax_grouped


    def get_taxes_values(self):
        tax_grouped = {}
        totales = {}
        included = False
        for line in self.move_ids:
            qty = line.quantity_done
            if qty <= 0:
                qty = line.product_uom_qty
            if (line.move_line_tax_ids and line.move_line_tax_ids[0].price_include) :# se asume todos losproductos vienen con precio incluido o no ( no hay mixes)
                if included or not tax_grouped:#genero error en caso de contenido mixto, en caso primer impusto no incluido segundo impuesto incluido
                    for t in line.move_line_tax_ids:
                        if t not in totales:
                            totales[t] = 0
                        amount_line = (self.currency_id.round(line.precio_unitario *qty))
                        totales[t] += (amount_line * (1 - (line.discount / 100)))
                included = True
            else:
                included = False
            if (totales and not included) or (included and not totales):
                raise UserError('No se puede hacer timbrado mixto, todos los impuestos en este pedido deben ser uno de estos dos:  1.- precio incluído, 2.-  precio sin incluir')
            taxes = line.move_line_tax_ids.with_context(
                date=self.scheduled_date,
                currency=self.currency_id.code).compute_all(line.precio_unitario, self.currency_id, qty, line.product_id, self.partner_id, discount=line.discount, uom_id=line.product_uom)['taxes']
            tax_grouped = self._get_grouped_taxes(line, taxes, tax_grouped)
        #if totales:
        #    tax_grouped = {}
        #    for line in self.invoice_line_ids:
        #        for t in line.invoice_line_tax_ids:
        #            taxes = t.compute_all(totales[t], self.currency_id, 1)['taxes']
        #            tax_grouped = self._get_grouped_taxes(line, taxes, tax_grouped)
        #_logger.warning(tax_grouped)
        '''
        @TODO GDR para guías
        if not self.global_descuentos_recargos:
            return tax_grouped
        gdr, gdr_exe = self.porcentaje_dr()
        '''
        for t, group in tax_grouped.items():
            group['base'] = self.currency_id.round(group['base'])
            group['amount'] = self.currency_id.round(group['amount'])
        return tax_grouped

    def set_use_document(self):
        return (self.picking_type_id and self.picking_type_id.code != 'incoming')

    def get_xml_file(self):
        return {
            'type' : 'ir.actions.act_url',
            'url': '/download/xml/guia/%s' % (self.id),
            'target': 'self',
        }

    def get_folio(self):
        # saca el folio directamente de la secuencia
        return int(self.sii_document_number)

    def pdf417bc(self, ted, columns=13, ratio=3):
        bc = pdf417gen.encode(
            ted,
            security_level=5,
            columns=columns,
            encoding='ISO-8859-1',
        )
        image = pdf417gen.render_image(
            bc,
            padding=15,
            scale=1,
            ratio=ratio,
        )
        return image


    def get_barcode_img(self, columns=13, ratio=3):
        barcodefile = BytesIO()
        image = self.pdf417bc(self.sii_barcode, columns, ratio)
        image.save(barcodefile, 'PNG')
        data = barcodefile.getvalue()
        return base64.b64encode(data)

    def _get_barcode_img(self):
        for r in self:
            if r.sii_barcode:
                r.sii_barcode_img = r.get_barcode_img()
            else:
                r.sii_barcode_img = False

    def _set_default_dc(self):
        pt_id = self.env.context.get('default_picking_type_id', False)
        pt = self.env['stock.picking.type'].browse(pt_id)
        if pt.code == 'incoming':
            return False
        return pt.warehouse_id.document_class_id.id

    sii_batch_number = fields.Integer(
        copy=False,
        string='Batch Number',
        readonly=True,
        help='Batch number for processing multiple invoices together')
    sii_barcode = fields.Char(
        copy=False,
        string=_('SII Barcode'),
        readonly=True,
        help='SII Barcode Name')
    sii_barcode_img = fields.Binary(
        compute="_get_barcode_img",
        string=_('SII Barcode Image'),
        help='SII Barcode Image in PDF417 format')
    sii_message = fields.Text(
            string='SII Message',
            copy=False,
        )
    sii_xml_dte = fields.Text(
            string='SII XML DTE',
            copy=False,
        )
    sii_xml_request = fields.Many2one(
            'sii.xml.envio',
            string='SII XML Request',
            copy=False,
        )
    sii_result = fields.Selection(
            [
                ('', 'n/a'),
                ('NoEnviado', 'No Enviado'),
                ('EnCola','En cola de envío'),
                ('Enviado', 'Enviado'),
                ('EnProceso', 'EnProceso'),
                ('Aceptado', 'Aceptado'),
                ('Rechazado', 'Rechazado'),
                ('Reparo', 'Reparo'),
                ('Proceso', 'Proceso'),
                ('Anulado', 'Anulado'),
            ],
            string='Resultado',
            copy=False,
            help="SII request result",
            default = '',
        )
    canceled = fields.Boolean(string="Is Canceled?")
    estado_recep_dte = fields.Selection(
        [
            ('no_revisado', 'No Revisado'),
            ('0', 'Conforme'),
            ('1', 'Error de Schema'),
            ('2', 'Error de Firma'),
            ('3', 'RUT Receptor No Corresponde'),
            ('90', 'Archivo Repetido'),
            ('91', 'Archivo Ilegible'),
            ('99', 'Envio Rechazado - Otros')
        ],string="Estado de Recepción del Envío")
    estado_recep_glosa = fields.Char(string="Información Adicional del Estado de Recepción")
    responsable_envio = fields.Many2one('res.users')
    document_class_id = fields.Many2one(
        'sii.document_class',
        string="Tipo de documento",
        readonly=True,
        states={'assigned':[('readonly',False)],'draft':[('readonly',False)]},
        default=_set_default_dc,
        domain=[('document_type', '=', 'stock_picking')]
    )
    dte_ticket = fields.Boolean(
        string="¿Formato Ticket?")

    amount_untaxed = fields.Monetary(
            compute='_compute_amount',
            digits='Account',
            string='Untaxed Amount',
            store=True,
        )
    amount_tax = fields.Monetary(
            compute='_compute_amount',
            string='Taxes',
            store=True,
        )
    amount_total = fields.Monetary(
            compute='_compute_amount',
            string='Total',
            store=True,
        )
    currency_id = fields.Many2one(
            'res.currency',
            string='Currency',
            required=True,
            states={'draft': [('readonly', False)]},
            default=lambda self: self.env.user.company_id.currency_id.id,
        )
    sii_batch_number = fields.Integer(
            copy=False,
            string='Batch Number',
            readonly=True,
            help='Batch number for processing multiple invoices together',
        )
    activity_description = fields.Many2one(
            'sii.activity.description',
            string='Giro',
            related="partner_id.commercial_partner_id.activity_description",
            readonly=True, states={'assigned':[('readonly',False)],'draft':[('readonly',False)]},
        )
    sii_document_number = BigInt(
            string='Document Number',
            copy=False,
            readonly=True,
            states={'assigned':[('readonly',False)],'draft':[('readonly',False)]},
        )
    responsability_id = fields.Many2one(
            'sii.responsability',
            string='Responsability',
            related='partner_id.commercial_partner_id.responsability_id',
            store=True,
        )
    next_number = fields.Integer(
            related='picking_type_id.warehouse_id.sequence_id.number_next_actual',
            string='Next Document Number',
            readonly=True,
        )
    use_documents = fields.Boolean(
            string='Use Documents?',
            default=set_use_document,
            readonly=True,
            states={'assigned':[('readonly',False)],'draft':[('readonly',False)]},
        )
    reference = fields.One2many(
            'stock.picking.referencias',
            'stock_picking_id',
            readonly=False,
            states={'done':[('readonly',True)]},
        )
    transport_type = fields.Selection(
            [
                ('2', 'Despacho por cuenta de empresa'),
                ('1', 'Despacho por cuenta del cliente'),
                ('3', 'Despacho Externo'),
                ('0', 'Sin Definir')
            ],
            string="Tipo de Despacho",
            default="2",
            readonly=False, states={'done':[('readonly',True)]},
        )
    move_reason = fields.Selection(
            [
                    ('1', 'Operación constituye venta'),
                    ('2', 'Ventas por efectuar'),
                    ('3', 'Consignaciones'),
                    ('4', 'Entrega Gratuita'),
                    ('5', 'Traslados Internos'),
                    ('6', 'Otros traslados no venta'),
                    ('7', 'Guía de Devolución'),
                    ('8', 'Traslado para exportación'),
                    ('9', 'Ventas para exportación')
            ],
            string='Razón del traslado',
            default="1",
            readonly=False, states={'done':[('readonly',True)]},
        )
    vehicle = fields.Many2one(
            'fleet.vehicle',
            string="Vehículo",
            readonly=False,
            states={'done': [('readonly', True)]},
        )
    chofer = fields.Many2one(
            'res.partner',
            string="Chofer",
            readonly=False,
            states={'done': [('readonly', True)]},
        )
    patente = fields.Char(
            string="Patente",
            readonly=False,
            states={'done': [('readonly', True)]},
        )
    contact_id = fields.Many2one(
            'res.partner',
            string="Contacto",
            readonly=False,
            states={'done': [('readonly', True)]},
        )
    invoiced = fields.Boolean(
            string='Invoiced?',
            readonly=True,
        )
    respuesta_ids = fields.Many2many(
            'sii.respuesta.cliente',
            string="Recepción del Cliente",
            readonly=True,
        )

    @api.onchange('picking_type_id')
    def onchange_picking_type(self,):
        if self.picking_type_id:
            self.use_documents = self.picking_type_id.code not in ["incoming"]
        else:
            self.use_documents = False

    @api.onchange('picking_type_id', 'use_documents')
    def set_dc_id(self):
        if self.use_documents and self.picking_type_id:
            self.document_class_id = self.picking_type_id.warehouse_id.document_class_id
            self.sii_document_number = 0
        else:
            self.document_class_id = self.env['sii.document_class']

    @api.onchange('company_id')
    def _refreshData(self):
        if self.move_ids:
            for m in self.move_ids:
                m.company_id = self.company_id.id

    @api.onchange('vehicle')
    def _setChofer(self):
        self.chofer = self.vehicle.driver_id
        self.patente = self.vehicle.license_plate

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for s in self:
            if not s.use_documents or s.picking_type_id.warehouse_id.restore_mode:
                continue
            s.sii_document_number = s.picking_type_id.warehouse_id.sequence_id.next_by_id()
            document_number = (s.document_class_id.doc_code_prefix or '') + str(s.sii_document_number)
            s.name = document_number
            if s.picking_type_id.code in ['outgoing', 'internal']:# @TODO diferenciar si es de salida o entrada para internal
                s.responsable_envio = self.env.uid
                s.sii_result = 'NoEnviado'
                s._timbrar()
                ISCP = self.env["ir.config_parameter"].sudo()
                metodo = ISCP.get_param("account.send_dte_method", default='diferido')
                if metodo == 'manual':
                    continue
                tiempo_pasivo = datetime.now()
                if metodo == 'diferido':
                    tipo_trabajo = 'pasivo'
                    tiempo_pasivo += timedelta(
                        hours=int(ISCP.get_param("account.auto_send_dte", default=1))
                    )
                elif metodo == 'inmediato':
                    tipo_trabajo = 'envio'
                self.env['sii.cola_envio'].sudo().create({
                                            'company_id': s.company_id.id,
                                            'doc_ids': [s.id],
                                            'model': 'stock.picking',
                                            'user_id': self.env.uid,
                                            'tipo_trabajo': tipo_trabajo,
                                            'date_time': tiempo_pasivo,
                                            })
        return res

    def do_dte_send_picking(self, n_atencion=None):
        ids = []
        if not isinstance(n_atencion, string_types):
            n_atencion = ''
        for rec in self:
            rec.responsable_envio = self.env.uid
            if rec.sii_result in ['', 'NoEnviado', 'Rechazado']:
                if not rec.sii_xml_request or rec.sii_result in [ 'Rechazado' ]:
                    rec._timbrar(n_atencion)
                    if len(rec.sii_xml_request.picking_ids) == 1:
                        rec.sii_xml_request.unlink()
                    else:
                        rec.sii_xml_request = False
                rec.sii_result = "EnCola"
                rec.sii_message = ""
                ids.append(rec.id)
        if ids:
            self.env['sii.cola_envio'].sudo().create({
                                    'company_id': self[0].company_id.id,
                                    'doc_ids': ids,
                                    'model': 'stock.picking',
                                    'user_id': self.env.uid,
                                    'tipo_trabajo': 'envio',
                                    'n_atencion': n_atencion,
                                    "set_pruebas": self._context.get("set_pruebas", False),
                                    })
    def _giros_emisor(self):
        giros_emisor = []
        for turn in self.picking_type_id.warehouse_id.acteco_ids:
            giros_emisor.append(turn.code)
        return giros_emisor

    def _id_doc(self, taxInclude=False, MntExe=0):
        IdDoc = {}
        IdDoc['TipoDTE'] = self.document_class_id.sii_code
        IdDoc['Folio'] = self.get_folio()
        IdDoc['FchEmis'] = self.scheduled_date.strftime("%Y-%m-%d")
        if self.transport_type and self.transport_type not in ['0']:
            IdDoc['TipoDespacho'] = self.transport_type
        IdDoc['IndTraslado'] = self.move_reason
        if self.dte_ticket:
            IdDoc['TpoImpresion'] = "T"
        if taxInclude and MntExe == 0 :
            IdDoc['MntBruto'] = 1
        #IdDoc['FmaPago'] = self.forma_pago or 1
        #IdDoc['FchVenc'] = self.date_due or datetime.strftime(datetime.now(), '%Y-%m-%d')
        return IdDoc

    def _emisor(self):
        Emisor = {}
        Emisor['RUTEmisor'] = self.company_id.partner_id.rut()
        Emisor['RznSoc'] = self.company_id.partner_id.name
        Emisor['GiroEmis'] = self.company_id.activity_description.name
        Emisor['Telefono'] = self.company_id.phone or ''
        Emisor['CorreoEmisor'] = self.company_id.dte_email_id.name_get()[0][1]
        Emisor['Actecos'] = self._giros_emisor()
        dir_origen = self.company_id
        if self.picking_type_id.warehouse_id.sii_code:
            Emisor['Sucursal'] = self.picking_type_id.warehouse_id.sucursal_id.name
            Emisor['CdgSIISucur'] = self.picking_type_id.warehouse_id.sii_code
            dir_origen = self.picking_type_id.warehouse_id.sucursal_id.partner_id
        Emisor['DirOrigen'] = dir_origen.street + ' ' +(dir_origen.street2 or '')
        Emisor['CmnaOrigen'] = dir_origen.city_id.name or ''
        Emisor['CiudadOrigen'] = dir_origen.city or ''
        Emisor["Modo"] = "produccion" if self.company_id.dte_service_provider == 'SII'\
                  else 'certificacion'
        Emisor["NroResol"] = self.company_id.dte_resolution_number
        Emisor["FchResol"] = self.company_id.dte_resolution_date.strftime('%Y-%m-%d')
        Emisor["ValorIva"] = 19
        return Emisor

    def _receptor(self):
        Receptor = {}
        partner_id = self.partner_id or self.company_id.partner_id
        if not partner_id.commercial_partner_id.vat :
            raise UserError("Debe Ingresar RUT Receptor")
        Receptor['RUTRecep'] = partner_id.commercial_partner_id.rut()
        Receptor['RznSocRecep'] = partner_id.commercial_partner_id.name
        activity_description = self.activity_description or partner_id.activity_description
        if not activity_description:
            raise UserError(_('Seleccione giro del partner'))
        Receptor['GiroRecep'] = activity_description.name
        if partner_id.commercial_partner_id.phone:
            Receptor['Contacto'] = partner_id.commercial_partner_id.phone
        if partner_id.commercial_partner_id.dte_email:
            Receptor['CorreoRecep'] = partner_id.commercial_partner_id.dte_email
        if not partner_id.commercial_partner_id.street:
            raise UserError("Debe Ingresar Dirección Receptor")
        Receptor['DirRecep'] = (partner_id.commercial_partner_id.street) + ' ' + ((partner_id.commercial_partner_id.street2) or '')
        Receptor['CmnaRecep'] = partner_id.commercial_partner_id.city_id.name
        Receptor['CiudadRecep'] = partner_id.commercial_partner_id.city
        return Receptor

    def _transporte(self):
        Transporte = {}
        if self.patente:
            Transporte['Patente'] = self.patente[:8]
        elif self.vehicle:
            Transporte['Patente'] = self.vehicle.license_plate or ''
        if self.transport_type in ['2', '3'] and self.chofer:
            if not self.chofer.vat:
                raise UserError("Debe llenar los datos del chofer")
            if self.transport_type == '2':
                Transporte['RUTTrans'] = self.company_id.partner_id.rut()
            else:
                if not self.carrier_id.partner_id.vat:
                    raise UserError("Debe especificar el RUT del transportista, en su ficha de partner")
                Transporte['RUTTrans'] = self.carrier_id.partner_id.rut()
            if self.chofer:
                Transporte['Chofer'] = {}
                Transporte['Chofer']['RUTChofer'] = self.chofer.rut()
                Transporte['Chofer']['NombreChofer'] = self.chofer.name[:30]
        partner_id = self.partner_id or self.company_id.partner_id
        Transporte['DirDest'] = (partner_id.street or '')+ ' '+ (partner_id.street2 or '')
        Transporte['CmnaDest'] = partner_id.city_id.name or ''
        Transporte['CiudadDest'] = partner_id.city or ''
        #@TODO SUb Area Aduana
        return Transporte

    def _totales(self, MntExe=0, no_product=False, taxInclude=False):
        Totales = {}
        IVA = False
        for line in self.move_ids:
            if line.move_line_tax_ids:
                for t in line.move_line_tax_ids:
                    if t.sii_code in [14, 15, 17]:
                        IVA = t
        if IVA and not no_product:
            Totales['MntNeto'] = self.currency_id.round(self.amount_untaxed)
            Totales['TasaIVA'] = round(IVA.amount,2)
            for k, t in self.get_taxes_values().items():
                if k == str(IVA.id):
                    Totales['IVA'] = self.currency_id.round(t['amount'])
        monto_total = self.currency_id.round(self.amount_total)
        if no_product:
            monto_total = 0
        Totales['MntTotal'] = monto_total
        return Totales

    def _encabezado(self, MntExe=0, no_product=False, taxInclude=False):
        Encabezado = {}
        Encabezado['IdDoc'] = self._id_doc(taxInclude, MntExe)
        Encabezado['Receptor'] = self._receptor()
        Encabezado['Transporte'] = self._transporte()
        Encabezado['Totales'] = self._totales(MntExe, no_product)
        return Encabezado

    def _picking_lines(self):
        line_number = 1
        picking_lines = []
        MntExe = 0
        for line in self.move_ids:
            no_product = False
            if line.product_id.default_code == 'NO_PRODUCT':
                no_product = True
            lines = {}
            lines['NroLinDet'] = line_number
            if line.product_id.default_code and not no_product:
                lines['CdgItem'] = {}
                lines['CdgItem']['TpoCodigo'] = 'INT1'
                lines['CdgItem']['VlrCodigo'] = line.product_id.default_code
            taxInclude = False
            lines["Impuesto"] = []
            if line.move_line_tax_ids:
                for t in line.move_line_tax_ids:
                    if t.sii_code in [26, 27, 28, 35, 271]:#@Agregar todos los adicionales
                        lines['CodImpAdic'] = t.sii_code
                    taxInclude = t.price_include
                    if t.amount == 0 or t.sii_code in [0]:#@TODO mejor manera de identificar exento de afecto
                        lines['IndExe'] = 1
                        MntExe += int(round(line.subtotal, 0))
                    else:
                        amount = t.amount
                        if t.sii_code in [28, 35]:
                            amount = t.compute_factor(line.product_uom)
                        lines["Impuesto"].append(
                                {
                                    "CodImp": t.sii_code,
                                    'price_include': taxInclude,
                                    'TasaImp': amount,
                                }
                        )
            lines['NmbItem'] = line.product_id.with_context(
                    display_default_code=False).name
            lines['DscItem'] = line.description_picking
            qty = round(line.quantity_done, 4)
            if qty <=0:
                qty = round(line.product_uom_qty, 4)
                if qty <=0:
                    raise UserError("¡No puede ser menor o igual que 0!, tiene líneas con cantidad realiada 0")
            if not no_product:
                lines['QtyItem'] = qty
            if self.move_reason in ['5']:
                no_product = True
            if not no_product:
                lines['UnmdItem'] = line.product_uom.name[:4]
                if line.precio_unitario > 0:
                    lines['PrcItem'] = round(line.precio_unitario, 4)
            if line.discount > 0:
                lines['DescuentoPct'] = line.discount
                lines['DescuentoMonto'] = int(round((((line.discount / 100) * lines['PrcItem'])* qty)))
            if not no_product :
                subtotal = line.subtotal if taxInclude else line.price_untaxed
                lines['MontoItem'] = int(round(subtotal,0))

            if no_product:
                lines['MontoItem'] = 0
            line_number += 1
            picking_lines.append(lines)
            if 'IndExe' in lines:
                taxInclude = False
        if len(picking_lines) == 0:
            raise UserError(_('No se puede emitir una guía sin líneas'))
        return {
                'Detalle': picking_lines,
                'MntExe': MntExe,
                'no_product':no_product,
                'tax_include': taxInclude,
                }

    def _dte(self, n_atencion=None):
        dte = {}
        if self.canceled and self.sii_xml_request:
            dte['Anulado'] = 2
        elif self.canceled:
            dte['Anulado'] = 1
        picking_lines = self._picking_lines()
        dte['Encabezado'] = self._encabezado(
            picking_lines['MntExe'],
            picking_lines['no_product'],
            picking_lines['tax_include'])
        lin_ref = 1
        ref_lines = []
        if n_atencion and self._context.get("set_pruebas", False):
            ref_line = {}
            ref_line['NroLinRef'] = lin_ref
            ref_line['TpoDocRef'] = "SET"
            ref_line['FolioRef'] = self.get_folio()
            ref_line['FchRef'] = datetime.strftime(datetime.now(), '%Y-%m-%d')
            ref_line['RazonRef'] = "CASO "+n_atencion+"-" + str(self.sii_batch_number)
            lin_ref = 2
            ref_lines.append(ref_line)
        for ref in self.reference:
            if ref.sii_referencia_TpoDocRef.sii_code in ['33','34']:#@TODO Mejorar Búsqueda
                inv = self.env["account.move"].search([('sii_document_number','=',str(ref.origen))])
            ref_line = {}
            ref_line['NroLinRef'] = lin_ref
            if  ref.sii_referencia_TpoDocRef:
                ref_line['TpoDocRef'] = ref.sii_referencia_TpoDocRef.sii_code
                ref_line['FolioRef'] = ref.origen
                ref_line['FchRef'] = datetime.strftime(datetime.now(), '%Y-%m-%d')
                if ref.date:
                    ref_line['FchRef'] = ref.date.strftime("%Y-%m-%d")
            ref_lines.append(ref_line)
            lin_ref += 1
        dte['Detalle'] = picking_lines['Detalle']
        dte['Referencia'] = ref_lines
        return dte

    def _get_datos_empresa(self, company_id):
        signature_id = self.env.user.get_digital_signature(company_id)
        if not signature_id:
            raise UserError(_('''There are not a Signature Cert Available for this user, please upload your signature or tell to someelse.'''))
        emisor = self._emisor()
        return {
            "Emisor": emisor,
            "firma_electronica": signature_id.parametros_firma(),
        }

    def _timbrar(self, n_atencion=None):
        folio = self.get_folio()
        datos = self._get_datos_empresa(self.company_id)
        datos['Documento'] = [{
            'TipoDTE': self.document_class_id.sii_code,
            'caf_file': [self.picking_type_id.warehouse_id.sequence_id.get_caf_file(
                            folio, decoded=False).decode()],
            'documentos': [self._dte(n_atencion)]
            },
        ]
        result = fe.timbrar(datos)
        if result[0].get('error'):
            raise UserError(result[0].get('error'))
        self.write({
            'sii_xml_dte': result[0]['sii_xml_dte'],
            'sii_barcode': result[0]['sii_barcode'],
        })

    def _crear_envio(self, n_atencion=False, RUTRecep="60803000-K"):
        grupos = {}
        count = 0
        company_id = False
        batch = 0
        for r in self.with_context(lang='es_CL'):
            batch += 1
            if not r.sii_batch_number or r.sii_batch_number == 0:
                r.sii_batch_number = batch #si viene una guía/nota regferenciando una factura, que por numeración viene a continuación de la guia/nota, será recahazada laguía porque debe estar declarada la factura primero
            if (
                self._context.get("set_pruebas", False) or r.sii_result == "Rechazado" or not r.sii_xml_dte
            ):
                r._timbrar(n_atencion)
            grupos.setdefault(r.document_class_id.sii_code, [])
            grupos[r.document_class_id.sii_code].append({
                        'NroDTE': r.sii_batch_number,
                        'sii_xml_request': r.sii_xml_dte,
                        'Folio': r.get_folio(),
                })
            if r.sii_result in ["Rechazado"] or (
                self._context.get("set_pruebas", False) and r.sii_xml_request.state in ["", "draft", "NoEnviado"]
            ):
                if r.sii_xml_request:
                    if len(r.sii_xml_request.picking_ids) == 1:
                        r.sii_xml_request.unlink()
                    else:
                        r.sii_xml_request = False
                r.sii_message = ''
        datos = self[0]._get_datos_empresa(self[0].company_id)
        datos.update({
            'api': False,
            'Documento': []
        })
        for k, v in grupos.items():
            datos['Documento'].append(
                {
                    'TipoDTE': k,
                    'documentos': v,
                }
            )
        return datos


    def do_dte_send(self, n_atencion=False):
        datos = self._crear_envio(n_atencion)
        envio_id = self[0].sii_xml_request
        if not envio_id:
            envio_id = self.env["sii.xml.envio"].create({
                'name': 'temporal',
                'xml_envio': 'temporal',
                'picking_ids': [[6,0, self.ids]],
                })
        datos["ID"] = "Env%s" %envio_id.id
        result = fe.timbrar_y_enviar(datos)
        envio = {
                'xml_envio': result.get('sii_xml_request', 'temporal'),
                'name': result.get("sii_send_filename", "temporal"),
                'company_id': self[0].company_id.id,
                'user_id': self.env.uid,
                'sii_send_ident': result['sii_send_ident'],
                'sii_xml_response': result.get('sii_xml_response'),
                'state': result.get('status'),
            }
        envio_id.write(envio)
        return envio_id

    def _get_dte_status(self):
        datos = self[0]._get_datos_empresa(self[0].company_id)
        datos['Documento'] = []
        docs = {}
        for r in self:
            if r.sii_xml_request.state not in ['Aceptado', 'Rechazado']:
                continue
            docs.setdefault(r.document_class_id.sii_code, [])
            docs[r.document_class_id.sii_code].append(r._dte())
        if not docs:
            return
        for k, v in docs.items():
            datos['Documento'].append ({
                'TipoDTE': k,
                'documentos': v
            })
        resultado = fe.consulta_estado_dte(datos)
        if not resultado:
            _logger.warning("no resultado en picking")
            return
        for r in self:
            id = "T{}F{}".format(r.document_class_id.sii_code,
                                 int(r.sii_document_number))
            r.sii_result = resultado[id]['status']
            if resultado[id].get('xml_resp'):
                r.sii_message = resultado[id].get('xml_resp')


    def ask_for_dte_status(self):
        for r in self:
            if not r.sii_xml_request and not r.sii_xml_request.sii_send_ident:
                raise UserError('No se ha enviado aún el documento, aún está en cola de envío interna en odoo')
            if r.sii_xml_request.state not in ['Aceptado', 'Rechazado']:
                r.sii_xml_request.with_context(
                    set_pruebas=self._context.get("set_pruebas", False)).get_send_status(r.env.user)
        try:
            self._get_dte_status()
        except Exception as e:
            _logger.warning("Error al obtener DTE Status Guía: %s" % str(e))


    def _get_printed_report_name(self):
        self.ensure_one()
        if self.document_class_id:
            string_state = ""
            if self.state == 'draft':
                string_state = "en borrador "
            report_string = "%s %s %s" % (self.document_class_id.name,
                                          string_state,
                                          self.sii_document_number or '')
        else:
            report_string = super(AccountInvoice, self)._get_printed_report_name()
        return report_string


    def getTotalDiscount(self):
        total_discount = 0
        for l in self.move_ids:
            qty = l.quantity_done
            if qty <= 0:
                qty = l.product_uom_qty
            total_discount +=  (((l.discount or 0.00) /100) * l.precio_unitario * qty)
        return self.currency_id.round(total_discount)


    def sii_header(self):
        W, H = (560, 255)
        img = Image.new('RGB', (W, H), color=(255,255,255))

        d = ImageDraw.Draw(img)
        w, h = (0, 0)
        for i in range(10):
            d.rectangle(((w, h), (550+w, 240+h)), outline="black")
            w += 1
            h += 1
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
        d.text((50,30), "R.U.T.: %s" % self.company_id.document_number, fill=(0,0,0), font=font)
        d.text((70,85), "Guía de Despacho", fill=(0,0,0), font=font)
        d.text((150,145), "Electrónica", fill=(0,0,0), font=font)
        d.text((220,195), "N° %s" % self.sii_document_number, fill=(0,0,0), font=font)
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)

        buffered = BytesIO()
        img.save(buffered, format="PNG")
        imm = base64.b64encode(buffered.getvalue()).decode()
        return imm


class Referencias(models.Model):
    _name = 'stock.picking.referencias'

    origen = fields.Char(
            string="Folio",
        )
    sii_referencia_TpoDocRef = fields.Many2one(
            'sii.document_class',
            string="Tipo Documento",
        )
    date = fields.Date(
            string="Fecha de la referencia",
        )
    stock_picking_id = fields.Many2one(
            'stock.picking',
            ondelete='cascade',
            index=True,
            copy=False,
            string="Documento",
        )
