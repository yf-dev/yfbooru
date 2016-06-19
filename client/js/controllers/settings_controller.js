'use strict';

const settings = require('../models/settings.js');
const topNavigation = require('../models/top_navigation.js');
const SettingsView = require('../views/settings_view.js');

class SettingsController {
    constructor() {
        topNavigation.activate('settings');
        this._view = new SettingsView({
            settings: settings.get(),
        });
        this._view.addEventListener('change', e => this._evtChange(e));
    }

    _evtChange(e) {
        this._view.clearMessages();
        settings.save(e.detail.settings);
        this._view.showSuccess('Settings saved.');
    }
};

module.exports = router => {
    router.enter('/settings', (ctx, next) => {
        ctx.controller = new SettingsController();
    });
};