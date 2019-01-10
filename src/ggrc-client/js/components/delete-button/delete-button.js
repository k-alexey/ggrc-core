/*
    Copyright (C) 2018 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import {
  confirm,
  BUTTON_VIEW_CLOSE,
  bindXHRToButton,
} from '../../plugins/utils/modals';
import {handleAjaxError} from '../../plugins/utils/errors-utils';
import {Snapshot} from '../../models/service-models';
import {isSnapshotType} from '../../plugins/utils/snapshot-utils';

export default can.Component.extend({
  tag: 'delete-button',
  template: `
    <span>
      <i class="fa fa-trash"></i>
      Delete
    </span>`,
  viewModel: {
    define: {
      instance: {
        set(instance) {
          if (!(instance instanceof can.Model) && isSnapshotType(instance)) {
            instance = new Snapshot(instance);
          }
          return instance;
        },
      },
    },
    confirmDelete() {
      const instance = this.attr('instance');
      const model = instance.class;
      const modalSettings = {
        button_view:
          GGRC.mustache_path + '/modals/delete_cancel_buttons.mustache',
        model,
        instance,
        modal_title: 'Delete ' + model.title_singular,
        skip_refresh: true,
        content_view:
          GGRC.mustache_path + '/base_objects/confirm_delete.mustache',
      };

      import(/* webpackChunkName: "modalsCtrls" */'../../controllers/modals')
        .then(() => {
          const $target = $('<div class="modal hide"></div>');
          $target
            .modal()
            .ggrc_controllers_modals(modalSettings)
            .on('click', '[data-toggle="delete"]', () => {
              const dfd = this.onConfirm();

              bindXHRToButton(dfd, $target.find('[data-dismiss="modal"]'));
              bindXHRToButton(dfd, $target.find('[data-toggle="delete"]'));

              dfd.always(() => {
                $target.modal('hide').remove();
              });
            })
            .on('click.modal-form.close', '[data-dismiss="modal"]', () => {
              $target.modal('hide').remove();
            });
        });
    },
    onConfirm() {
      const instance = this.attr('instance');

      return instance.refresh().then(() => {
        return instance.destroy();
      }).then(() => {}, (error) => {
        if (error.status === 409) {
          return this.fetchRelatedObjects();
        } else {
          handleAjaxError(error);
        }
      });
    },
    fetchRelatedObjects() {
      return $.get(`/api/snapshots/${this.attr('instance.id')}/related_objects`)
        .then((rawData) => {
          const {
            relatedToOriginal,
            relatedToSnapshot,
          } = this.composeData(rawData);

          const originalObject = this.attr('instance.revision.content');

          confirm({
            modal_title: 'Warning',
            originalObject,
            relatedToOriginal,
            relatedToSnapshot,
            content_view:
              `${GGRC.mustache_path}/modals/snapshot-related-objects.mustache`,
            button_view: BUTTON_VIEW_CLOSE,
          });
        });
    },
    composeData(rawData) {
      let issues = rawData.Issue ? rawData.Issue : [];
      let assessments = rawData.Assessment ? rawData.Assessment : [];
      let relatedToSnapshot = [...assessments, ...issues];

      let relatedToOriginal = rawData.Snapshot ? rawData.Snapshot : [];

      return {
        relatedToSnapshot,
        relatedToOriginal,
      };
    },
  },
  events: {
    click() {
      this.viewModel.confirmDelete();
    },
  },
});
