odoo.define('l10n_cl_dte_point_of_sale.PaymentScreen', function(require) {
  "use strict";

  var PaymentScreen = require('point_of_sale.PaymentScreen');
  const Registries = require('point_of_sale.Registries');
  const { isConnectionError } = require('point_of_sale.utils');

  const FEPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
      setup(){
        super.setup();
        this.env.pos.update_sequences();
      }

      async _finalizeValidation() {
            if ((this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change()) && this.env.pos.config.iface_cashdrawer) {
                this.env.proxy.printer.open_cashbox();
            }

            this.currentOrder.initialize_validation_date();
            this.currentOrder.finalized = true;

            let syncOrderResult, hasError;

            try {
                // 1. Save order to server.
                syncOrderResult = await this.env.pos.push_single_order(this.currentOrder);

                // 2. Invoice.
                if (this.currentOrder.is_to_invoice()) {
                    if (syncOrderResult.length) {
                        await this.env.legacyActionManager.do_action('account.account_invoices', {
                            additional_context: {
                                active_ids: [syncOrderResult[0].account_move],
                            },
                        });
                    } else {
                        throw { code: 401, message: 'Backend Invoice', data: { order: this.currentOrder } };
                    }
                }

                // 3. Post process.
                if (syncOrderResult.length && this.currentOrder.wait_for_push_order()) {
                    const postPushResult = await this._postPushOrderResolve(
                        this.currentOrder,
                        syncOrderResult.map((res) => res.id)
                    );
                    if (!postPushResult) {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Error: no internet connection.'),
                            body: this.env._t('Some, if not all, post-processing after syncing order failed.'),
                        });
                    }
                    if (this.currentOrder.es_factura() || this.currentOrder.es_nc()){
                      this.currentOrder.sii_document_number = syncOrderResult[0].sii_document_number;
                      this.currentOrder.signature = syncOrderResult[0].sii_barcode;
                      let seq = this.env.pos.seq_by_sii_code[this.currentOrder.document_class_id.sii_code];
                      seq.start_number += 1;
                      this.env.pos.set_next_number(seq, seq.start_number);
                      if (!this.currentOrder.sii_document_number) {
                        this.showPopup('ErrorPopup', {
                          'title': "Sin Folios disponibles",
                          'body': _.str.sprintf("No hay CAF por lo que no se pudo timbrar %(document)s " +
                            "Solicite un nuevo CAF en el sitio www.sii.cl o utilice el asistente apicaf desde la secuencia", {
                              document: this.currentOrder.document_class_id.name
                            })
                        });
                        return false;
                      }
                    }
                }
            } catch (error) {
                if (error.code == 700 || error.code == 701)
                    this.error = true;

                if ('code' in error) {
                    // We started putting `code` in the rejected object for invoicing error.
                    // We can continue with that convention such that when the error has `code`,
                    // then it is an error when invoicing. Besides, _handlePushOrderError was
                    // introduce to handle invoicing error logic.
                    await this._handlePushOrderError(error);
                } else {
                    // We don't block for connection error. But we rethrow for any other errors.
                    if (isConnectionError(error)) {
                        this.showPopup('OfflineErrorPopup', {
                            title: this.env._t('Connection Error'),
                            body: this.env._t('Order is not synced. Check your internet connection'),
                        });
                    } else {
                        throw error;
                    }
                }
            } finally {
                // Always show the next screen regardless of error since pos has to
                // continue working even offline.
                this.showScreen(this.nextScreen);
                // Remove the order from the local storage so that when we refresh the page, the order
                // won't be there
                this.env.pos.db.remove_unpaid_order(this.currentOrder);

                // Ask the user to sync the remaining unsynced orders.
                if (!hasError && syncOrderResult && this.env.pos.db.get_orders().length) {
                    const { confirmed } = await this.showPopup('ConfirmPopup', {
                        title: this.env._t('Remaining unsynced orders'),
                        body: this.env._t(
                            'There are unsynced orders. Do you want to sync these orders?'
                        ),
                    });
                    if (confirmed) {
                        // NOTE: Not yet sure if this should be awaited or not.
                        // If awaited, some operations like changing screen
                        // might not work.
                        this.env.pos.push_orders();
                    }
                }
            }
        }
      async _isOrderValid(isForceValidate) {
        let dc = this.currentOrder.document_class_id;
        if (dc && dc.qty_available < 1) {
          await this.env.pos.update_sequences();
          //validar que el numero emitido no supere el maximo del folio
          if (dc.qty_available < 1) {
            this.showPopup('ErrorPopup', {
              'title': "Sin Folios disponibles",
              'body': _.str.sprintf("No hay CAF para el folio de %(document)s: %(document_number)s " +
                "Solicite un nuevo CAF en el sitio www.sii.cl o utilice el asistente apicaf desde la secuencia", {
                  document: dc.name,
                  document_number: dc.next_number,
                })
            });
            return false;
          }
        }
        var res = super._isOrderValid(...arguments);
        if (res && this.currentOrder.es_tributaria()) {
          for (let line of this.paymentLines) {
            if(line.payment_method.restrict_no_dte){
              this.showPopup('ErrorPopup', {
                  title: this.env._t('Restricción'),
                  body: this.env._t('No puede usar este medio de pago en DTE')
              });
              return false;
            }
          }
          let es_nc = this.currentOrder.es_nc();
          if (!es_nc) {
            if (!dc.caf_file && this.currentOrder.es_boleta()) {
              this.showPopup('ErrorPopup', {
                  title: this.env._t('Error en CAF'),
                  body: this.env._t('No se ecuentra el CAF para el folio: ') + dc.next_number
              });
              return false;
            }
            let amount = Math.round(this.currentOrder.get_total_with_tax());
            if (amount === 0) {
              this.showPopup('ErrorPopup', {
                'title': "Error de integridad",
                'body': "Para emisión, debe el monto ser mayor a 0",
              });
              return false;
            }
            var total_tax = this.currentOrder.get_total_tax();
            if ((this.currentOrder.es_boleta_exenta() || this.currentOrder.es_factura_exenta()) && total_tax > 0) {
              this.showPopup('ErrorPopup', {
                'title': "Error de integridad",
                'body': "No pueden haber productos afectos en boleta/factura exenta",
              });
              return false;
            } else if ((this.currentOrder.es_boleta_afecta() || this.currentOrder.es_factura_afecta()) && total_tax <= 0) {
              this.showPopup('ErrorPopup', {
                'title': "Error de integridad",
                'body': "Debe haber almenos un producto afecto",
              });
              return false;
            };
          } else {
            if (this.currentOrder.referencias.length === 0) {
              this.showPopup('ErrorPopup', {
                'title': "Error de integridad",
                'body': "Una NC debe llevar una referencia como mínimo",
              });
              return false;
            }
          };
          for (const line of this.currentOrder.orderlines) {
            if (es_nc && line.get_price_without_tax() > 0) {
              this.showPopup('ErrorPopup', {
                'title': "Error de integridad",
                'body': "No pueden ir valores Positivos en Una NC",
              });
              return false;
            } else if (!es_nc && line.get_price_without_tax() < 0) {
              this.showPopup('ErrorPopup', {
                'title': "Error de integridad",
                'body': "No pueden ir valores negativos",
              });
              return false;
            }
          }
          if ((this.currentOrder.is_to_invoice() || this.currentOrder.crear_guia()) && this.currentOrder.get_partner()) {
            var partner = this.currentOrder.get_partner();
            if (!partner.street) {
              this.showPopup('ErrorPopup', {
                'title': 'Datos de Cliente Incompletos',
                'body': 'El Cliente seleccionado no tiene la dirección, por favor verifique',
              });
              return false;
            }
            if (!partner.document_number) {
              this.showPopup('ErrorPopup', {
                'title': 'Datos de Cliente Incompletos',
                'body': 'El Cliente seleccionado no tiene RUT, por favor verifique',
              });
              return false;
            }
            if (!partner.activity_description) {
              this.showPopup('ErrorPopup', {
                'title': 'Datos de Cliente Incompletos',
                'body': 'El Cliente seleccionado no tiene Giro, por favor verifique',
              });
              return false;
            }
          }
          if (!es_nc && Math.abs(this.currentOrder.get_total_with_tax() <= 0)) {
            this.showPopup('ErrorPopup', {
              'title': 'Orden con total 0',
              'body': 'No puede emitir Pedidos con total 0, por favor asegurese que agrego lineas y que el precio es mayor a cero',
            });
            return false;
          }
        }
        return res;
      }

      unset_boleta() {
        this.currentOrder.unset_boleta();
      }

      click_boleta() {
        this.currentOrder.set_to_invoice(false);
        if (this.env.pos.pos_session.caf_files && !this.currentOrder.es_boleta_afecta()) {
          this.currentOrder.set_tipo(this.env.pos.config.secuencia_boleta.sii_document_class_id);
        } else {
          this.unset_boleta();
        }
        this.render();
      }

      click_boleta_exenta() {
        this.currentOrder.set_to_invoice(false);
        if (this.env.pos.pos_session.caf_files_exentas && !this.currentOrder.es_boleta_exenta()) {
          this.currentOrder.set_tipo(this.env.pos.config.secuencia_boleta_exenta.sii_document_class_id);
        } else {
          this.unset_boleta();
        }
        this.render();
      }

      toggleIsToInvoice() {
        this.unset_boleta();
        if (!this.env.pos.config.habilita_factura_afecta) {
          this.showPopup('ErrorPopup', {
            'title': "No ha seleccionado secuencia de facturas",
          })
        } else {
          this.currentOrder.set_to_invoice(!this.currentOrder.is_to_invoice());
          if (this.currentOrder.is_to_invoice()) {
            this.currentOrder.set_factura_afecta();
          } else {
            this.currentOrder.unset_tipo();
          }
        }
        this.render();
      }

      click_factura_exenta() {
        this.unset_boleta();
        this.currentOrder.set_to_invoice(!this.currentOrder.is_to_invoice());
        if (this.currentOrder.is_to_invoice()) {
          this.currentOrder.set_factura_exenta();
        } else {
          this.currentOrder.unset_tipo();
        }
        this.render();
      }

    }
  Registries.Component.extend(PaymentScreen, FEPaymentScreen);

  return FEPaymentScreen;
});
