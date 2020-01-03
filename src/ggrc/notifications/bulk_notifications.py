# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""This module handles bulk assessment update notifications"""
from ggrc import db
from ggrc import login
from ggrc import settings

from ggrc.models import all_models
from ggrc.notifications import common
from ggrc.notifications.data_handlers import get_object_url


BULK_UPDATE_TITLE = "Bulk update of Assessments is finished"


def _create_notif_data(assessments):
  """Create data in format applicable for template rendering"""
  result = [
      {"title": assessment.title,
       "url": get_object_url(assessment)} for assessment in assessments
  ]
  return result


def send_notification(update_errors, partial_errors, asmnt_ids):
  """Send bulk complete job finished."""

  not_updated_asmnts = []
  if update_errors:
    not_updated_asmnts = db.session.query(all_models.Assessment).filter(
        all_models.Assessment.slug.in_(update_errors)
    ).all()

  partially_upd_asmnts = []
  if partial_errors:
    partially_upd_asmnts = db.session.query(all_models.Assessment).filter(
        all_models.Assessment.slug.in_(partial_errors)
    ).all()

  not_updated_ids = set(asmnt.id for asmnt in not_updated_asmnts)
  partially_upd_ids = set(asmnt.id for asmnt in partially_upd_asmnts)
  success_ids = set(asmnt_ids) - not_updated_ids - partially_upd_ids

  success_asmnts = []
  if success_ids:
    success_asmnts = db.session.query(all_models.Assessment).filter(
        all_models.Assessment.id.in_(success_ids)
    ).all()

  bulk_data = {
      "update_errors": _create_notif_data(not_updated_asmnts),
      "partial_errors": _create_notif_data(partially_upd_asmnts),
      "succeeded": _create_notif_data(success_asmnts),
  }
  body = settings.EMAIL_BULK_COMPLETE.render(sync_data=bulk_data)
  common.send_email(login.get_current_user().email, BULK_UPDATE_TITLE, body)
