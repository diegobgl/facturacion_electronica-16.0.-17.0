odoo.define('l10n_cl_point_of_sale.ReferenciasButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class ReferenciasButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
            this.count = this.env.pos.get_order().referencias.length;
        }
        async onClick() {
            this.showScreen('ReferenciasScreen');
        }
    }
    ReferenciasButton.template = 'ReferenciasButton';

    ProductScreen.addControlButton({
        component: ReferenciasButton,
        condition: function() {
            return true;
        },
    });

    Registries.Component.add(ReferenciasButton);

    return ReferenciasButton;
});
