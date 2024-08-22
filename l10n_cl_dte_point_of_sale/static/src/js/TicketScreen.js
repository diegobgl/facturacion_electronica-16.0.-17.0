odoo.define('l10n_cl_dte_point_of_sale.TicketScreen', function (require) {
"use strict";

  var TicketScreen = require('point_of_sale.TicketScreen');
  const { _t } = require('web.core');
  const Registries = require('point_of_sale.Registries');

  const FETicketScreen = (TicketScreen) =>
      class extends TicketScreen {

        async _onDoRefund() {
            const order = this.getSelectedSyncedOrder();

            if (!order) {
                this._state.ui.highlightHeaderNote = !this._state.ui.highlightHeaderNote;
                return;
            }

            if (this._doesOrderHaveSoleItem(order)) {
                if (!this._prepareAutoRefundOnOrder(order)) {
                    // Don't proceed on refund if preparation returned false.
                    return;
                }
            }

            const partner = order.get_partner();

            const allToRefundDetails = this._getRefundableDetails(partner);
            if (allToRefundDetails.length == 0) {
                this._state.ui.highlightHeaderNote = !this._state.ui.highlightHeaderNote;
                return;
            }

            // The order that will contain the refund orderlines.
            // Use the destinationOrder from props if the order to refund has the same
            // partner as the destinationOrder.
            const destinationOrder =
                this.props.destinationOrder &&
                partner === this.props.destinationOrder.get_partner() &&
                !this.env.pos.doNotAllowRefundAndSales()
                    ? this.props.destinationOrder
                    : this._getEmptyOrder(partner);

            //Add a check too see if the fiscal position exist in the pos
            if (order.fiscal_position_not_found) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Fiscal Position not found'),
                    body: this.env._t('The fiscal position used in the original order is not loaded. Make sure it is loaded by adding it in the pos configuration.')
                });
                return;
            }

            // Add orderline for each toRefundDetail to the destinationOrder.
            for (const refundDetail of allToRefundDetails) {
                const product = this.env.pos.db.get_product_by_id(refundDetail.orderline.productId);
                const options = this._prepareRefundOrderlineOptions(refundDetail);
                await destinationOrder.add_product(product, options);
                refundDetail.destinationOrderUid = destinationOrder.uid;
            }
            destinationOrder.fiscal_position = order.fiscal_position;

            // Set the partner to the destinationOrder.
            if (partner && !destinationOrder.get_partner()) {
                destinationOrder.set_partner(partner);
                destinationOrder.updatePricelist(partner);
            }

            if (this.env.pos.get_order().cid !== destinationOrder.cid) {
                this.env.pos.set_order(destinationOrder);
            }

            let crear_nc = order.es_tributaria();
            if (crear_nc){
                destinationOrder.set_nc();
                const { confirmed, payload } = await this.showPopup(
                    'ReferenciasPopup',
                    {
                        is_refund: true,
                        folio: order.sii_document_number,
                        dc_id: order.document_class_id,
                        tpo_op: '1',
                        fecha: moment(order.validation_date).format('YYYY-MM-DD'),
                    }
                );
                if (!confirmed) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Debe Agregar referencia'),
                        body: this.env._t('Es obligatoria para NC agregar Referencia. Se eliminará esta NC.')
                    });
                    this.env.pos.removeOrder(destinationOrder);
                    return;
                }
                if (payload.tpo_op === '1'){
                  if (destinationOrder.orderlines.length !== order.orderlines.length){
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Error Consistencia'),
                        body: this.env._t('Para anulación, debe ser la misma cantidad de líneas que la referencia')
                    });
                    this.env.pos.removeOrder(destinationOrder);
                    return;
                  }
                  if (destinationOrder.get_total_with_tax()*-1 !== order.get_total_with_tax()){
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Error Consistencia'),
                        body: this.env._t('Para anulación, debe ser el mismo valor final que la referencia')
                    });
                    this.env.pos.removeOrder(destinationOrder);
                    return;
                  }
                }
                else if (payload.tpo_op === '2'){
                  if (destinationOrder.orderlines.length > 1 || destinationOrder.orderlines[0].product_id.code === 'NO_PRODUCT'){
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Error Consistencia'),
                        body: this.env._t('Para modifica Texto, solo puede ir línea código especial modifica texto')
                    });
                    this.env.pos.removeOrder(destinationOrder);
                    return;
                  }
                }
                for(const refLine of destinationOrder.referencias){
                  if(refLine.origen === order.sii_document_number && refLine.sii_referencia_TpoDocRef.id === order.document_class_id.id){
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Referencia Existente'),
                        body: this.env._t('Ya existe este folio como referencia en esta NC.')
                    });
                    this.env.pos.removeOrder(destinationOrder);
                    return;
                  }
                }
                let referencia = {
                    sequence: destinationOrder.referencias.length+1,
                    origen: payload.folio,
                    sii_referencia_TpoDocRef: payload.dc_id,
                    sii_referencia_CodRef: payload.tpo_op,
                    motivo: payload.motivo,
                    fecha_documento: payload.fecha,
                  }
                destinationOrder.referencias.push(referencia);
            }

            this._onCloseScreen();
        }

        _computeSyncedOrdersDomain() {
            let vals = super._computeSyncedOrdersDomain(...arguments);
            const { fieldName, searchTerm } = this._state.ui.searchDetails;
            if (fieldName === 'RECEIPT_NUMBER' && searchTerm)
            {
              vals.unshift('|');
              vals.push(['sii_document_number', 'ilike', `%${searchTerm}%`]);
            }
            return vals;
        }

        getDC(order){
          if (order && order.document_class_id){
              return order.document_class_id.name
            }
          return ''
        }

        getNumber(order){
            if (!order){
                return ''
            }
            return order.sii_document_number || order.name;
        }

        getSIIResult(order){
            if (!order || !order.sii_result){
                return ''
            }
            return _t(order.sii_result);
        }

      }
      Registries.Component.extend(TicketScreen, FETicketScreen);

      return FETicketScreen;
});
