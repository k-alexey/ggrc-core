/*
 Copyright (C) 2020 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canList from 'can-list';
import Cacheable from '../cacheable';
import {getRole} from '../../plugins/utils/acl-utils';
import AccessControlList from '../mixins/access-control-list';
import UniqueTitle from '../mixins/unique-title';
import CaUpdate from '../mixins/ca-update';
import IssueTracker from '../mixins/issue-tracker';
import Stub from '../stub';
import Program from './program';

export default Cacheable.extend({
  root_object: 'audit',
  root_collection: 'audits',
  category: 'programs',
  findAll: 'GET /api/audits',
  findOne: 'GET /api/audits/{id}',
  update: 'PUT /api/audits/{id}',
  destroy: 'DELETE /api/audits/{id}',
  create: 'POST /api/audits',
  mixins: [
    AccessControlList,
    UniqueTitle,
    CaUpdate,
    IssueTracker,
  ],
  is_custom_attributable: true,
  is_clonable: true,
  isRoleable: true,
  attributes: {
    context: Stub,
    program: Stub,
    modified_by: Stub,
    audit_firm: Stub,
  },
  defaults: {
    status: 'Planned',
  },
  statuses: ['Planned', 'In Progress', 'Manager Review',
    'Ready for External Review', 'Completed', 'Deprecated'],
  obj_nav_options: {
    show_all_tabs: false,
    force_show_list: ['Assessment Templates',
      'Issues', 'Assessments', 'Evidence'],
  },
  tree_view_options: {
    add_item_view: 'audits/tree-add-item',
    attr_list: [{
      attr_title: 'Title',
      attr_name: 'title',
      order: 1,
    }, {
      attr_title: 'Code',
      attr_name: 'slug',
      order: 3,
    }, {
      attr_title: 'State',
      attr_name: 'status',
      order: 4,
    }, {
      attr_title: 'Last Updated Date',
      attr_name: 'updated_at',
      order: 5,
    }, {
      attr_title: 'Last Updated By',
      attr_name: 'modified_by',
      order: 6,
    }, {
      attr_title: 'Planned Start Date',
      attr_name: 'start_date',
      order: 7,
    }, {
      attr_title: 'Planned End Date',
      attr_name: 'end_date',
      order: 8,
    }, {
      attr_title: 'Last Deprecated Date',
      attr_name: 'last_deprecated_date',
      order: 9,
    }, {
      attr_title: 'Planned Report Period to',
      attr_name: 'report_period',
      attr_sort_field: 'report_end_date',
      order: 10,
    }, {
      attr_title: 'Audit Firm',
      attr_name: 'audit_firm',
      order: 11,
    }, {
      attr_title: 'Archived',
      attr_name: 'archived',
      order: 12,
    }, {
      attr_title: 'Description',
      attr_name: 'description',
      order: 13,
    }],
  },
  sub_tree_view_options: {
    default_filter: ['Product'],
  },
  buildIssueTrackerConfig() {
    return {
      hotlist_id: '766459',
      component_id: '188208',
      issue_severity: 'S2',
      issue_priority: 'P2',
      issue_type: 'PROCESS',
      enabled: false,
      people_sync_enabled: true,
    };
  },
}, {
  define: {
    title: {
      value: '',
      validate: {
        required: true,
        validateUniqueTitle: true,
      },
    },
    _transient_title: {
      value: '',
      validate: {
        validateUniqueTitle: true,
      },
    },
    program: {
      value: null,
      validate: {
        required: true,
      },
    },
    issue_tracker: {
      value: {},
      validate: {
        validateIssueTrackerComponentId: true,
      },
    },
    audit_firm: {
      value: null,
    },
  },
  clone: function (options) {
    let cloneModel = new this.constructor({
      operation: 'clone',
      cloneOptions: options.cloneOptions,
      program: this.program,
      title: this.title + new Date(),
    });

    delete cloneModel.custom_attribute_values;

    return cloneModel;
  },
  save: function () {
    // Make sure the context is always set to the parent program
    let _super = this._super;
    let args = arguments;
    if (!this.context || !this.context.id) {
      return Program.findInCacheById(this.program.id).refresh().
        then(function (program) {
          this.attr('context', program.context);
          return _super.apply(this, args);
        }.bind(this));
    }
    return _super.apply(this, args);
  },
  findRoles: function (roleName) {
    const auditRole = getRole('Audit', roleName);

    return new canList(this.access_control_list.filter((item) => {
      return item.ac_role_id === auditRole.id;
    }));
  },
});
