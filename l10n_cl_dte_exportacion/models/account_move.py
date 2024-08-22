# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.addons.l10n_cl_fe.models.currency import float_round_custom as round
import logging
_logger = logging.getLogger(__name__)


class Exportacion(models.Model):
    _inherit = "account.move"

    pais_destino = fields.Many2one(
        'aduanas.paises',
        string='País de Destino',
        readonly=False,
    )
    puerto_embarque = fields.Many2one(
        'aduanas.puertos',
        string='Puerto Embarque',
        readonly=False,
    )
    puerto_desembarque = fields.Many2one(
        'aduanas.puertos',
        string='Puerto de Desembarque',
        readonly=False,
    )
    via = fields.Many2one(
        'aduanas.tipos_transporte',
        string='Vía',
        readonly=False,
    )
    carrier_id = fields.Many2one(
        'delivery.carrier',
        string="Transporte",
        readonly=False,
    )
    tara = fields.Integer(
        string="Tara",
        readonly=False,
    )
    uom_tara = fields.Many2one(
        'uom.uom',
        string='Unidad Medida Tara',
        readonly=False,
    )
    peso_bruto = fields.Float(
        string="Peso Bruto",
        readonly=False,
    )
    uom_peso_bruto = fields.Many2one(
        'uom.uom',
        string='Unidad Medida Peso Bruto',
        readonly=False,
    )
    peso_neto = fields.Float(
        string="Peso Neto",
        readonly=False,
    )
    uom_peso_neto = fields.Many2one(
        'uom.uom',
        string='Unidad Medida Peso Neto',
        readonly=False,
    )
    total_items = fields.Integer(
        string="Total Items",
        readonly=False,
    )
    total_bultos = fields.Integer(
        string="Total Bultos",
        readonly=False,
    )
    monto_flete = fields.Monetary(
        string="Monto Flete",
        readonly=False,
    )
    monto_seguro = fields.Monetary(
        string="Monto Seguro",
        readonly=False,
    )
    pais_recepcion = fields.Many2one(
        'aduanas.paises',
        string='País de Recepción',
        readonly=False,
    )
    chofer_id = fields.Many2one(
            'res.partner',
            string="Chofer"
        )
    bultos = fields.One2many(
        string="Bultos",
        comodel_name="account.move.bultos",
        inverse_name="move_id",
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string="Movimiento Relacionado",
        readonly=False,
    )

    @api.onchange('carrier_id')
    def set_chofer(self):
        if self.carrier_id and not self.chofer_id:
            self.chofer_id = self.carrier_id.partner_id

    @api.onchange('pais_destino')
    def set_recepcion(self):
        if not self.pais_recepcion:
            self.pais_recepcion = self.pais_destino

    def _es_nc_exportacion(self):
        return self.document_class_id.es_nc_exportacion()

    def _es_exportacion(self):
        return self.document_class_id.es_exportacion()

    def _totales(self, resumen):
        if not resumen['product'] or not self._es_exportacion():
            return super(Exportacion, self)._totales(resumen)
        totales = dict(MntExe=0, MntNeto=0, MntIVA=0, TasaIVA=0,
                       MntTotal=0, MntBase=0, MntRet=0, MontoNF=0, OtrosImp=0,
                       CredEC=0)
        if self.move_type == 'entry' or self.is_outbound():
            sign = 1
        else:
            sign = -1
        currency_base = self.currency_base()
        another_currency_id = self.currency_target()
        gdr = 0
        for r in self.line_ids.filtered(lambda line: line.display_type in ['D', 'R']):
            if another_currency_id and currency_base != another_currency_id:
                gdr += r.amount_currency * sign
            else:
                gdr += r.balance * sign
        totales['MntNeto'] = gdr + sum(line['MontoItem'] for line in resumen['Detalle']) - resumen['MontoNF']
        totales['MntExe'] = totales['MntTotal'] = totales['MntNeto']
        return totales

    def currency_base(self):
        if self._es_exportacion():
            return self.currency_id
        return super(Exportacion, self).currency_base()

    def currency_target(self):
        if self._es_exportacion():
            return self.env.ref('base.CLP').with_context(date=self.invoice_date)
        return super(Exportacion, self).currency_target()

    def _totales_normal(self, currency_id, totales):
        if not self._es_exportacion():
            return super(Exportacion, self)._totales_normal(currency_id, totales)
        if totales['MntIVA'] > 0 or totales['MntExe'] == 0:
            raise UserError("Deben ser todos los productos Exentos!")
        Totales = {}
        if currency_id:
            Totales['TpoMoneda'] = currency_id.abreviatura
        Totales['MntExe'] = totales['MntExe']
        Totales['MntTotal'] = totales['MntTotal']
        return Totales

    def _totales_otra_moneda(self, currency_id, totales):
        if not self._es_exportacion():
            return super(Exportacion, self)._totales_otra_moneda(currency_id,
                                                                totales)
        Totales = {}
        #CLP
        currency_target = self.currency_target()
        Totales['TpoMoneda'] = self._acortar_str(currency_target.abreviatura, 15)
        base = self.currency_base()
        Totales['TpoCambio'] =  round(base._convert(currency_target.rate,
                                                    currency_target,
                                                    self.company_id,
                                                    self.invoice_date), 4)
        MntExe = totales['MntExe']
        if MntExe and currency_target:
            MntExe = base._convert(totales['MntExe'],
                      currency_target,
                      self.company_id,
                      self.invoice_date)
        Totales['MntExeOtrMnda'] = MntExe
        MntTotal = totales['MntTotal']
        if currency_target:
            MntTotal = base._convert(totales['MntTotal'],
                                     currency_target,
                                     self.company_id,
                                     self.invoice_date)
        Totales['MntTotOtrMnda'] = MntTotal
        return Totales

    def _id_doc(self, resumen):
        res = super(Exportacion, self)._id_doc(resumen)
        if self._es_exportacion() and self.invoice_payment_term_id.forma_pago_aduanas:
            res['FmaPagExp'] = self.invoice_payment_term_id.forma_pago_aduanas.code
        return res

    def _receptor(self):
        if not self._es_exportacion():
            return super(Exportacion, self)._receptor()
        Receptor = {}
        commercial_partner_id = self.commercial_partner_id or self.partner_id.commercial_partner_id
        Receptor['RUTRecep'] = '55.555.555-5'
        Receptor['RznSocRecep'] = self._acortar_str( commercial_partner_id.name, 100)
        GiroRecep = self.acteco_id.name or commercial_partner_id.activity_description.name
        if GiroRecep:
            Receptor['GiroRecep'] = self._acortar_str(GiroRecep, 40)
        if self.partner_id.phone or commercial_partner_id.phone:
            Receptor['Contacto'] = self._acortar_str(self.partner_id.phone or commercial_partner_id.phone or self.partner_id.email, 80)
        if (commercial_partner_id.email or commercial_partner_id.dte_email or self.partner_id.email or self.partner_id.dte_email):
            Receptor['CorreoRecep'] = commercial_partner_id.dte_email or self.partner_id.dte_email or commercial_partner_id.email or self.partner_id.email
        street_recep = (self.partner_id.street or commercial_partner_id.street or False)
        if not street_recep:
        # or self.indicador_servicio in [1, 2]:
            raise UserError('Debe Ingresar dirección del cliente')
        street2_recep = (self.partner_id.street2 or commercial_partner_id.street2 or False)
        if street_recep or street2_recep:
            Receptor['DirRecep'] = self._acortar_str(street_recep + (' ' + street2_recep if street2_recep else ''), 70)
        cmna_recep = self.partner_id.city_id.name or commercial_partner_id.city_id.name
        if cmna_recep:
            Receptor['CmnaRecep'] = cmna_recep
        ciudad_recep = self.partner_id.city or commercial_partner_id.city
        if ciudad_recep:
            Receptor['CiudadRecep'] = ciudad_recep
        Receptor['Nacionalidad'] = self.partner_id.commercial_partner_id.country_id.aduanas_id.code
        return Receptor

    def _validaciones_uso_dte(self):
        super(Exportacion,self)._validaciones_uso_dte()
        if self._es_exportacion():
            if self.invoice_incoterm_id and not self.invoice_payment_term_id:
                raise UserError("Debe Ingresar un Término de Pago")
            if not self.invoice_payment_term_id.modalidad_venta and not self._es_nc_exportacion() and not self.document_class_id.es_nd_exportacion():
                raise UserError("Debe indicar Modalidad de venta")
            if self.ind_servicio in [3, 4, 5] and self.invoice_payment_term_id.modalidad_venta.code != '1':
                raise UserError("La modalidad de venta del plazo de pago debe ser 1.- A FIRME")

    def get_monto_clausula(self):
        for k, terms in self.needed_terms.items():
            if k['move_id']==self.id:
                amount = round(terms['amount_currency'], 2)
                return amount if amount > 0 else amount *-1
        return 0

    def _bultos(self, bultos):
        Bultos = []
        for b in bultos:
            Bulto = dict()
            Bulto['CodTpoBultos'] = b.tipo_bulto.code
            Bulto['CantBultos'] = b.cantidad_bultos
            if b.marcas:
                Bulto['Marcas'] = b.marcas
            if b.id_container:
                Bulto['IdContainer'] = b.id_container
                Bulto['Sello'] = b.sello
                Bulto['EmisorSello'] = b.emisor_sello
            Bultos.append(Bulto)
        return Bultos

    def _aduana(self):
        Aduana = {}
        Aduana['CodModVenta'] = self.invoice_payment_term_id.modalidad_venta.code
        if self.invoice_incoterm_id:
            Aduana['CodClauVenta'] = self.invoice_incoterm_id.aduanas_code
        if self.invoice_payment_term_id:
            Aduana['TotClauVenta'] = self.get_monto_clausula()
        if self.via:
            Aduana['CodViaTransp'] = self.via.code
        if self.chofer_id:
            Aduana['NombreTransp'] = self.chofer_id.name
        if self.carrier_id:
            Aduana['RUTCiaTransp'] = self.carrier_id.partner_id.rut()
        if self.carrier_id:
            Aduana['NomCiaTransp'] = self.carrier_id.name
        #Aduana['IdAdicTransp'] = self.indicador_adicional
        if self.puerto_embarque:
            Aduana['CodPtoEmbarque'] = self.puerto_embarque.code
        #Aduana['IdAdicPtoEmb'] = self.ind_puerto_embarque
        if self.puerto_desembarque:
            Aduana['CodPtoDesemb'] = self.puerto_desembarque.code
        #Aduana['IdAdicPtoDesemb'] = self.ind_puerto_desembarque
        if self.tara:
            Aduana['Tara'] = self.tara
        if self.uom_tara.code:
            Aduana['CodUnidMedTara'] = self.uom_tara.code
        if self.peso_bruto:
            Aduana['PesoBruto'] = round(self.peso_bruto, 2)
        if self.uom_peso_bruto.code:
            Aduana['CodUnidPesoBruto'] = self.uom_peso_bruto.code
        if self.peso_neto:
            Aduana['PesoNeto'] = round(self.peso_neto, 2)
        if self.uom_peso_neto.code:
            Aduana['CodUnidPesoNeto'] = self.uom_peso_neto.code
        if self.total_items:
            Aduana['TotItems'] = self.total_items
        if self.total_bultos:
            Aduana['TotBultos'] = self.total_bultos
            Aduana['Bultos'] = self._bultos(self.bultos)
        #Aduana['Marcas'] =
        #Solo si es contenedor
        #Aduana['IdContainer'] =
        #Aduana['Sello'] =
        #Aduana['EmisorSello'] =
        if self.monto_flete:
            Aduana['MntFlete'] = self.monto_flete
        if self.monto_seguro:
            Aduana['MntSeguro'] = self.monto_seguro
        if self.pais_recepcion:
            Aduana['CodPaisRecep'] = self.pais_recepcion.code
        if self.pais_destino:
            Aduana['CodPaisDestin'] = self.pais_destino.code
        return Aduana

    def _transporte(self):
        Transporte = {}
        if self.carrier_id:
            if self.patente:
                Transporte['Patente'] = self.patente[:8]
            elif self.vehicle:
                Transporte['Patente'] = self.vehicle.matricula or ''
            if self.transport_type in [2, 3] and self.chofer:
                if not self.chofer.vat:
                    raise UserError("Debe llenar los datos del chofer")
                if self.transport_type == 2:
                    Transporte['RUTTrans'] = self.company_id.rut()
                else:
                    if not self.carrier_id.partner_id.vat:
                        raise UserError("Debe especificar el RUT del transportista, en su ficha de partner")
                    Transporte['RUTTrans'] = self.carrier_id.partner_id.rut()
                if self.chofer:
                    Transporte['Chofer'] = {}
                    Transporte['Chofer']['RUTChofer'] = self.chofer.rut()
                    Transporte['Chofer']['NombreChofer'] = self.chofer.name[:30]
        if not self._es_exportacion():
            partner_id = self.partner_id or self.company_id.partner_id
            Transporte['DirDest'] = (partner_id.street or '')+ ' '+ (partner_id.street2 or '')
            Transporte['CmnaDest'] = partner_id.state_id.name or ''
            Transporte['CiudadDest'] = partner_id.city or ''
        Transporte['Aduana'] = self._aduana()
        return Transporte

    def _encabezado(self, resumen):
        res = super(Exportacion, self)._encabezado(resumen)
        if self._es_exportacion():
            if self.ind_servicio != 4:
                res['Transporte'] = self._transporte()
            elif not self.ind_servicio:
                raise UserError("Si es una factura de exportación, debe indicar el tipo de servicio")
        return res

    @api.onchange('monto_flete', 'monto_seguro')
    def _set_seguros(self):
        if self.monto_flete:
            flete = self.env['account.move.gdr'].search([
                ('type', '=', 'R'),
                ('move_id', '=', self.id),
                ('aplicacion', '=', 'flete'),
            ])
            if not flete:
                flete = self.env['account.move.gdr'].create({
                    'type': 'R',
                    'move_id': self.id,
                    'aplicacion': 'flete',
                    'impuesto': 'exentos',
                    'gdr_detail': 'Flete',
                    'gdr_type': 'amount',
                })
                flete.valor = self.monto_flete
        if self.monto_seguro:
            seguro = self.env['account.move.gdr'].search([
                ('type', '=', 'R'),
                ('move_id', '=', self.id),
                ('aplicacion', '=', 'seguro'),
            ])
            if not seguro:
                seguro = self.env['account.move.gdr'].create({
                    'type': 'R',
                    'move_id': self.id,
                    'aplicacion': 'seguro',
                    'impuesto': 'exentos',
                    'gdr_detail': 'Seguro',
                    'gdr_type': 'amount',
                })
            seguro.valor = self.monto_seguro

    @api.onchange('bultos')
    def tot_bultos(self):
        tot_bultos = 0
        for b in self.bultos:
            tot_bultos += b.cantidad_bultos
        self.total_bultos = tot_bultos
