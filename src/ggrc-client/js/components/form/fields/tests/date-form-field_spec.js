/*
    Copyright (C) 2020 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import {getComponentVM} from '../../../../../js_specs/spec-helpers';
import Component from '../date-form-field';

describe('date-form-field component', () => {
  'use strict';
  let viewModel;

  beforeEach(function () {
    viewModel = getComponentVM(Component);
    spyOn(viewModel, 'dispatch');
    viewModel.attr('fieldId', 'id');
  });

  it('does not fire valueChanged event on first value assignation', () => {
    viewModel.attr('value', '');
    expect(viewModel.dispatch).not.toHaveBeenCalled();
  });

  it('sets the value of the input', () => {
    viewModel.attr('value', 'test');
    expect(viewModel.attr('inputValue')).toEqual('test');
  });

  it('does not fire valueChanged event if value wasn\'t changed', () => {
    viewModel.attr('value', '');
    viewModel.attr('inputValue', 'newValue');
    viewModel.dispatch.calls.reset();
    viewModel.attr('inputValue', 'newValue');
    expect(viewModel.dispatch).not.toHaveBeenCalled();
  });

  it('fires valueChanged event on input value change', () => {
    viewModel.attr('value', '');
    viewModel.attr('inputValue', 'newValue');
    expect(viewModel.dispatch).toHaveBeenCalledWith({
      type: 'valueChanged',
      fieldId: 'id',
      value: 'newValue',
    });
    viewModel.attr('inputValue', 'newValue2');
    expect(viewModel.dispatch).toHaveBeenCalledWith({
      type: 'valueChanged',
      fieldId: 'id',
      value: 'newValue2',
    });
  });
});
