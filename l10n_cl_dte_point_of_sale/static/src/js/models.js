odoo.define('l10n_cl_dte_point_of_sale.models', function(require) {
  "use strict";

  // implementaciónen el lado del cliente de firma
  const {
    PosModel,
    PosGlobalState,
    Order,
    Orderline,
    Payment
  } = require('point_of_sale.models');
  const Registries = require('point_of_sale.Registries');
  const {
    batched
  } = require('point_of_sale.utils')
  var utils = require('web.utils');
  var core = require('web.core');
  var { Gui } = require('point_of_sale.Gui');

  var _t = core._t;
  var round_pr = utils.round_precision;

  class DC extends PosModel {
    constructor(obj) {
      super(obj);
    }
    es_nc(){
      return this.sii_code === 61;
    }

    es_boleta_afecta(){
        return this.sii_code === 39;
    }

    es_boleta_exenta(){
      return this.sii_code === 41;
    }

    es_boleta(){
      return this.es_boleta_afecta() || this.es_boleta_exenta();
    }

    es_factura_afecta(){
      return this.sii_code === 33;
    }

    es_factura_exenta(){
      return this.sii_code === 41;
    }

    es_factura(){
      return this.es_factura_afecta() || this.es_factura_exenta();
    }
    es_tributaria() {
      return this.sii_code;
    }
  }

  const FEPosGlobalState = (PosGlobalState) => class FEPosGlobalState extends PosGlobalState {
    get tpo_ops() {
      return {
        '1': {
          label: '1.- Anula el documento de referencia',
          op: '1'
        },
        '2': {
          label: '2.- Solo Corrige texto del documento referencia ',
          op: '2'
        },
        '3': {
          label: '3.- Corrige Montos (cantidad de productos , precios y otros totales)',
          op: '3'
        }
      }
    }

    async _processData(loadedData) {
      await super._processData(...arguments);
      this.sequences = loadedData['ir.sequence'];
      this._loadSequences(this.sequences);
      this.document_classes = loadedData['sii.document_class'];
      this._loadDCs(this.document_classes);
      this.sii_document_types = loadedData['sii.document_type'];
      this.sii_activities = loadedData['sii.activity.description'];
      this.cities = loadedData['res.city'];
      this.cities_by_id = loadedData['cities_by_id'];
      this.responsabilities = loadedData['sii.responsability'];
    }

    _loadSequences(sequences) {
      var self = this;
      if (sequences.length > 0) {
        sequences.forEach(function(seq) {
          if (self.config.secuencia_boleta && seq.id === self.config.secuencia_boleta[0]) {
            self.config.secuencia_boleta = seq;
          } else if (self.config.secuencia_boleta_exenta && seq.id === self.config.secuencia_boleta_exenta[0]) {
            self.config.secuencia_boleta_exenta = seq;
          } else if (self.config.secuencia_nc && seq.id === self.config.secuencia_nc[0]) {
            self.config.secuencia_nc = seq;
          } else if (self.config.secuencia_factura && seq.id === self.config.secuencia_factura[0]) {
            self.config.secuencia_factura = seq;
          } else if (self.config.secuencia_factura_exenta && seq.id === self.config.secuencia_factura_exenta[0]) {
            self.config.secuencia_factura_exenta = seq;
          }
        });
      }
    }

    _loadDCs(document_classes) {
      var self = this;
      self.dc_by_sii_code = {};
      self.dc_by_id = {};
      self.seq_by_sii_code = {};
      if (document_classes.length > 0) {
        document_classes.forEach(function(rdoc) {
          let doc = DC.create(rdoc);
          self.dc_by_sii_code[doc.sii_code] = doc;
          self.dc_by_id[doc.id] = doc;
          if (self.config.secuencia_boleta && doc.id === self.config.secuencia_boleta.sii_document_class_id[0]) {
            doc.start_number = self.pos_session.start_number;
            doc.caf_files = self.pos_session.caf_files;
            self.config.secuencia_boleta.sii_document_class_id = doc;
            self.seq_by_sii_code[doc.sii_code] = self.config.secuencia_boleta;
            doc.qty_available = self.config.secuencia_boleta.qty_available;
            self.set_next_number(self.config.secuencia_boleta,
                doc.start_number+self.pos_session.numero_ordenes)
          } else if (self.config.secuencia_boleta_exenta && doc.id === self.config.secuencia_boleta_exenta.sii_document_class_id[0]) {
            doc.start_number = self.pos_session.start_number_exentas;
            doc.caf_files = self.pos_session.caf_files_exentas;
            self.config.secuencia_boleta_exenta.sii_document_class_id = doc;
            self.seq_by_sii_code[doc.sii_code] = self.config.secuencia_boleta_exenta;
            doc.qty_available = self.config.secuencia_boleta_exenta.qty_available;
            self.set_next_number(self.config.secuencia_boleta_exenta,
                doc.start_number+self.pos_session.numero_ordenes)
          } else if (self.config.secuencia_nc && doc.id === self.config.secuencia_nc.sii_document_class_id[0]) {
            doc.start_number = self.pos_session.start_number_nc;
            doc.caf_files = self.pos_session.caf_files_nc;
            self.config.secuencia_nc.sii_document_class_id = doc;
            self.seq_by_sii_code[doc.sii_code] = self.config.secuencia_nc;
            doc.qty_available = self.config.secuencia_nc.qty_available;
            self.set_next_number(self.config.secuencia_nc,
                doc.start_number)
          } else if (self.config.secuencia_factura && doc.id === self.config.secuencia_factura.sii_document_class_id[0]) {
            doc.start_number = self.pos_session.start_number_factura;
            self.config.secuencia_factura.sii_document_class_id = doc;
            self.seq_by_sii_code[doc.sii_code] = self.config.secuencia_factura;
            doc.qty_available = self.config.secuencia_factura.qty_available;
            self.set_next_number(self.config.secuencia_factura,
                doc.start_number)
          } else if (self.config.secuencia_factura_exenta && doc.id === self.config.secuencia_factura_exenta.sii_document_class_id[0]) {
            doc.start_number = self.pos_session.start_number_factura_exenta;
            self.config.secuencia_factura_exenta.sii_document_class_id = doc;
            self.seq_by_sii_code[doc.sii_code] = self.config.secuencia_factura_exenta;
            doc.qty_available = self.config.secuencia_factura_exenta.qty_available;
            self.set_next_number(self.config.secuencia_factura_exenta,
                doc.start_number)
          }
        });
        var orders = this.get_order_list();
        for (var i = 0; i < orders.length; i++) {
          if (orders[i].data.document_class_id === self.config.secuencia_boleta.sii_document_class_id.id) {
            self.pos_session.numero_ordenes++;
            self.set_next_number(self.config.secuencia_boleta,
                orders[i].data.document_class_id.next_number+1)
          } else if (orders[i].data.document_class_id === self.config.secuencia_boleta_exenta.sii_document_class_id.id) {
            self.pos_session.numero_ordenes_exentas++;
            self.set_next_number(self.config.secuencia_boleta_exenta,
                orders[i].data.document_class_id.next_number+1)
          }
        }
      }
    }

    async update_sequences() {
      const res = await this.env.services.rpc({
        model: 'pos.session',
        method: 'update_sequences',
        args: [[odoo.pos_session_id]],
      }, { shadow: true });
      for (const seq of res.seqs) {
        let doc = this.dc_by_id[seq.sii_document_class_id[0]];
        doc.caf_files = seq.caf_files;
        doc.start_number = seq.start_number;
        doc.qty_available = seq.qty_available;
        try{
            this.set_next_number(this.seq_by_sii_code[doc.sii_code], doc.next_number)
            this.seq_by_sii_code[doc.sii_code].caf_files = seq.caf_files;
            this.seq_by_sii_code[doc.sii_code].qty_available = seq.qty_available;
        }catch{
            this.set_next_number(this.seq_by_sii_code[doc.sii_code], doc.start_number)
            console.log("no sequence id")
            console.log(seq)
        }
      }
    }

    folios_boleta_exenta() {
      return this.pos_session.caf_files_exentas;
    }

    folios_boleta_afecta() {
      return this.pos_session.caf_files;
    }

    set_next_number(seq, sii_document_number) {
      if (seq.sii_document_class_id.es_factura() || seq.sii_document_class_id.es_nc()){
        seq.sii_document_class_id.next_number = sii_document_number;
        return
      }
      var caf_files = JSON.parse(seq.sii_document_class_id.caf_files);
      var start_number = seq.sii_document_class_id.start_number;
      var start_caf_file = false;
      for (const caf of caf_files) {
        if (parseInt(caf.AUTORIZACION.CAF.DA.RNG.D) <= parseInt(start_number) &&
          parseInt(start_number) <= parseInt(caf.AUTORIZACION.CAF.DA.RNG.H)) {
          start_caf_file = caf;
        }
      }
      if (!start_caf_file){
        seq.sii_document_class_id.caf_file = false;
        seq.sii_document_class_id.next_number = 0;
        return;
      }
      var caf_file = false;
      var gived = 0;
      for (const caf of caf_files) {
        if (parseInt(caf.AUTORIZACION.CAF.DA.RNG.D) <= sii_document_number &&
          sii_document_number >= parseInt(caf.AUTORIZACION.CAF.DA.RNG.H)) {
          caf_file = caf;
        } else if (!caf_file || (sii_document_number < parseInt(caf.AUTORIZACION.CAF.DA.RNG.D) &&
            sii_document_number < parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D) &&
            parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D) < parseInt(caf.AUTORIZACION.CAF.DA.RNG.D)
          )) { // menor de los superiores caf
          caf_file = caf;
        }
        if (sii_document_number > parseInt(caf.AUTORIZACION.CAF.DA.RNG.H) && caf != start_caf_file) {
          gived += (parseInt(caf.AUTORIZACION.CAF.DA.RNG.H) - parseInt(caf.AUTORIZACION.CAF.DA.RNG.D)) + 1;
        }
      }
      seq.sii_document_class_id.caf_file = caf_file;
      seq.sii_document_class_id.next_number = sii_document_number;
      if (!caf_file) {
        return;
      }
      if (sii_document_number < parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D)) {
        var dif = sii_document_number - ((parseInt(start_caf_file.AUTORIZACION.CAF.DA.RNG.H) - start_number) + 1 + gived);
        sii_document_number = parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D) + dif;
        if (sii_document_number > parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.H)) {
          this.set_next_number(seq, sii_document_number);
        }
      }
    }

    set_sequence_next(seq) {
      if (!seq) {
        return 0;
      }
      if (seq.sii_document_class_id.es_factura() || seq.sii_document_class_id.es_nc()){
        return seq.sii_document_class_id.start_number;
      }
      var orden_numero = 0;
      if (seq.sii_document_class_id.es_boleta_exenta()) {
        orden_numero = this.pos_session.numero_ordenes_exentas;
      } else {
        orden_numero = this.pos_session.numero_ordenes;
      }
      this.set_next_number(
        seq,
        parseInt(orden_numero) + parseInt(seq.start_number)
      )
    }

    get_sequence_left(seq) {
      if (!seq) {
        return 0;
      }
      if (seq.sii_document_class_id.es_factura() || seq.sii_document_class_id.es_nc()){
        return seq.sii_document_class_id.qty_available;
      }
      var sii_document_number = seq.sii_document_class_id.next_number;
      var caf_files = JSON.parse(seq.sii_document_class_id.caf_files);
      var left = 0;
      for (const caf of caf_files) {
        if (sii_document_number > parseInt(caf.AUTORIZACION.CAF.DA.RNG.D)) {
          var desde = sii_document_number;
        } else {
          var desde = parseInt(caf.AUTORIZACION.CAF.DA.RNG.D);
        }
        var hasta = parseInt(caf.AUTORIZACION.CAF.DA.RNG.H);
        if (sii_document_number <= hasta) {
          var dif = 0;
          if (desde < sii_document_number) {
            sii_document_number - desde;
          }
          left += (hasta - desde - dif) + 1;
        }
      }
      return left;
    }

    _compute_factor(tax, uom_id) {
      var tax_uom = this.units_by_id[tax.uom_id[0]];
      var amount_tax = tax.amount;
      if (tax.uom_id !== uom_id) {
        var factor = (1 / tax_uom.factor);
        amount_tax = (amount_tax / factor);
      }
      return amount_tax;
    }

    _compute_all(tax, base_amount, quantity, price_exclude, uom_id=false) {
      if(price_exclude === undefined)
          var price_include = tax.price_include;
      else
          var price_include = !price_exclude;
      if (tax.amount_type === 'fixed') {
          // Use sign on base_amount and abs on quantity to take into account the sign of the base amount,
          // which includes the sign of the quantity and the sign of the price_unit
          // Amount is the fixed price for the tax, it can be negative
          // Base amount included the sign of the quantity and the sign of the unit price and when
          // a product is returned, it can be done either by changing the sign of quantity or by changing the
          // sign of the price unit.
          // When the price unit is equal to 0, the sign of the quantity is absorbed in base_amount then
          // a "else" case is needed.
        var amount_tax = 0;
        if(uom_id){
          amount_tax = this._compute_factor(tax, uom_id);
        }
        if (base_amount)
          return amount_tax * Math.sign(base_amount) * Math.abs(quantity) * tax.amount;
        else
            return amount_tax * quantity * tax.amount;
      }
      if (tax.amount_type === 'percent' && !price_include){
          return base_amount * tax.amount / 100;
      }
      if (tax.amount_type === 'percent' && price_include){
          return base_amount - (base_amount / (1 + tax.amount / 100));
      }
      if (tax.amount_type === 'division' && !price_include) {
          return base_amount / (1 - tax.amount / 100) - base_amount;
      }
      if (tax.amount_type === 'division' && price_include) {
          return base_amount - (base_amount * (tax.amount / 100));
      }
      return false;
    }

    compute_all(taxes, price_unit, quantity, currency_rounding, handle_price_include=true, uom_id=false) {
      var self = this;

      // 1) Flatten the taxes.

      var _collect_taxes = function(taxes, all_taxes){
          taxes = [...taxes].sort(function (tax1, tax2) {
              return tax1.sequence - tax2.sequence;
          });
          _(taxes).each(function(tax){
              if(tax.amount_type === 'group')
                  all_taxes = _collect_taxes(tax.children_tax_ids, all_taxes);
              else
                  all_taxes.push(tax);
          });
          return all_taxes;
      }
      var collect_taxes = function(taxes){
          return _collect_taxes(taxes, []);
      }

      taxes = collect_taxes(taxes);

      // 2) Deal with the rounding methods

      var round_tax = this.company.tax_calculation_rounding_method != 'round_globally';

      var initial_currency_rounding = currency_rounding;
      if(!round_tax)
          currency_rounding = currency_rounding * 0.00001;

      // 3) Iterate the taxes in the reversed sequence order to retrieve the initial base of the computation.
      var recompute_base = function(base_amount, fixed_amount, percent_amount, division_amount){
           return (base_amount - fixed_amount) / (1.0 + percent_amount / 100.0) * (100 - division_amount) / 100;
      }

      var base = round_pr(price_unit * quantity, initial_currency_rounding);

      var sign = 1;
      if(base < 0){
          base = -base;
          sign = -1;
      }

      var total_included_checkpoints = {};
      var i = taxes.length - 1;
      var store_included_tax_total = true;

      var incl_fixed_amount = 0.0;
      var incl_percent_amount = 0.0;
      var incl_division_amount = 0.0;

      var cached_tax_amounts = {};
      if (handle_price_include) {
        _(taxes.reverse()).each(function(tax) {
          if (tax.include_base_amount) {
            base = recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount);
            incl_fixed_amount = 0.0;
            incl_percent_amount = 0.0;
            incl_division_amount = 0.0;
            store_included_tax_total = true;
          }
          if (tax.price_include) {
            if (tax.amount_type === 'percent')
              incl_percent_amount += tax.amount;
            else if (tax.amount_type === 'division')
              incl_division_amount += tax.amount;
            else if (tax.amount_type === 'fixed')
              incl_fixed_amount += quantity * tax.amount
            else {
              var tax_amount = self._compute_all(tax, base, quantity);
              incl_fixed_amount += tax_amount;
              cached_tax_amounts[i] = tax_amount;
            }
            if (store_included_tax_total) {
              total_included_checkpoints[i] = base;
              store_included_tax_total = false;
            }
          }
          i -= 1;
        });
      }

      var total_excluded = round_pr(recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount), initial_currency_rounding);
      var total_included = total_excluded;

      // 4) Iterate the taxes in the sequence order to fill missing base/amount values.

      base = total_excluded;

      var skip_checkpoint = false;

      var taxes_vals = [];
      i = 0;
      var cumulated_tax_included_amount = 0;
      _(taxes.reverse()).each(function(tax){
          if(tax.price_include || tax.is_base_affected)
              var tax_base_amount = base;
          else
              var tax_base_amount = total_excluded;

          if(!skip_checkpoint && tax.price_include && total_included_checkpoints[i] !== undefined){
              var tax_amount = total_included_checkpoints[i] - (base + cumulated_tax_included_amount);
              cumulated_tax_included_amount = 0;
          }else
              var tax_amount = self._compute_all(tax, tax_base_amount, quantity, true);

          tax_amount = round_pr(tax_amount, currency_rounding);

          if(tax.price_include && total_included_checkpoints[i] === undefined)
              cumulated_tax_included_amount += tax_amount;

          taxes_vals.push({
              'id': tax.id,
              'name': tax.name,
              'amount': sign * tax_amount,
              'base': sign * round_pr(tax_base_amount, currency_rounding),
          });

          if(tax.include_base_amount){
              base += tax_amount;
              if(!tax.price_include)
                  skip_checkpoint = true;
          }

          total_included += tax_amount;
          i += 1;
      });

      return {
          'taxes': taxes_vals,
          'total_excluded': sign * round_pr(total_excluded, this.currency.rounding),
          'total_included': sign * round_pr(total_included, this.currency.rounding),
      };
    }
  }

  Registries.Model.extend(PosGlobalState, FEPosGlobalState);


  const FEOrderline = (Orderline) => class FEOrderline extends Orderline {
    export_for_printing() {
      let json = super.export_for_printing(...arguments);
      if (this.order.es_nc()) {
        json.quantity *= -1;
        json.price_display *= -1;
        json.price_with_tax *= -1;
        json.price_without_tax *= -1;
        json.price_with_tax_before_discount *= -1;
      }
      return json;
    }

    _fix_composed_included_tax(taxes, base, quantity, uom_id) {
      let composed_tax = {}
      var price_included = false;
      var percent = 0.0;
      var rec = 0.0;
      var self = this;
      _(taxes).each(function(tax) {
        if (tax.price_include) {
          price_included = true;
          if (tax.amount_type == 'percent') {
            percent += tax.amount;
          } else {
            var amount_tax = self._compute_factor(tax, uom_id);
            rec += (quantity * amount_tax);
          }
        }
      });
      if (price_included) {
        var _base = base - rec
        var common_base = (_base / (1 + percent / 100.0))
        _(taxes).each(function(tax) {
          if (tax.amount_type == 'percent') {
            composed_tax[tax.id] = (common_base * (1 + tax.amount / 100))
          }
        });
      }
      return composed_tax
    }

    get_all_prices(qty = this.get_quantity()) {
      var price_unit = this.get_unit_price() * (1.0 - (this.get_discount() / 100.0));
      var taxtotal = 0;

      var product = this.get_product();
      var taxes_ids = this.tax_ids || product.taxes_id;
      taxes_ids = _.filter(taxes_ids, t => t in this.pos.taxes_by_id);
      var taxdetail = {};
      var product_taxes = this.pos.get_taxes_after_fp(taxes_ids, this.order.fiscal_position);

      var all_taxes = this.compute_all(product_taxes, price_unit, qty, this.pos.currency.rounding, true, this.get_unit());
      var all_taxes_before_discount = this.compute_all(product_taxes, this.get_unit_price(), qty, this.pos.currency.rounding, true, this.get_unit());
      let iva = false;
      _(all_taxes.taxes).each(function(tax) {
        if([14, 15].includes(tax.sii_code)){
          iva = tax;
        }
        taxtotal += tax.amount;
        taxdetail[tax.id] = tax.amount;
      });

      if (this.order.es_boleta_afecta()){
        let price_unit_discount = 0;
        if (iva.price_include){
          price_unit = all_taxes_before_discount.total_included;
          price_unit_discount = price_unit * (1.0 - (this.get_discount() / 100.0));
        }else{
          price_unit = all_taxes_before_discount.total_excluded;
          price_unit_discount = price_unit * (1.0 - (this.get_discount() / 100.0));
        }

        all_taxes = this.compute_all(iva, price_unit_discount, 1, this.pos.currency.rounding, true, this.get_unit());
        all_taxes_before_discount = this.compute_all(product_taxes, price_unit, 1, this.pos.currency.rounding, true, this.get_unit());
        taxtotal = 0;
        tax_detail = {};
        _(all_taxes.taxes).each(function(tax) {
          taxtotal += tax.amount;
          taxdetail[tax.id] = tax.amount;
        });
        return {
            "priceWithTax": all_taxes.total_included,
            "priceWithoutTax": all_taxes.total_excluded,
            "priceWithTaxBeforeDiscount": all_taxes_before_discount.total_included,
            "priceWithoutTaxBeforeDiscount": all_taxes_before_discount.total_excluded,
            "tax": taxtotal,
            "taxDetails": taxdetail,
            "tax_percentages": product_taxes.map((tax) => tax.amount),
        };
      }
      return {
          "priceWithTax": all_taxes.total_included,
          "priceWithoutTax": all_taxes.total_excluded,
          "priceWithTaxBeforeDiscount": all_taxes_before_discount.total_included,
          "priceWithoutTaxBeforeDiscount": all_taxes_before_discount.total_excluded,
          "tax": taxtotal,
          "taxDetails": taxdetail,
          "tax_percentages": product_taxes.map((tax) => tax.amount),
      };
    }

  }

  Registries.Model.extend(Orderline, FEOrderline);

  const FEOrder = (Order) => class FEOrder extends Order {
    constructor(obj, options) {
      super(...arguments);
      if (options.json) {
        return;
      }
      this.sii_document_number = false;
      this.signature = false;
      this.referencias = [];
      this.set_tipo();
      if (this.pos.config.marcar === 'boleta' && this.pos.folios_boleta_afecta()) {
        this.set_tipo(this.pos.config.secuencia_boleta.sii_document_class_id);
      } else if (this.pos.config.marcar === 'boleta_exenta' && this.pos.folios_boleta_exenta()) {
        this.set_tipo(this.pos.config.secuencia_boleta_exenta.sii_document_class_id);
      } else if (this.pos.config.marcar === 'factura') {
        this.set_to_invoice(true);
        this.set_factura_afecta();
      } else if (this.pos.config.marcar === 'factura_exenta') {
        this.set_to_invoice(true);
        this.set_factura_exenta()
      }
      if (this.es_boleta()) {
        this.orden_numero = this.orden_numero || (this.es_boleta_afecta() ? this.pos.pos_session.numero_ordenes : this.pos.pos_session.numero_ordenes);
        if (this.orden_numero <= 0) {
          this.orden_numero = 1;
        }
      }
    }

    init_from_JSON(json) { // carga pedido individual
      super.init_from_JSON(...arguments);
      if (json.document_class_id) {
        let dc = this.pos.dc_by_id[json.document_class_id];
        this.set_tipo(dc);
        if (dc.es_factura()){
          this.set_to_invoice(true);
        }
      }
      this.sii_document_number = json.sii_document_number;
      this.signature = json.signature;
      this.orden_numero = json.orden_numero;
      this.finalized = json.finalized;
      var referencias = [];
      if (json.referencias && json.referencias.length !== 0) {
        for (const ref_element of json.referencias) {
          let ref = ref_element[2];
          referencias.push({
            sequence: ref.sequence,
            origen: ref.origen,
            sii_referencia_TpoDocRef: this.pos.dc_by_id[ref.sii_referencia_TpoDocRef],
            sii_referencia_CodRef: ref.sii_referencia_CodRef,
            motivo: ref.motivo,
            fecha_documento: ref.fecha_documento,
          });
        }
      }
      this.referencias = referencias;
      this.sii_result = json.sii_result || '';
    }

    export_as_JSON() {
      const json = super.export_as_JSON(...arguments);
      if (this.document_class_id) {
        json.document_class_id = this.document_class_id.id;
      } else {
        json.document_class_id = false;
      }
      json.sii_document_number = this.sii_document_number;
      json.signature = this.signature;
      json.orden_numero = this.orden_numero;
      json.finalized = this.finalized;
      var referencias = [];
      if (this.referencias.length !== 0) {
        for (const ref of this.referencias) {
          referencias.push([0,0, {
            sequence: ref.sequence,
            origen: ref.origen,
            sii_referencia_TpoDocRef: ref.sii_referencia_TpoDocRef.id,
            sii_referencia_CodRef: ref.sii_referencia_CodRef,
            motivo: ref.motivo,
            fecha_documento: ref.fecha_documento,
          }])
        }
      }
      json.referencias = referencias;
      return json;
    }

    export_for_printing() {
      const json = super.export_for_printing(...arguments);
      json.company.document_number = this.pos.company.document_number;
      json.company.activity_description = this.pos.company.activity_description ? this.pos.company.activity_description[1] : null;
      json.company.street = this.pos.company.street;
      json.company.city = this.pos.company.city;
      json.company.dte_resolution_date = this.pos.company.dte_resolution_date;
      json.company.dte_resolution_number = this.pos.company.dte_resolution_number;
      json.company.sucursal_ids = this.pos.company.sucursal_ids ? this.pos.company.sucursal_ids : [];
      json.sii_document_number = this.sii_document_number;
      json.orden_numero = this.orden_numero;
      json.referencias = [];
      for (const ref of this.referencias) {
        json.referencias.push({
          sequence: ref.sequence,
          folio: ref.origen,
          dc_id: ref.sii_referencia_TpoDocRef.name,
          tpo_op: ref.tpo_op ? this.pos.tpo_ops[ref.sii_referencia_CodRef] : '',
          motivo: ref.motivo,
          fecha: ref.fecha_documento
        });
      }
      if (this.document_class_id) {
        json.nombre_documento = this.document_class_id.name;
        if (this.is_to_invoice()) {
          json.nombre_documento = "Ticket de documento, no válido como " + json.nombre_documento;
        }
      }
      var d = this.creation_date;
      var curr_date = this.completa_cero(d.getDate());
      var curr_month = this.completa_cero(d.getMonth() + 1); // Months
      // are zero
      // based
      var curr_year = d.getFullYear();
      var hours = d.getHours();
      var minutes = d.getMinutes();
      var seconds = d.getSeconds();
      var date = curr_year + '-' + curr_month + '-' + curr_date + ' ' +
        this.completa_cero(hours) + ':' + this.completa_cero(minutes) + ':' + this.completa_cero(seconds);
      json.creation_date = date;
      json.barcode_pdf417 = this.barcode_pdf417();
      json.exento = this.get_total_exento();
      json.referencias = [];
      if (this.es_nc()) {
        json.subtotal *= -1;
        json.total_with_tax *= -1;
        json.total_rounded *= -1;
        json.total_without_tax *= -1;
        json.total_tax *= -1;
        json.total_tax_paid *= -1;
        json.total_discount *= -1;
      }
      return json;
    }

    initialize_validation_date() {
      if (this.finalized) {
        return;
      }
      super.initialize_validation_date(...arguments);
      if (!this.sii_document_number && this.es_boleta()) {
        if (this.es_boleta_exenta()) {
          var orden_numero = this.pos.pos_session.numero_ordenes_exentas;
          this.pos.pos_session.numero_ordenes_exentas++;
        } else {
          var orden_numero = this.pos.pos_session.numero_ordenes;
          this.pos.pos_session.numero_ordenes++;
        }
        this.orden_numero = orden_numero + 1;
        this.document_class_id.qty_available -= 1;
        this.sii_document_number = this.document_class_id.next_number;
        this.signature = this.timbrar();
        this.pos.set_next_number(
          this.pos.seq_by_sii_code[this.document_class_id.sii_code],
          this.sii_document_number+1
        );
      }
    }

    get_total_exento() {
      var self = this;
      var taxes = this.pos.taxes;
      var exento = 0;
      self.orderlines.forEach(function(line) {
        var product = line.get_product();
        var taxes_ids = product.taxes_id;
        _(taxes_ids).each(function(id) {
          var t = self.pos.taxes_by_id[id];
          if (t.sii_code === 0) {
            exento += (line.get_unit_price() * line.get_quantity());
          }
        });
      });
      return exento;
    }

    add_orderline(line){
      this.assert_editable();
      if (this.es_tributaria()){
        let lineas = this.get_orderlines().length;
        if(this.es_boleta()){
          if(lineas >= 200){
            let error = _t('No puede haber más de 200 líneas de pedido');
            Gui.showPopup('ErrorPopup', {
                title: _t('Límite de líneas'),
                body: error,
            });
            return;
          }
        }else if(lineas >= 60){
          let error = _t('No puede haber más de 60 líneas de pedido');
          Gui.showPopup('ErrorPopup', {
              title: _t('Límite de líneas'),
              body: error,
          });
          return;
        }
      }
      return super.add_orderline(...arguments);
    }

    remove_orderline(line) {
      this.assert_editable();
      super.remove_orderline(line);
      if (this.es_nc() && this.orderlines.length === 0) {
        this.unset_tipo()
      }
    }

    wait_for_push_order(){
        if(this.es_nc()){
            return true;
        }
        return super.wait_for_push_order(...arguments);
    }

    removeReferencia(line) {
      this.referencias = this.referencias.filter(function(ref) {
        return ref.sequence !== line.sequence;
      });
    }

    set_tipo(tipo) {
      if (tipo)
        {
          this.document_class_id = tipo;
        }
        this.document_class_id = DC.create({});
    }

    set_boleta(boleta) {
      this.boleta = boleta;
    }

    set_factura_afecta() {
      this.set_tipo(this.pos.dc_by_sii_code[33]);
    }

    set_factura_exenta() {
      this.set_tipo(this.pos.dc_by_sii_code[34])
    }

    set_nc() {
      this.set_tipo(this.pos.dc_by_sii_code[61])
    }

    unset_tipo() {
      this.set_tipo(false);
    }

    unset_boleta() {
      this.set_tipo(false);
      this.orden_numero = false;
      this.sii_document_number = false;
      this.unset_tipo();
    }

    es_boleta() {
      return this.es_boleta_afecta() || this.es_boleta_exenta();
    }

    es_boleta_exenta() {
      return this.document_class_id.es_boleta_exenta();
    }

    es_boleta_afecta(check_marcar = false) {
      return this.document_class_id.es_boleta_afecta();
    }

    es_factura_afecta() {
      return (this.document_class_id.es_factura_afecta() && this.is_to_invoice());
    }

    es_factura_exenta() {
      return (this.document_class_id.es_factura_exenta() && this.is_to_invoice());
    }

    es_factura(){
      return (this.es_factura_afecta() || this.es_factura_exenta())
    }

    es_nc() {
      return (this.document_class_id.es_nc());
    }

    crear_guia() {
      return (this.pos.config.dte_picking && (this.pos.config.dte_picking_option === 'all' || (this.pos.config.dte_picking_option === 'no_tributarios' && !this.es_tributaria())));
    }

    es_tributaria() {
      return this.document_class_id.es_tributaria();
    }

    completa_cero(val) {
      if (parseInt(val) < 10) {
        return '0' + val;
      }
      return val;
    }

    timbrar() {
      var order = this;
      if (order.signature) { // no firmar otra vez
        return order.signature;
      }
      var caf_file = this.document_class_id.caf_file;
      var priv_key = caf_file.AUTORIZACION.RSASK;
      var pki = forge.pki;
      var privateKey = pki.privateKeyFromPem(priv_key);
      var md = forge.md.sha1.create();
      var partner_id = this.get_partner();
      if (!partner_id) {
        partner_id = {};
        partner_id.name = "Usuario Anonimo";
      }
      if (!partner_id.document_number) {
        partner_id.document_number = "66666666-6";
      }

      function format_str(text) {
        return text.replace('&', '&amp;');
      }
      var product_name = format_str(order.orderlines[0].product.name);
      var d = order.validation_date;
      var curr_date = this.completa_cero(d.getDate());
      var curr_month = this.completa_cero(d.getMonth() + 1); // Months
      // are zero
      // based
      var curr_year = d.getFullYear();
      var hours = d.getHours();
      var minutes = d.getMinutes();
      var seconds = d.getSeconds();
      var date = curr_year + '-' + curr_month + '-' + curr_date + 'T' +
        this.completa_cero(hours) + ':' + this.completa_cero(minutes) + ':' + this.completa_cero(seconds);
      var rut_emisor = this.pos.company.document_number.replace('.', '').replace('.', '');
      if (rut_emisor.charAt(0) == "0") {
        rut_emisor = rut_emisor.substr(1);
      }
      let total = this.get_total_with_tax();
      if (total < 0) {
        total *= -1;
      }
      var string = '<DD>' +
        '<RE>' + rut_emisor + '</RE>' +
        '<TD>' + order.document_class_id.sii_code + '</TD>' +
        '<F>' + order.sii_document_number + '</F>' +
        '<FE>' + curr_year + '-' + curr_month + '-' + curr_date + '</FE>' +
        '<RR>' + partner_id.document_number.replace('.', '').replace('.', '') + '</RR>' +
        '<RSR>' + format_str(partner_id.name) + '</RSR>' +
        '<MNT>' + Math.round(total) + '</MNT>' +
        '<IT1>' + product_name + '</IT1>' +
        '<CAF version="1.0"><DA><RE>' + caf_file.AUTORIZACION.CAF.DA.RE + '</RE>' +
        '<RS>' + format_str(caf_file.AUTORIZACION.CAF.DA.RS) + '</RS>' +
        '<TD>' + caf_file.AUTORIZACION.CAF.DA.TD + '</TD>' +
        '<RNG><D>' + caf_file.AUTORIZACION.CAF.DA.RNG.D + '</D><H>' + caf_file.AUTORIZACION.CAF.DA.RNG.H + '</H></RNG>' +
        '<FA>' + caf_file.AUTORIZACION.CAF.DA.FA + '</FA>' +
        '<RSAPK><M>' + caf_file.AUTORIZACION.CAF.DA.RSAPK.M + '</M><E>' + caf_file.AUTORIZACION.CAF.DA.RSAPK.E + '</E></RSAPK>' +
        '<IDK>' + caf_file.AUTORIZACION.CAF.DA.IDK + '</IDK>' +
        '</DA>' +
        '<FRMA algoritmo="SHA1withRSA">' + caf_file.AUTORIZACION.CAF.FRMA + '</FRMA>' +
        '</CAF>' +
        '<TSTED>' + date + '</TSTED></DD>';
      md.update(string);
      var signature = forge.util.encode64(privateKey.sign(md));
      string = '<TED version="1.0">' + string + '<FRMT algoritmo="SHA1withRSA">' + signature + '</FRMT></TED>';
      return string;
    }

    barcode_pdf417() {
      if (!this.document_class_id || !this.sii_document_number) {
        return false;
      }
      PDF417.ROWHEIGHT = 2;
      PDF417.init(this.signature, 6);
      var barcode = PDF417.getBarcodeArray();
      var bw = 2;
      var bh = 2;
      var canvas = document.createElement('canvas');
      canvas.width = bw * barcode['num_cols'];
      canvas.height = 255;
      var ctx = canvas.getContext('2d');
      var y = 0;
      for (var r = 0; r < barcode['num_rows']; ++r) {
        var x = 0;
        for (var c = 0; c < barcode['num_cols']; ++c) {
          if (barcode['bcode'][r][c] == 1) {
            ctx.fillRect(x, y, bw, bh);
          }
          x += bw;
        }
        y += bh;
      }
      return canvas.toDataURL("image/png");
    }
  }

  Registries.Model.extend(Order, FEOrder);

});
