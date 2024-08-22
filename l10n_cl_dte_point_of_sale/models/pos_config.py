# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = "pos.config"

    def get_left_numbers(self):
        for rec in self:
            rec.left_number_exenta = rec.left_number_guia = rec.left_number = 0
            if rec.secuencia_boleta:
                rec.left_number = rec.secuencia_boleta.get_qty_available()
            if rec.secuencia_boleta_exenta:
                rec.left_number_exenta = rec.secuencia_boleta_exenta.get_qty_available()
            if rec.dte_picking_sequence:
                rec.left_number_guia = rec.dte_picking_sequence.get_qty_available()

    def _sii_sucursal(self):
        for rec in self:
            rec.sucursal_id = self.env['sii.sucursal']
            if 'sucursal_id' in rec.picking_type_id.default_location_src_id:
                rec.sucursal_id = rec.picking_type_id.default_location_src_id.sucursal_id

    @api.onchange('habilita_nc', 'habilita_factura_afecta', 'habilita_factura_exenta')
    def _secuencias(self):
        nc = self.env['ir.sequence'].search([('sii_document_class_id.sii_code', '=', 61)], limit=1)
        for r in self:
            r.secuencia_nc = self.env['ir.sequence']
            if r.habilita_nc:
                r.secuencia_nc = nc
            r.secuencia_factura = self.env['ir.sequence']
            if r.habilita_factura_afecta:
                r.secuencia_factura = self.env['account.journal.sii_document_class'].search(
                    [
                        ('journal_id', '=', r.invoice_journal_id.id),
                        ('sii_document_class_id.sii_code', '=', 33),
                    ],
                ).sequence_id
            r.secuencia_factura_exenta = self.env['ir.sequence']
            if r.habilita_factura_exenta:
                r.secuencia_factura_exenta = self.env['account.journal.sii_document_class'].search(
                    [
                        ('journal_id', '=', r.invoice_journal_id.id),
                        ('sii_document_class_id.sii_code', '=', 34),
                    ],
                ).sequence_id
            r.dte_picking_sequence = self.env['ir.sequence']
            if 'sequence_id' in r.picking_type_id.default_location_src_id:
                r.dte_picking_sequence = r.picking_type_id.default_location_src_id.sequence_id

    secuencia_boleta = fields.Many2one(
            'ir.sequence',
            string='Secuencia Boleta',
        )
    secuencia_boleta_exenta = fields.Many2one(
            'ir.sequence',
            string='Secuencia Boleta Exenta',
        )
    habilita_factura_afecta = fields.Boolean(
            string='Secuencia Factura Afecta',
            default=lambda self: bool(self.invoice_journal_id),
        )
    secuencia_factura = fields.Many2one(
            'ir.sequence',
            string='Secuencia Factura',
            compute='_secuencias',
        )
    habilita_factura_exenta = fields.Boolean(
            string='Secuencia Factura Exenta',
            default=False
        )
    secuencia_factura_exenta = fields.Many2one(
            'ir.sequence',
            string='Secuencia Factura Exenta',
            compute='_secuencias',
        )
    habilita_nc = fields.Boolean(
            string='Habilitar Nota de Crédito',
            default=False
        )
    secuencia_nc = fields.Many2one(
            'ir.sequence',
            string='Secuencia Nota de Crédito',
            compute='_secuencias',
        )
    ticket = fields.Boolean(
            string="¿Facturas en Formato Ticket?",
            default=False,
        )
    next_number = fields.Integer(
            related="secuencia_boleta.number_next_actual",
            string="Next Number",
        )
    next_number_exenta = fields.Integer(
            related="secuencia_boleta_exenta.number_next_actual",
            string="Next Number Exenta",
        )
    left_number = fields.Integer(
            compute="get_left_numbers",
            string="Folios restantes Boletas",
        )
    left_number_exenta = fields.Integer(
            compute="get_left_numbers",
            string="Folios restantes Boletas Exentas",
        )
    marcar = fields.Selection(
        [
            ('boleta', 'Boletas'),
            ('factura', 'Facturas'),
            ('boleta_exenta', 'Boletas Exentas'),
            ('factura_exenta', 'Facturas Exentas'),
        ],
        string="Marcar por defecto",
    )
    restore_mode = fields.Boolean(
        string="Restore Mode",
        default=False,
    )
    opciones_impresion = fields.Selection(
        [
            ('cliente', 'Solo Copia Cliente'),
            ('cedible', 'Solo Cedible'),
            ('cliente_cedible', 'Cliente y Cedible'),
        ],
        string="Opciones de Impresión",
        default="cliente",
    )
    dte_picking = fields.Boolean(
        string="Emitir Guía de despacho Electrónica",
    )
    dte_picking_ticket = fields.Boolean(
        string="Emitir Guía de despacho Electrónica",
    )
    dte_picking_move_type = fields.Selection(
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
        )
    dte_picking_transport_type = fields.Selection(
            [
                #('2', 'Despacho por cuenta de empresa'),
                ('1', 'Despacho por cuenta del cliente'),
                #('3', 'Despacho Externo'),
                #('0', 'Sin Definir')
            ],
            string="Tipo de Despacho",
            default="1",
        )
    dte_picking_sequence = fields.Many2one(
            'ir.sequence',
            string='Secuencia Boleta',
            compute='_secuencias'
        )
    dte_picking_option = fields.Selection(
            [
                ('all', 'Todos los pedidos'),
                ('no_tributarios', 'Solo a No Tributarios'),
            ],
            string="Opción de emisión de despacho",
            default="all",
        )
    next_number_guia = fields.Integer(
            related="dte_picking_sequence.number_next_actual",
            string="Next Number Guía",
        )
    left_number_guia = fields.Integer(
            compute="get_left_numbers",
            string="Folios restantes Guía",
        )
    sucursal_id = fields.Many2one(
        'sii.sucursal',
        string='Código Sucursal SII',
        compute='_sii_sucursal',
    )
    company_activity_ids = fields.Many2many("partner.activities", related="company_id.company_activities_ids")
    acteco_ids = fields.Many2many(
            'partner.activities',
            string="Código de Actividades",
        )

    @api.onchange('secuencia_boleta', 'secuencia_boleta_exenta')
    def validacion_cambio_secuencia(self):
        query = [
            ('rescue', '=', False),
            ('state', 'not in', ['closed']),
            ('config_id', '=', self.id),
        ]
        if self.env['pos.session'].sudo().search(query):
            raise UserError("No puede cambiar secuencia de boleta, estando abierta el punto de ventas")

    @api.onchange('iface_invoicing')
    def set_seq(self):
        self.habilita_factura_afecta = False
        self.habilita_factura_exenta = False
        for r in self.invoice_journal_id.journal_document_class_ids:
            if r.sii_document_class_id.sii_code == 33:
                self.habilita_factura_afecta = True
            if r.sii_document_class_id.sii_code == 34:
                self.habilita_factura_exenta = True
        self.habilita_nc = self.habilita_factura_afecta or \
                           self.habilita_factura_exenta or self.secuencia_boleta\
                           or self.secuencia_boleta_exenta

    @api.onchange('habilita_factura_afecta')
    def check_habilita_factura_afecta(self):
        factura_afecta = False
        for r in self.invoice_journal_id.journal_document_class_ids:
            if r.sii_document_class_id.sii_code == 33:
                factura_afecta = True
        if not factura_afecta:
            raise UserError("No tiene habilitado Folios de Factura Afecta en \
el diario %s" %self.invoice_journal_id.name)

    @api.onchange('habilita_factura_exenta')
    def check_habilita_factura_exenta(self):
        factura_exenta = False
        for r in self.invoice_journal_id.journal_document_class_ids:
            if r.sii_document_class_id.sii_code == 34:
                factura_exenta = True
        if not factura_exenta:
            raise UserError("No tiene habilitado Folios de Factura Afecta  en \
el diario %s" %self.invoice_journal_id.name)

    @api.constrains('marcar', 'secuencia_boleta', 'secuencia_boleta_exenta', 'iface_invoicing')
    def _check_document_type(self):
        if self.marcar == 'boleta' and not self.secuencia_boleta:
            raise ValidationError("Al marcar por defecto Boletas, "
                                  "debe seleccionar la Secuencia de Boletas, "
                                  "por favor verifique su configuracion")
        elif self.marcar == 'boleta_exenta' and not self.secuencia_boleta_exenta:
            raise ValidationError("Al marcar por defecto Boletas Exentas, "
                                  "debe seleccionar la Secuencia de Boletas Exentas, "
                                  "por favor verifique su configuracion")
        elif self.marcar == 'factura' and not self.iface_invoicing and not self.habilita_factura_afecta:
            raise ValidationError("Al marcar por defecto Facturas, "
                                  "debe activar el check de Facturación, "
                                  "por favor verifique su configuración")
        elif self.marcar == 'factura_exenta' and not self.iface_invoicing and not self.habilita_factura_exenta:
            raise ValidationError("Al marcar por defecto Facturas Exenta, "
                                  "debe activar el check de Facturación, "
                                  "por favor verifique su configuración")
