odoo.define('l10n_cl_dte_point_of_sale.ActionpadWidget', function (require) {
"use strict";

  var ActionpadWidget = require('point_of_sale.ActionpadWidget');
  const { _t } = require('web.core');
  const Registries = require('point_of_sale.Registries');

  const FEActionpadWidget = (ActionpadWidget) =>
    class extends ActionpadWidget{
        getNCName(){
            let dc = false;
            let order = this.env.pos.get_order();
            if (this.props.actionToTrigger === 'do-refund'){
                dc = this.env.pos.dc_by_sii_code[61];
            }else{
                dc = order.document_class_id;
            }
            if (!dc){
                return 'No Tributaria'
            }
            let seq = this.env.pos.seq_by_sii_code[dc.sii_code];
            var name = dc.name;
            if (seq){
                let next_f = seq.sii_document_class_id.next_number;
                let left_f = this.env.pos.get_sequence_left(seq);
                name += ', F('+next_f+'). '+ 'Quedan: ' + left_f  + ' Folios';
            }
            return name;
        }

    }
    Registries.Component.extend(ActionpadWidget, FEActionpadWidget);


    return FEActionpadWidget;
});
