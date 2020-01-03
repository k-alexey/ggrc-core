/*
 Copyright (C) 2020 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canList from 'can-list';
import canMap from 'can-map';
import {getComponentVM} from '../../../../js_specs/spec-helpers';
import Component from '../object-list';

describe('object-list component', function () {
  'use strict';

  let viewModel;

  describe('should have some default values', function () {
    beforeEach(function () {
      viewModel = getComponentVM(Component);
    });

    it('and they should be correct', function () {
      expect(viewModel.attr('items').length).toBe(0);
      expect(viewModel.attr('itemSelector')).toBe('');
      expect(viewModel.attr('isLoading')).toBe(false);
      expect(viewModel.attr('emptyMessage')).toBe('None');
      expect(viewModel.attr('isInnerClick')).toBe(false);
      expect(viewModel.attr('selectedItem.el')).toBeNull();
      expect(viewModel.attr('selectedItem.data')).toBeNull();
    });
  });

  describe('modifySelection() method ', function () {
    let scope = new canMap({
      instance: {
        type: 'a',
        id: 1,
      },
      isSelected: false,
    });

    let items = new canList([
      scope, {
        instance: {
          type: 'b',
          id: 1,
        },
        isSelected: false,
      },
    ]);
    beforeEach(function () {
      viewModel = getComponentVM(Component);
      viewModel.attr('items', items);
    });

    it('should select item with correct index', function () {
      viewModel.modifySelection(scope, {}, $('body'));
      expect(viewModel.attr('items')[0].attr('isSelected')).toBe(true);
    });

    it('should update selected Item', function () {
      viewModel.modifySelection(scope, {}, $('body'));
      expect(viewModel.attr('selectedItem.data')).toBe(scope.attr('instance'));
    });
  });

  describe('clearSelection() method ', function () {
    let scope;
    let items;

    beforeEach(function () {
      scope = new canMap({
        instance: {
          type: 'a',
          id: 1,
        },
        isSelected: false,
      });
      items = new canList([scope, {
        instance: {
          type: 'b',
          id: 1,
        },
        isSelected: false,
      }]);
      viewModel = getComponentVM(Component);
      viewModel.attr('items', items);
      // Set some not null default value selectedItem for each test execution
      viewModel.attr('selectedItem', {
        el: 'some object',
        data: new canMap({
          field: 'someData',
        }),
      });
    });

    it('should deselect selected item and empty selection' +
      'if no item was selected', function () {
      viewModel.clearSelection();
      expect(viewModel.attr('items').attr()
        .every(function (item) {
          return !item.isSelected;
        })).toBe(true);
      expect(viewModel.attr('selectedItem.el')).toBeNull();
      expect(viewModel.attr('selectedItem.data')).toBeNull();
    });

    it('should deselect selected item and empty selection' +
      'if single item was selected', function () {
      scope.attr('isSelected', true);
      viewModel.clearSelection();
      expect(viewModel.attr('items').attr()
        .every(function (item) {
          return !item.isSelected;
        })).toBe(true);
      expect(viewModel.attr('selectedItem.el')).toBeNull();
      expect(viewModel.attr('selectedItem.data')).toBeNull();
    });

    it('should deselect selected item and empty selection' +
      'if all items were selected', function () {
      viewModel.attr('items').each(function (item) {
        item.attr('isSelected', true);
      });
      viewModel.clearSelection();
      expect(viewModel.attr('items').attr()
        .every(function (item) {
          return !item.isSelected;
        })).toBe(true);
      expect(viewModel.attr('selectedItem.el')).toBeNull();
      expect(viewModel.attr('selectedItem.data')).toBeNull();
    });
  });

  describe('onOuterClick() method ', function () {
    beforeEach(function () {
      viewModel = getComponentVM(Component);
      spyOn(viewModel, 'clearSelection');
    });

    it('should clear selection ' +
      'if attribute "isInnerClick" is false', function () {
      viewModel.onOuterClick();
      expect(viewModel.clearSelection).toHaveBeenCalled();
    });

    it('should not clear selection and set attribute "isInnerClick" to false' +
      'if attribute "isInnerClick" is true', function () {
      viewModel.attr('isInnerClick', true);
      viewModel.onOuterClick();
      expect(viewModel.clearSelection).not.toHaveBeenCalled();
      expect(viewModel.attr('isInnerClick')).toBe(false);
    });
  });
});
