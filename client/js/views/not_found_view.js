'use strict';

const config = require('../config.js');
const views = require('../util/views.js');

const template = views.getTemplate('not-found');

class NotFoundView {
    constructor(path) {
        this._hostNode = document.getElementById('content-holder');

        const sourceNode = template({path: path});
        views.replaceContent(this._hostNode, sourceNode);
    }
}

module.exports = NotFoundView;