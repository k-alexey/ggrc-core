/*
    Copyright (C) 2020 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import canStache from 'can-stache';
import canMap from 'can-map';
import canComponent from 'can-component';
import template from './templates/proposable-control.stache';
import {getProposalAttrUrl} from '../../../plugins/utils/ggrcq-utils';

const viewModel = canMap.extend({
  define: {
    link: {
      get() {
        return getProposalAttrUrl(
          this.attr('instance'),
          this.attr('attrName'),
          this.attr('isCustomAttribute')
        );
      },
    },
  },
  instance: null,
  attrName: '',
  isCustomAttribute: false,
});

export default canComponent.extend({
  tag: 'proposable-control',
  leakScope: false,
  view: canStache(template),
  viewModel,
});
