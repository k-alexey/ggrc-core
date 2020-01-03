/*
 Copyright (C) 2020 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canStache from 'can-stache';
import canComponent from 'can-component';
import template from './inner-nav.stache';
import './inner-nav-item';
import '../add-tab-button/add-tab-button';
import InnerNavVM from './inner-nav-vm';

export default canComponent.extend({
  tag: 'inner-nav',
  view: canStache(template),
  viewModel: InnerNavVM,
  events: {
    inserted() {
      this.viewModel.initVM();
    },
    '{counts} change'(counts, event, name, action, count) {
      this.viewModel.setWidgetCount(name, count);
    },
  },
});
