/*
    Copyright (C) 2020 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import canComponent from 'can-component';
import canStache from 'can-stache';
import template from './assessments-bulk-complete-button.stache';
import BulkUpdatableButton from '../view-models/bulk-updatable-button-vm';

const viewModel = BulkUpdatableButton.extend({
  async openBulkCompleteModal(el) {
    const {AssessmentsBulkComplete} = await import(
      /* webpackChunkName: "mapper" */
      '../../../controllers/mapper/mapper'
    );

    AssessmentsBulkComplete.launch($(el), this.getModalConfig());
  },
});

export default canComponent.extend({
  tag: 'assessments-bulk-complete-button',
  view: canStache(template),
  viewModel,
});
