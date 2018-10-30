# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for background_task model."""

from ggrc.models import all_models
from integration.ggrc import api_helper
from integration.ggrc import TestCase


class TestBackgroundTask(TestCase):
  """Tests for background task model."""

  def setUp(self):
    """setUp, nothing else to add."""
    super(TestBackgroundTask, self).setUp()
    self.api = api_helper.Api()

  def test_bg_task_from_post(self):
    """Test filtering of GET response for BackgroundTask"""
    control_dict = {
        "control": {
            "title": "Control title",
            "context": None,
        },
    }
    response = self.api.send_request(
        self.api.client.post,
        all_models.Control,
        control_dict,
        {"X-GGRC-BackgroundTask": "true"},
    )
    self.assertEqual(response.status_code, 201)
    bg_tasks = all_models.BackgroundTask.query.all()
    self.assertEqual(len(bg_tasks), 1)

    content = self.api.client.get("/api/background_tasks")
    self.assert200(content)
    bg_tasks_content = \
        content.json['background_tasks_collection']['background_tasks']
    self.assertEqual(len(bg_tasks_content), 1)
    self.assertEqual(set(bg_tasks_content[0].keys()), {"id", "status"})

    task_id = bg_tasks[0].id
    content = self.api.client.get("/api/background_tasks/{}".format(task_id))
    self.assert200(content)
    bg_task_content = \
        content.json['background_task']
    self.assertEqual(set(bg_task_content.keys()), {"id", "status"})
