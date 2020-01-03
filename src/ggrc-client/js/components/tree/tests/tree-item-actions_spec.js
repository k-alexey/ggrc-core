/*
  Copyright (C) 2020 Google Inc.
  Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import canMap from 'can-map';
import Component from '../tree-item-actions';
import {
  getComponentVM,
  makeFakeInstance,
} from '../../../../js_specs/spec-helpers';
import * as Permission from '../../../permission';
import * as SnapshotUtils from '../../../plugins/utils/snapshot-utils';
import * as Mapper from '../../../models/mappers/mappings';
import Cacheable from '../../../models/cacheable';

describe('tree-item-actions component', function () {
  let viewModel;

  beforeEach(() => {
    viewModel = getComponentVM(Component);
    viewModel.attr('instance', new canMap());
  });

  describe('isAllowedToMap get() method', () => {
    beforeEach(() => {
      spyOn(SnapshotUtils, 'isSnapshot').and.returnValue(false);
    });
    describe('returns false', () => {
      it('if there is no objects to map to instance type', () => {
        spyOn(Permission, 'isAllowedFor').and.returnValue(true);
        spyOn(Mapper, 'getMappingList').and.returnValue([]);
        viewModel.attr('instance.type', 'Workflow');

        let result = viewModel.attr('isAllowedToMap');

        expect(result).toBe(false);
      });

      it('if user has no rights to update instance', () => {
        spyOn(Permission, 'isAllowedFor').and.returnValue(false);
        let result = viewModel.attr('isAllowedToMap');

        expect(result).toBe(false);
      });
    });

    describe('returns true', () => {
      it('if there are objects to map to instance type and ' +
        'user has permissions to update instance', () => {
        spyOn(Permission, 'isAllowedFor').and.returnValue(true);
        spyOn(Mapper, 'getMappingList').and.returnValue(['Object1']);
        viewModel.attr('instance.type', 'Type');

        let result = viewModel.attr('isAllowedToMap');

        expect(result).toBe(true);
      });
    });
  });

  describe('isAllowedToEdit get() method', () => {
    describe('returns false', () => {
      it('if instance is archived', () => {
        spyOn(Permission, 'isAllowedFor').and.returnValue(true);
        spyOn(SnapshotUtils, 'isSnapshot').and.returnValue(false);
        viewModel.attr('instance.type', 'Type');
        viewModel.attr('instance.archived', true);

        let result = viewModel.attr('isAllowedToEdit');
        expect(result).toBe(false);
      });

      it('if instance is snapshot', () => {
        spyOn(Permission, 'isAllowedFor').and.returnValue(true);
        spyOn(SnapshotUtils, 'isSnapshot').and.returnValue(true);
        viewModel.attr('instance.type', 'Type');
        viewModel.attr('instance.archived', false);

        let result = viewModel.attr('isAllowedToEdit');
        expect(result).toBe(false);
      });

      it('if instance type is in forbiddenEditList', () => {
        spyOn(Permission, 'isAllowedFor').and.returnValue(true);
        spyOn(SnapshotUtils, 'isSnapshot').and.returnValue(false);
        viewModel.attr('instance.type', 'Cycle');
        viewModel.attr('instance.archived', false);

        let result = viewModel.attr('isAllowedToEdit');
        expect(result).toBe(false);
      });

      it('if user has not permissions to update instance', () => {
        spyOn(Permission, 'isAllowedFor').and.returnValue(false);
        spyOn(SnapshotUtils, 'isSnapshot').and.returnValue(false);
        viewModel.attr('instance.type', 'Type');
        viewModel.attr('instance.archived', false);

        let result = viewModel.attr('isAllowedToEdit');
        expect(result).toBe(false);
      });

      it('if object is changeable externally', () => {
        spyOn(Permission, 'isAllowedFor').and.returnValue(true);
        spyOn(SnapshotUtils, 'isSnapshot').and.returnValue(false);

        let instance = makeFakeInstance({
          model: Cacheable,
          staticProps: {
            isChangeableExternally: true,
          },
        })({
          archived: false,
        });

        viewModel.attr('instance', instance);

        let result = viewModel.attr('isAllowedToEdit');
        expect(result).toBe(false);
      });

      it('if instance is readonly', () => {
        spyOn(Permission, 'isAllowedFor').and.returnValue(true);
        spyOn(SnapshotUtils, 'isSnapshot').and.returnValue(false);
        viewModel.attr('instance.type', 'Type');
        viewModel.attr('instance.archived', false);
        viewModel.attr('instance.readonly', true);

        let result = viewModel.attr('isAllowedToEdit');
        expect(result).toBe(false);
      });
    });

    describe('returns true', () => {
      it('if allowed to edit instance', () => {
        spyOn(Permission, 'isAllowedFor').and.returnValue(true);
        spyOn(SnapshotUtils, 'isSnapshot').and.returnValue(false);
        viewModel.attr('instance.type', 'Type');
        viewModel.attr('instance.archived', false);
        viewModel.attr('instance.readonly', false);

        let result = viewModel.attr('isAllowedToEdit');
        expect(result).toBe(true);
      });
    });
  });
});
