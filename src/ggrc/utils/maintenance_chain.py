# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Utils for maintenance jobs execution in chain"""

import json
import re
import uuid
from functools import wraps
from logging import getLogger

import sqlalchemy
from flask import request

from ggrc import settings, db
from ggrc.notifications.common import send_email

URL_MAP = {
    "reindex": "/admin/reindex",
    "full_reindex": "/admin/full_reindex",
    "reindex_snapshots": "/admin/reindex_snapshots",
    "compute_attributes": "/admin/compute_attributes",
    "create_missing_revisions": "/admin/create_missing_revisions",
    "chain_migration": "/admin/chain_migration",
    "propagate_acl": "/admin/propagate_acl",
}

# List of jobs in reverse order
JOBS = [
    "propagate_acl",  # Last
    "reindex_snapshots",
    "reindex",
    "full_reindex",
    "compute_attributes",
    "create_missing_revisions",
    "chain_migration",  # First
]


# pylint: disable=invalid-name
logger = getLogger(__name__)


def request_endpoint(job, chain_id):
  """Sends request to job endpoint using taskqueue"""
  from ggrc.models.background_task import collect_task_headers
  if getattr(settings, 'APP_ENGINE', False):
    from google.appengine.api import taskqueue
    headers = collect_task_headers()
    headers.set("X-GGRC-Chain-id", chain_id)
    headers.set("X-GGRC-Chain-job", job)
    taskqueue.add(
        queue_name="ggrc",
        url=URL_MAP[job],
        name="{}_{}_chain".format(uuid.uuid4(), job),
        method="POST",
        headers=headers,
        retry_options=taskqueue.TaskRetryOptions(task_retry_limit=1)
    )


def trigger_next_job(chain_id):
  """Finds next job in chain and sends request to its endpoint"""
  from ggrc.maintenance_views.maintenance import _turn_off_maintenance_mode
  from ggrc.models.maintenance import ChainLog
  chain = db.session.query(ChainLog).get(chain_id)
  data = json.loads(chain.data)
  maintenance = data.get("maintenance", False)
  left_jobs = {k for k, v in data.get("jobs", {}).items() if v == "Planned"}
  left_jobs = [k for k in JOBS if k in left_jobs]  # ordering
  next_job = left_jobs.pop() if left_jobs else None
  if next_job:
    request_endpoint(next_job, chain_id)
  else:
    if maintenance:
      _turn_off_maintenance_mode()
    change_chain_status(chain_id, "Finished")
    send_notification(chain_id)


def change_job_status(chain_id, job, status):
  """Change status of job in ChainLog model"""
  from ggrc.models.maintenance import ChainLog
  db.session.rollback()
  chain = db.session.query(ChainLog).get(chain_id)
  data = json.loads(chain.data)
  data["jobs"][job] = status
  chain.data = json.dumps(data)
  db.session.add(chain)
  db.session.commit()


def change_chain_status(chain_id, status):
  """Change status of chain in ChainLog model"""
  from ggrc.models.maintenance import ChainLog
  db.session.rollback()
  chain = db.session.query(ChainLog).get(chain_id)
  data = json.loads(chain.data)
  data["status"] = status
  chain.data = json.dumps(data)
  db.session.add(chain)
  db.session.commit()


def send_notification(chain_id):
  try:
    from ggrc.models.maintenance import ChainLog
    chain = db.session.query(ChainLog).get(chain_id)
    data = json.loads(chain.data)
    if not data["notify_email"]:
      return
    title = "{} deployment status".format(settings.APPENGINE_INSTANCE)
    msg = {
        "title": title,
        "body": "<br>".join(
            "{}: {}".format(k, v) for k, v in data["jobs"].items())
    }
    body = settings.EMAIL_MAINTENANCE.render(maintenance=msg)
    send_email(data["notify_email"], title, body)
  except:  # pylint: disable=bare-except
    logger.exception("Failed on sending notification")


def chainable(func):
  """Decorator that tracks wrapped function in case of chained jobs"""
  @wraps(func)
  def wrapper(*args, **kw):
    """Help function"""
    chain_id = request.headers.get("X-GGRC-Chain-id")
    if chain_id:
      job = request.headers.get("X-GGRC-Chain-job")
      change_job_status(chain_id, job, "Running")
    try:

      result = func(*args, **kw)

    except Exception as err:
      if chain_id:
        change_job_status(chain_id, job, "Failed:{}".format(repr(err)))
        send_notification(chain_id)
        change_chain_status(chain_id, "Failed")
      raise
    if chain_id:
      change_job_status(chain_id, job, "Finished")
      trigger_next_job(chain_id)
    return result
  return wrapper


def jobs_status():
  """Returns dict with status on jobs.
  Hide chain <div> in case of missing table"""
  from ggrc.models.maintenance import ChainLog
  result = {"{}_status".format(k): "---" for k in JOBS}
  try:
    chain = db.session.query(ChainLog).order_by(
        ChainLog.id.desc()).limit(1).first()
  except sqlalchemy.exc.ProgrammingError as error:
    if re.search(r"\(1146, \"Table '.+' doesn't exist\"\)$", error.message):
      result["chain_style"] = "display: none;"
      return result
    else:
      raise
  if chain:
    result["created_at"] = chain.created_at
    for job, status in json.loads(chain.data)["jobs"].items():
      result[job + "_status"] = status
  return result
