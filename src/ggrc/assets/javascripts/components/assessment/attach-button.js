/*!
 Copyright (C) 2017 Google Inc.
 Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
 */

(function (GGRC, can) {
  'use strict';

  var tag = 'attach-button';
  var template = can.view(GGRC.mustache_path +
    '/components/assessment/attach-button.mustache');

  GGRC.Components('attachButton', {
    tag: tag,
    template: template,
    confirmationCallback: '@',
    viewModel: {
      define: {
        hasPermissions: {
          get: function (prevValue, setValue) {
            var instance = this.attr('instance');
            if (Permission.is_allowed_for('update', instance) &&
              !instance.archived) {
              this.checkFolder().always(function () {
                setValue(true);
              });
            } else {
              setValue(false);
            }
          }
        }
      },
      assessmentTypeObjects: [],
      canAttach: false,
      isFolderAttached: false,
      checksPassed: false,
      error: {},
      instance: null,
      isAttachActionDisabled: false,
      onBeforeCreate: function (event) {
        var items = event.items;
        this.dispatch({type: 'beforeCreate', items: items});
      },
      itemsUploadedCallback: function () {
        this.dispatch('refreshEvidences');

        if (this.attr('instance')) {
          this.attr('instance').dispatch('refreshInstance');
        }
      },
      checkFolder: function () {
        var self = this;

        return this.findFolder().then(function (folder) {
          if (folder) {
            self.attr('isFolderAttached', true);
          }
          self.attr('canAttach', true);
        }, function (err) {
          self.attr('error', err);
          self.attr('canAttach', false);
        }).always(function () {
          self.attr('checksPassed', true);
        });
      },
      findFolder: function () {
        var GFolder = CMS.Models.GDriveFolder;
        var folderId = this.attr('instance.folder');

        if (!folderId) {
          this.attr('canAttach', true);
          return can.Deferred().resolve();
        }

        return GFolder.findOne({id: folderId});
      }
    }
  });
})(window.GGRC, window.can);
