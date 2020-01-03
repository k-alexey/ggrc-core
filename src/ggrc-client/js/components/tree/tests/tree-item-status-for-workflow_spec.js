/*
 Copyright (C) 2020 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import Component from '../tree-item-status-for-workflow';
import {getComponentVM} from '../../../../js_specs/spec-helpers';

describe('tree-item-status-for-workflow component', () => {
  let viewModel;

  beforeEach(function () {
    viewModel = getComponentVM(Component);
  });

  describe('statusCSSClass attribute', () => {
    describe('get() method', () => {
      beforeEach(function () {
        viewModel.attr('instance', {});
      });

      it('returns a class name without whitespace characters in lowercase ' +
      'if status exists', function () {
        const status = 'Some long status';
        const expectedStatus = 'state-somelongstatus';
        viewModel.attr('instance.status', status);
        expect(viewModel.attr('statusCSSClass')).toBe(expectedStatus);
      });

      it('returns empty string by default', function () {
        expect(viewModel.attr('statusCSSClass')).toBe('');
      });
    });
  });
});
