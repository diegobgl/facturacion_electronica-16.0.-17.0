# -*- coding: utf-8 -*-

from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_secuencia_boleta = fields.Many2one(
            'ir.sequence',
            related="pos_config_id.secuencia_boleta",
            string='Secuencia Boleta',
            readonly=False)
    pos_secuencia_boleta_exenta = fields.Many2one(
            'ir.sequence',
            related="pos_config_id.secuencia_boleta_exenta",
            string='Secuencia Boleta Exenta',
            readonly=False)
    pos_habilita_factura_afecta = fields.Boolean(
            related="pos_config_id.habilita_factura_afecta",
            string='Secuencia Factura Afecta',
            readonly=False)
    pos_secuencia_factura = fields.Many2one(
            'ir.sequence',
            related="pos_config_id.secuencia_factura",
            string='Secuencia Factura',
        )
    pos_habilita_factura_exenta = fields.Boolean(
            related="pos_config_id.habilita_factura_exenta",
            string='Secuencia Factura Exenta',
            readonly=False)
    pos_secuencia_factura_exenta = fields.Many2one(
            'ir.sequence',
            related="pos_config_id.secuencia_factura_exenta",
            string='Secuencia Factura Exenta',
        )
    pos_habilita_nc = fields.Boolean(
            related="pos_config_id.habilita_nc",
            string='Secuencia Nota de crédito',
            readonly=False)
    pos_secuencia_nc = fields.Many2one(
            'ir.sequence',
            related="pos_config_id.secuencia_nc",
            string='Secuencia NC',
        )
    pos_ticket = fields.Boolean(
            related="pos_config_id.ticket",
            string="¿Facturas en Formato Ticket?",
            default=False,
            readonly=False)
    pos_marcar = fields.Selection(
        related="pos_config_id.marcar",
        string="Marcar por defecto",
        readonly=False)
    pos_restore_mode = fields.Boolean(
        related="pos_config_id.restore_mode",
        string="Restore Mode",
        default=False,
        readonly=False)
    pos_opciones_impresion = fields.Selection(
        related="pos_config_id.opciones_impresion",
        string="Opciones de Impresión",
        default="cliente",
        readonly=False)
    pos_dte_picking = fields.Boolean(
        related="pos_config_id.dte_picking",
        string="Emitir Guía de despacho Electrónica",
        readonly=False)
    pos_dte_picking_ticket = fields.Boolean(
        related="pos_config_id.dte_picking_ticket",
        string="Emitir Guía de despacho Electrónica",
        readonly=False)
    pos_dte_picking_move_type = fields.Selection(
            related="pos_config_id.dte_picking_move_type",
            string='Razón del traslado',
            default="1",
            readonly=False)
    pos_dte_picking_transport_type = fields.Selection(
            related="pos_config_id.dte_picking_transport_type",
            string="Tipo de Despacho",
            default="1",
            readonly=False)
    pos_dte_picking_sequence = fields.Many2one(
            'ir.sequence',
            related="pos_config_id.dte_picking_sequence",
            string='Secuencia Boleta',
            readonly=False)
    pos_dte_picking_option = fields.Selection(
            related="pos_config_id.dte_picking_option",
            string="Opción de emisión de despacho",
            default="all",
            readonly=False)
    pos_company_activity_ids = fields.Many2many(
        "partner.activities", related="company_id.company_activities_ids",
        readonly=False)
    pos_acteco_ids = fields.Many2many(
            'partner.activities',
            related="pos_config_id.acteco_ids",
            string="Código de Actividades",
            readonly=False)

    @api.onchange('pos_habilita_nc', 'pos_habilita_factura_afecta', 'pos_habilita_factura_exenta')
    def _update_sequences(self):
        self.pos_secuencia_nc = self.env['ir.sequence']
        if self.pos_habilita_nc:
            self.pos_secuencia_nc = self.env['ir.sequence'].search([
                ('sii_document_class_id.sii_code', '=', 61)
                ],
            limit=1)
        self.pos_secuencia_factura = self.env['ir.sequence']
        if self.pos_habilita_factura_afecta:
            self.pos_secuencia_factura = self.env['account.journal.sii_document_class'].search(
                [
                    ('journal_id', '=', self.pos_invoice_journal_id.id),
                    ('sii_document_class_id.sii_code', '=', 33),
                ],
            ).sequence_id
        self.pos_secuencia_factura_exenta = self.env['ir.sequence']
        if self.pos_habilita_factura_exenta:
            self.pos_secuencia_factura_exenta = self.env['account.journal.sii_document_class'].search(
                [
                    ('journal_id', '=', self.pos_invoice_journal_id.id),
                    ('sii_document_class_id.sii_code', '=', 34),
                ],
            ).sequence_id
