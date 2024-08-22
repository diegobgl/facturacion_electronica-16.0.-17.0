odoo.define('l10n_cl_dte_point_of_sale.PartnerListScreen', function (require) {
"use strict";

var PartnerListScreen = require('point_of_sale.PartnerListScreen');
const { _t } = require('web.core');
const Registries = require('point_of_sale.Registries');


const FEPartnerListScreen = (PartnerListScreen) =>
		class extends PartnerListScreen {
			constructor(){
				super(...arguments);
			}
			back(){
				if(this.state.detailIsShown) {
					this.state.editModeProps.partner = {
						country_id: this.env.pos.company.country_id,
						city_id: this.env.pos.company.city_id,
						city: this.env.pos.company.city,
						state_id: this.env.pos.company.state_id,
					}
				}
				super.back();
			}
		}
	Registries.Component.extend(PartnerListScreen, FEPartnerListScreen);

	return FEPartnerListScreen;
});
