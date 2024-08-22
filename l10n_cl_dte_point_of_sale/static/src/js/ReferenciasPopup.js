odoo.define('l10n_cl_point_of_sale.ReferenciasPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    const { onMounted, useRef, useState } = owl;

    class ReferenciasPopup extends AbstractAwaitablePopup {
        /**
         * @param {Object} props
         * @param {string} props.startingValue
         */
        setup() {
            super.setup();
            this.tpo_ops = [];
            for(const op in this.env.pos.tpo_ops){
                if (this.env.pos.tpo_ops.hasOwnProperty(op)){
                    this.tpo_ops.push(this.env.pos.tpo_ops[op])
                }
            }
            this.is_refund = this.props.is_refund;
            this.document_class_ids = this.env.pos.document_classes;
            this.state = useState({
              folio: this.props.folio,
              dc_id: this.props.dc_id,
              tpo_op: this.props.tpo_op,
              motivo: this.props.motivo,
              fecha: this.props.fecha,
            });
            this.folioRef = useRef('input_folio');
            this.motivoRef = useRef('input_motivo');
            this.fechaRef = useRef('input_fecha');
            onMounted(this.onMounted);
        }
        onMounted() {
            this.folioRef.el.focus();
        }
        selectDC(dc) {
            this.state.dc_id = dc;
        }
        selectOp(op) {
            this.state.tpo_op = op;
        }
        getPayload() {
          return {
              folio: this.state.folio,
              dc_id: this.state.dc_id,
              tpo_op: this.state.tpo_op,
              motivo: this.state.motivo,
              fecha: this.state.fecha,
            }
        }
        confirm(){
            if (!this.state.folio){
                this.showPopup('ErrorPopup', {
                        title: this.env._t('Debe Ingresar Folio'),
                        body: this.env._t('Debe ingresar Folio Referencia.')
                    });
                return;
            }
            if (!this.state.dc_id){
                this.showPopup('ErrorPopup', {
                        title: this.env._t('Debe Seleccionar tipo documento'),
                        body: this.env._t('Debe Seleccionar el tipo de Documento Referencia.')
                    });
                return;
            }
            if(this.is_refund){
                if (!this.state.tpo_op){
                    this.showPopup('ErrorPopup', {
                            title: this.env._t('Debe Selecionar operación'),
                            body: this.env._t('Debe Seleccionar el tipo de Operación para la Referencia.')
                        });
                    return;
                }
                if (!this.state.motivo){
                    this.showPopup('ErrorPopup', {
                            title: this.env._t('Debe Ingresar Motivo'),
                            body: this.env._t('Debe ingresar el motivo de la Referencia.')
                        });
                    return;
                }
            }
            if (!this.state.fecha){
                this.showPopup('ErrorPopup', {
                        title: this.env._t('Debe Ingresar Fecha'),
                        body: this.env._t('Debe ingresar fecha del Documento de Referencia.')
                    });
                return;
            }
            super.confirm();
        }
    }
    ReferenciasPopup.template = 'ReferenciasPopup';
    ReferenciasPopup.defaultProps = {
        confirmText: _lt('Ok'),
        cancelText: _lt('Cancel'),
        title: 'Referencias DTE',
        body: 'Detalle de la referencia',
    };

    Registries.Component.add(ReferenciasPopup);

    return ReferenciasPopup;
});
