odoo.define('l10n_cl_point_of_sale.ReferenciasScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require("@web/core/utils/hooks");
    const { Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const { useState, onMounted } = owl;

    class ReferenciasScreen extends PosComponent {
        setup() {
            super.setup();
            useListener('crear-referencia', this.crearReferencia);
            useListener('click-line', this.onClickLine);
            useListener('delete-line', this.onClickDeleteLine);
            this.state = useState({
                highlighted: false,
            });
        }
        onClickLine(line){
            this.state.highlighted = line.sequence;
        }
        onClickDeleteLine({ detail: line }) {
            if (line ) {
                this.currentOrder.removeReferencia(line);
            }
        }
        isHighlighted(line){
            return line.sequence === this.state.highlighted
        }
        shouldHideDeleteButton(line){
            return false;
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        getReferenciasList() {
            return this.currentOrder.referencias;
        }
        getDC(line){
          if (line && line.sii_referencia_TpoDocRef){
              return line.sii_referencia_TpoDocRef.name
            }
          return ''
        }
        getFolio(line){
            return line.origen;
        }
        getTPO(line){
            if(!line || !line.sii_referencia_CodRef){
                return ''
            }
            return this.env.pos.tpo_ops[line.sii_referencia_CodRef].label;
        }
        getMotivo(line){
            return line.motivo;
        }
        getFecha(line){
            return moment(line.fecha_documento).format('DD-MM-YYYY');
        }
        back() {
            this.showScreen('ProductScreen');
        }
        async crearReferencia(){
            let order = this.currentOrder;
            const { confirmed, payload } = await this.showPopup(
                'ReferenciasPopup',
                {
                    is_refund: order.es_nc(),
                    tpo_op: '1',
                }
            );
            if (!confirmed) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Debe Agregar referencia'),
                    body: this.env._t('Es obligatoria para NC agregar Referencia. Se eliminará esta NC.')
                });
                return;
            }
            for(const refLine of order.referencias){
              if(refLine.origen === payload.folio && refLine.sii_referencia_TpoDocRef.id === payload.dc_id.id){
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Referencia Existente'),
                    body: this.env._t('Ya existe este folio como referencia en esta NC.')
                });
                return;
              }
            }
            let referencia = {
                sequence: order.referencias.length+1,
                origen: payload.folio,
                sii_referencia_TpoDocRef: payload.dc_id,
                fecha_documento: payload.fecha,
              }
            if(order.es_nc()){
                referencia.sii_referencia_CodRef= payload.tpo_op;
                referencia.motivo = payload.motivo;
            }
            order.referencias.push(referencia);
        }
    }
    ReferenciasScreen.template = 'ReferenciasScreen';

    Registries.Component.add(ReferenciasScreen);

    return ReferenciasScreen;
});
