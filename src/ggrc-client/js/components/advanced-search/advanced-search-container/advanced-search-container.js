/*
  Copyright (C) 2020 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/


import '../../../components/advanced-search/advanced-search-filter-container';
import '../../../components/advanced-search/advanced-search-mapping-container';

import canComponent from 'can-component';
import canStache from 'can-stache';
import canMap from 'can-map';
import template from './advanced-search-container.stache';

const viewModel = canMap.extend({
  filterItems: [],
  defaultFilterItems: [],
  availableAttributes: [],
  statesCollectionKey: [],
  mappingItems: [],
  modelName: null,
  mappedToItems: [],
  filterOperatorOptions: null,
  disabled: false,
  resetFilters() {
    this.attr('filterItems', this.attr('defaultFilterItems').serialize());
    this.attr('mappingItems', []);
  },
  onSubmit() {
    this.dispatch('onSubmit');
  },
});

export default canComponent.extend({
  tag: 'advanced-search-container',
  view: canStache(template),
  viewModel,
});
