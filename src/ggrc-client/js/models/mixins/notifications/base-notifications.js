/*
    Copyright (C) 2020 Google Inc.
    Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
*/

import Mixin from '../mixin';

export default class BaseNotifications extends Mixin {
}

Object.assign(BaseNotifications.prototype, {
  send_by_default: true,
  recipients: 'Admin,Primary Contacts,Secondary Contacts',
});
