/*
 Copyright (C) 2020 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

import canMap from 'can-map';
import canComponent from 'can-component';
import canStache from 'can-stache';
import {loadComments} from '../../../plugins/utils/comments-utils';
import template from './assessment-mapped-comments.stache';

export default canComponent.extend({
  tag: 'assessment-mapped-comments',
  view: canStache(template),
  viewModel: canMap.extend({
    instance: {},
    mappedComments: [],
    showMore: false,
    isInitialized: false,
    isLoading: false,
    expanded: false,
    async initMappedComments() {
      try {
        this.attr('isLoading', true);
        const response =
          await loadComments(this.attr('instance'), 'Comment', 0, 5);
        let {values: comments, total} = response.Comment;

        this.attr('mappedComments', comments);
        this.attr('showMore', total > comments.length);
        this.attr('isInitialized', true);
      } finally {
        this.attr('isLoading', false);
      }
    },
  }),
  events: {
    '{viewModel} expanded'() {
      const needToMakeRequest = this.viewModel.attr('expanded') &&
        !this.viewModel.attr('isInitialized');
      if (needToMakeRequest) {
        this.viewModel.initMappedComments();
      }
    },
  },
});
