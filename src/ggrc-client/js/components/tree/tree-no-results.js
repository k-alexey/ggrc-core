/*
 Copyright (C) 2020 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canStache from 'can-stache';
import canMap from 'can-map';
import canComponent from 'can-component';
import template from './templates/tree-no-results.stache';

export default canComponent.extend({
  tag: 'tree-no-results',
  view: canStache(template),
  leakScope: true,
  viewModel: canMap.extend({
    define: {
      text: {
        value: 'No results, please check your filter criteria',
        set: function (value) {
          return value || 'No results...';
        },
      },
      show: {
        set: function (value) {
          return value || false;
        },
      },
    },
  }),
});
