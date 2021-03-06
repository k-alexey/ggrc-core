# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

import unittest

from datetime import datetime
from freezegun import freeze_time
from mock import patch

from ggrc.notifications import common
from ggrc import models
from integration.ggrc import TestCase
from integration.ggrc_workflows.generator import WorkflowsGenerator
from integration.ggrc.api_helper import Api
from integration.ggrc.generator import ObjectGenerator
from integration.ggrc.models import factories


@unittest.skip("unskip when import/export fixed for workflows")
class TestEnableAndDisableNotifications(TestCase):

  """ This class contains simple one time workflow tests that are not
  in the gsheet test grid
  """

  def setUp(self):
    super(TestEnableAndDisableNotifications, self).setUp()
    self.api = Api()
    self.wf_generator = WorkflowsGenerator()
    self.object_generator = ObjectGenerator()
    models.Notification.query.delete()

    self.random_objects = self.object_generator.generate_random_objects(2)
    _, self.user = self.object_generator.generate_person(
        user_role="Administrator")
    self.create_test_cases()

    def init_decorator(init):
      def new_init(self, *args, **kwargs):
        init(self, *args, **kwargs)
        if hasattr(self, "created_at"):
          self.created_at = datetime.now()
      return new_init

    models.Notification.__init__ = init_decorator(models.Notification.__init__)

  @patch("ggrc.notifications.common.send_email")
  def test_default_notifications_settings(self, mock_mail):

    with freeze_time("2015-02-01 13:39:20"):
      _, wf = self.wf_generator.generate_workflow(self.quarterly_wf)
      response, wf = self.wf_generator.activate_workflow(wf)

      self.assert200(response)

      user = models.Person.query.get(self.user.id)

    with freeze_time("2015-01-01 13:39:20"):
      _, notif_data = common.get_daily_notifications()
      self.assertNotIn(user.email, notif_data)

    with freeze_time("2015-01-29 13:39:20"):
      _, notif_data = common.get_daily_notifications()
      self.assertIn(user.email, notif_data)

  @patch("ggrc.notifications.common.send_email")
  def test_disabled_notifications(self, mock_mail):

    with freeze_time("2015-02-01 13:39:20"):
      _, wf = self.wf_generator.generate_workflow(self.quarterly_wf)
      response, wf = self.wf_generator.activate_workflow(wf)

      self.assert200(response)

      self.object_generator.generate_notification_setting(
          self.user.id, "Email_Digest", False)

      user = models.Person.query.get(self.user.id)

    with freeze_time("2015-01-01 13:39:20"):
      _, notif_data = common.get_daily_notifications()
      self.assertNotIn(user.email, notif_data)

    with freeze_time("2015-01-29 13:39:20"):
      _, notif_data = common.get_daily_notifications()
      self.assertNotIn(user.email, notif_data)

  @patch("ggrc.notifications.common.send_email")
  def test_enabled_notifications(self, mock_mail):

    with freeze_time("2015-02-01 13:39:20"):
      _, wf = self.wf_generator.generate_workflow(self.quarterly_wf)
      response, wf = self.wf_generator.activate_workflow(wf)
      self.assert200(response)

    with freeze_time("2015-01-29 13:39:20"):
      user = models.Person.query.get(self.user.id)
      _, notif_data = common.get_daily_notifications()
      self.assertIn(user.email, notif_data)

      self.object_generator.generate_notification_setting(
          self.user.id, "Email_Digest", True)

      user = models.Person.query.get(self.user.id)
      _, notif_data = common.get_daily_notifications()
      self.assertIn(user.email, notif_data)

  @patch("ggrc.notifications.common.send_email")
  def test_forced_notifications(self, mock_mail):

    with freeze_time("2015-02-01 13:39:20"):
      _, wf = self.wf_generator.generate_workflow(self.quarterly_wf_forced)
      response, wf = self.wf_generator.activate_workflow(wf)

      self.assert200(response)

      user = models.Person.query.get(self.user.id)

    with freeze_time("2015-01-29 13:39:20"):
      _, notif_data = common.get_daily_notifications()
      self.assertIn(user.email, notif_data)

      self.object_generator.generate_notification_setting(
          self.user.id, "Email_Digest", True)

      user = models.Person.query.get(self.user.id)
      _, notif_data = common.get_daily_notifications()
      self.assertIn(user.email, notif_data)

  @patch("ggrc.notifications.common.send_email")
  def test_force_one_wf_notifications(self, mock_mail):

    with freeze_time("2015-02-01 13:39:20"):
      _, wf_forced = self.wf_generator.generate_workflow(
          self.quarterly_wf_forced)
      response, wf_forced = self.wf_generator.activate_workflow(wf_forced)
      _, wf = self.wf_generator.generate_workflow(self.quarterly_wf)
      response, wf = self.wf_generator.activate_workflow(wf)

      self.assert200(response)

      user = models.Person.query.get(self.user.id)

    with freeze_time("2015-01-29 13:39:20"):
      _, notif_data = common.get_daily_notifications()
      self.assertIn(user.email, notif_data)
      self.assertIn("cycle_starts_in", notif_data[user.email])
      self.assertIn(wf_forced.id, notif_data[user.email]["cycle_starts_in"])
      self.assertIn(wf.id, notif_data[user.email]["cycle_starts_in"])

      self.object_generator.generate_notification_setting(
          self.user.id, "Email_Digest", False)

      user = models.Person.query.get(self.user.id)
      _, notif_data = common.get_daily_notifications()
      self.assertIn(user.email, notif_data)
      self.assertIn("cycle_starts_in", notif_data[user.email])
      self.assertIn(wf_forced.id, notif_data[user.email]["cycle_starts_in"])
      self.assertNotIn(wf.id, notif_data[user.email]["cycle_starts_in"])

  def create_test_cases(self):
    def person_dict(person_id):
      return {
          "href": "/api/people/%d" % person_id,
          "id": person_id,
          "type": "Person"
      }

    self.quarterly_wf_forced = {
        "title": "quarterly wf forced notifications",
        "notify_on_change": True,
        "description": "",
        # admin will be current user with id == 1
        "unit": "month",
        "repeat_every": 3,
        "task_groups": [{
            "title": "tg_1",
            "contact": person_dict(self.user.id),
            "task_group_tasks": [{
                "contact": person_dict(self.user.id),
                "description": factories.random_str(100),
            },
            ],
        },
        ]
    }

    self.quarterly_wf = {
        "title": "quarterly wf 1",
        "description": "",
        # admin will be current user with id == 1
        "unit": "month",
        "repeat_every": 3,
        "task_groups": [{
            "title": "tg_1",
            "contact": person_dict(self.user.id),
            "task_group_tasks": [{
                "contact": person_dict(self.user.id),
                "description": factories.random_str(100),
            },
            ],
        },
        ]
    }
