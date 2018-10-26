# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Module for ggrc background tasks."""

import json
import traceback
import uuid
from logging import getLogger
from functools import wraps
from time import time

from flask import request
from flask.wrappers import Response
from werkzeug import exceptions
from werkzeug.datastructures import Headers

from ggrc import db
from ggrc import settings
from ggrc.login import get_current_user
from ggrc.models.mixins import base
from ggrc.models.mixins import Base
from ggrc.models.deferred import deferred
from ggrc.models.mixins import Stateful
from ggrc.models.types import CompressedType
from ggrc.utils import benchmark

logger = getLogger(__name__)

BANNED_HEADERS = {
    "X-Appengine-Country",
    "X-Appengine-Queuename",
    "X-Appengine-Current-Namespace",
    "X-Appengine-Taskname",
    "X-Appengine-Tasketa",
    "X-Appengine-Taskexecutioncount",
    "X-Appengine-Taskretrycount",
    "X-Task-Name",
}

RETRY_OPTIONS = {
    "min_backoff_seconds": 30,
    "max_backoff_seconds": 3600,
    "max_doublings": 5,
    "task_retry_limit": 10,
}


class BackgroundTask(base.ContextRBAC, Base, Stateful, db.Model):
  """Background task model."""
  __tablename__ = 'background_tasks'

  VALID_STATES = [
      "Pending",
      "Running",
      "Success",
      "Failure"
  ]
  name = db.Column(db.String, nullable=False, unique=True)
  parameters = deferred(db.Column(CompressedType), 'BackgroundTask')
  result = deferred(db.Column(CompressedType), 'BackgroundTask')

  bg_operation = db.relationship(
      "BackgroundOperation",
      backref='bg_task',
      uselist=False
  )

  _aliases = {
      "status": {
          "display_name": "State",
          "mandatory": False,
          "description": "Options are: \n{}".format('\n'.join(VALID_STATES))
      }
  }

  def start(self):
    """Mark the current task as running."""
    self.status = "Running"
    db.session.add(self)
    db.session.commit()

  def finish(self, status, result):
    """Finish the current bg task."""
    # Ensure to not commit any not-yet-committed changes
    db.session.rollback()

    if isinstance(result, Response):
      self.result = {'content': result.response[0],
                     'status_code': result.status_code,
                     'headers': result.headers.items()}
    else:
      self.result = {'content': result,
                     'status_code': 200,
                     'headers': [('Content-Type', 'text/html')]}
    self.status = status
    db.session.add(self)
    db.session.commit()

  def make_response(self, default=None):
    """Create task status response."""
    if self.result is None:
      return default
    from ggrc.app import app
    return app.make_response((self.result['content'],
                              self.result['status_code'],
                              self.result['headers']))

  def task_scheduled_response(self):
    """Create success response with info about scheduled task."""
    from ggrc.app import app
    return self.make_response(
        app.make_response((
            json.dumps("scheduled %s" % self.name),
            200,
            [("Content-Type", "application/json")]
        ))
    )

  def get_content(self):
    """Get result content of the task."""
    try:
      content_json = self.result.get("content", "{}") if self.result else "{}"
      content = json.loads(content_json)
    except (TypeError, ValueError):
      content = {}
    return content


def collect_task_headers():
  """Get headers required for appengine background task run."""
  return Headers({k: v for k, v in request.headers if k not in BANNED_HEADERS})


# pylint: disable=too-many-locals
def create_task(name, url, **kwargs):
  """Create and enqueue a background task."""
  with benchmark("Create background task"):
    queued_callback = kwargs.get("queued_callback", None)
    parameters = kwargs.get("parameters", dict())
    method = kwargs.get("method", request.method)
    operation_type = kwargs.get("operation_type", None)
    payload = kwargs.get("payload", None)
    queue = kwargs.get("queue", "ggrc")
    retry_options = RETRY_OPTIONS.copy()
    retry_options.update(kwargs.get("retry_options", dict()))

    bg_operation, parent_type, parent_id = None, None, None
    if operation_type:
      if isinstance(parameters, dict):
        parent_type = parameters.get("parent", {}).get("type")
        parent_id = parameters.get("parent", {}).get("id")
      if bg_operation_running(operation_type, parent_type, parent_id):
        raise exceptions.BadRequest(
            "Task '{}' already run for {} {}.".format(
                operation_type, parent_type, parent_id
            )
        )
      bg_operation = create_bg_operation(operation_type,
                                         parent_type, parent_id)

    bg_task_name = "{}_{}".format(uuid.uuid4(), name)
    bg_task = BackgroundTask(
        name=bg_task_name,
        bg_operation=bg_operation,
        parameters=parameters,
        modified_by=get_current_user(),
    )
    db.session.add(bg_task)

    if getattr(settings, "APP_ENGINE", False):
      from google.appengine.api import taskqueue
      headers = collect_task_headers()
      headers.add("X-Task-Name", bg_task_name)
      queued_task_name = "{}_{}".format(uuid.uuid4(), bg_task_name)
      try:
        task = taskqueue.Queue(queue).add_async(
            taskqueue.Task(
                url=url,
                name=queued_task_name,
                params=parameters,
                payload=payload,
                method=method,
                headers=headers,
                retry_options=taskqueue.TaskRetryOptions(**retry_options),
            )
        )
      except taskqueue.Error:
        bg_task.status = "Failure"
      if not getattr(settings, "PROD_APPSERVER", False):
        # On local SDK development appserver we need to wait result
        # to successfully enqueue task.
        # In Google Cloud async adding tasks works properly.
        task.get_result()
    elif queued_callback:
      queued_callback(bg_task)
    else:
      raise ValueError("Either queued_callback should be provided "
                       "or APP_ENGINE set to true.")
    return bg_task


def create_lightweight_task(name, url, queued_callback=None, parameters=None,
                            method=None):
  """Create background task.

  This function create an app engine background task without handling
  related BackgroundTask object.
  """
  if not method:
    method = request.method

  if not parameters:
    parameters = {}

  if getattr(settings, 'APP_ENGINE', False):
    from google.appengine.api import taskqueue
    taskqueue.add(
        queue_name="ggrc",
        url=url,
        name="{}_{}".format(name + str(int(time())), uuid.uuid4()),
        payload=json.dumps(parameters),
        method=method,
        headers=collect_task_headers()
    )
  elif queued_callback:
    queued_callback(**parameters)
  else:
    raise ValueError(
        "Either queued_callback should be provided or APP_ENGINE set to true."
    )


def create_bg_operation(operation_type, object_type, object_id):
  """Create background task operation instance."""
  bg_operation = None
  if operation_type:
    from ggrc import models
    bg_operation_type = models.BackgroundOperationType.query.filter_by(
        name=operation_type
    ).first()

    if bg_operation_type and object_type and object_id:
      bg_operation = models.BackgroundOperation(
          object_type=object_type,
          object_id=object_id,
          bg_operation_type=bg_operation_type,
          modified_by=get_current_user()
      )
  return bg_operation


def bg_operation_running(operation_type, object_type, object_id):
  """Check if there is a background task in running state related to object."""
  from ggrc import models
  bg_task = models.BackgroundTask
  bg_operation = models.BackgroundOperation
  bg_type = models.BackgroundOperationType
  tasks = bg_task.query.join(
      bg_operation,
      bg_operation.bg_task_id == bg_task.id
  ).join(
      bg_type,
      bg_type.id == bg_operation.bg_operation_type_id
  ).filter(
      bg_operation.object_type == object_type,
      bg_operation.object_id == object_id,
      bg_type.name == operation_type,
      bg_task.status.in_(("Pending", "Running")),
  )
  return db.session.query(tasks.exists()).scalar()


def queued_task(func):
  """Decorator for task queues."""
  from ggrc.app import app

  @wraps(func)
  def decorated_view(*args, **_):
    """Background task runner.

    This runner makes sure that the task is called with the task model as
    the parameter.
    """
    if args and isinstance(args[0], BackgroundTask):
      task = args[0]
    else:
      task_name = request.headers.get("X-Task-Name")
      task = BackgroundTask.query.filter_by(name=task_name).first()
    if not task:
      return app.make_response(('BackgroundTask not found. Retry later.',
                                503,
                                [('Content-Type', 'text/html')]))
    task.start()
    try:
      result = func(task)
    except:  # pylint: disable=bare-except
      # Bare except is allowed here so that we can respond with the correct
      # message to all exceptions.
      logger.exception("Task failed")
      task.finish("Failure", app.make_response((
          traceback.format_exc(), 200, [('Content-Type', 'text/html')])))

      # Return 200 so that the task is not retried
      return app.make_response((
          'failure', 200, [('Content-Type', 'text/html')]))
    task.finish("Success", result)
    return result
  return decorated_view
