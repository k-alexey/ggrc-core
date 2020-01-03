# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for notifications for cycle task comments."""

from mock import patch

from ggrc.notifications import common
from ggrc.models import all_models
from integration.ggrc.models import factories
from integration.ggrc.notifications import test_assignable_notifications
from integration.ggrc_workflows.models import factories as wf_factories
from integration.ggrc import generator


class TestWorkflowCommentNotification(test_assignable_notifications.
                                      TestAssignableNotification):

  """Test notification on cycle task comments."""

  def setUp(self):
    super(TestWorkflowCommentNotification, self).setUp()
    self.client.get("/login")
    self._fix_notification_init()
    self.generator = generator.ObjectGenerator()

  @patch("ggrc.notifications.common.send_email")
  def test_ctgot_comments(self, _):
    """Test setting notification entries for ctgot comments.

    Check if the correct notification entries are created when a comment gets
    posted.
    """
    person = all_models.Person.query.first()
    secondary_assignee = self.create_user_with_role(role="Reader")
    task_assignees_emails = [person.email, secondary_assignee.email]
    recipients = {
        "Task Assignees": person,
        "Task Secondary Assignees": secondary_assignee,
    }
    with factories.single_commit():
      obj = wf_factories.CycleTaskGroupObjectTaskFactory(
          recipients=",".join(recipients),
          send_by_default=False,
      )
      # pylint: disable=protected-access
      for acl in obj._access_control_list:
        if acl.ac_role.name in recipients:
          recipient = recipients.get(acl.ac_role.name)
          if recipient:
            factories.AccessControlPersonFactory(
                ac_list=acl,
                person=recipient,
            )

    self.generator.generate_comment(
        obj, "", "some comment", send_notification="true")

    notifications, notif_data = common.get_daily_notifications()
    for email in task_assignees_emails:
      self.assertEqual(len(notifications), 1,
                       "Missing comment notification entry.")

      recip_notifs = notif_data.get(email, {})
      comment_notifs = recip_notifs.get("comment_created", {})
      self.assertEqual(len(comment_notifs), 1)

    self.client.get("/_notifications/send_daily_digest")
    notifications = self._get_notifications(notif_type="comment_created").all()
    self.assertEqual(len(notifications), 0,
                     "Found a comment notification that was not sent.")
