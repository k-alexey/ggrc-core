# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""View functions for maintenance"""

# pylint: disable=invalid-name
# pylint: disable=no-else-return

import json
import re
import uuid
from functools import wraps
from logging import getLogger

import sqlalchemy
from flask import json
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from google.appengine.api import users
from google.appengine.ext import deferred

from ggrc import db
from ggrc import migrate
from ggrc import settings
from ggrc.maintenance import maintenance_app
from ggrc.models.maintenance import ChainLog
from ggrc.models.maintenance import Maintenance
from ggrc.models.maintenance import MigrationLog
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


logger = getLogger(__name__)


def login_app():
  """Login into main app"""
  import flask_login
  from ggrc.login import get_login_module
  login_module = get_login_module()
  user = login_module.get_user()
  if user.system_wide_role != 'No Access':
    flask_login.login_user(user)


@maintenance_app.route('/maintenance/index')
def index():
  """Renders admin maintenance dashboard."""
  login_app()
  gae_user = users.get_current_user()
  if not (gae_user and gae_user.email() in settings.BOOTSTRAP_ADMIN_USERS):
    return "Unauthorized", 403
  maintenance = Maintenance.query.get(1)
  mode = "ON" if maintenance and maintenance.under_maintenance else "OFF"
  context = {"maintenance_mode": mode}
  context.update(jobs_status())
  context.update(migration_status())
  return render_template("maintenance/trigger.html", **context)


def migration_status():
  """Returns dict with last migration status"""
  result = {'migration_status': 'Not started'}
  if session.get('migration_started'):
    try:
      row = db.session.query(MigrationLog).order_by(
        MigrationLog.id.desc()).first()
      if row:
        if row.log:
          result = {'migration_status': 'Error'}
        elif row.is_migration_complete:
          result = {'migration_status': 'Complete'}
        else:
          result = {'migration_status': 'In progress'}
    except sqlalchemy.exc.ProgrammingError as err:
      if not re.search(r"""\(1146, "Table '.+' doesn't exist"\)$""",
                       err.message):
        raise
  return result


def jobs_status():
  """Returns dict with status on jobs.
  Hide chain <div> in case of missing table"""
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


def trigger_migration():
  """Triggers a deferred task for migration."""
  try:
    maint_row = db.session.query(Maintenance).get(1)
    if maint_row and maint_row.under_maintenance:
      logger.info(
          'System is under maintenance. Try running migration later.')
      return None
    mig_row = MigrationLog(is_migration_complete=False)
    db.session.add(mig_row)

    # Set the db flag before running migrations
    if maint_row:
      maint_row.under_maintenance = True
    else:
      maint_row = Maintenance(id=1, under_maintenance=True)
      db.session.add(maint_row)
    db.session.plain_commit()
  except sqlalchemy.exc.ProgrammingError as e:
    if re.search(r"""\(1146, "Table '.+' doesn't exist"\)$""", e.message):
      mig_row = None
    else:
      raise

  mig_row_id = mig_row.id if mig_row else 0
  deferred.defer(migrate.migrate, row_id=mig_row_id, _queue='ggrc')
  session['migration_started'] = True
  return mig_row_id


@maintenance_app.route('/maintenance/migrate', methods=['POST'])
def run_migration():
  """Allow authenticated user or with valid access token to run migration."""
  if "access_token" not in request.form:
    gae_user = users.get_current_user()
    if not (gae_user and gae_user.email() in settings.BOOTSTRAP_ADMIN_USERS):
      return json.dumps({"message": "Unauthorized"}), 403

    trigger_migration()
    return redirect(url_for('index'))

  if not (hasattr(settings, 'ACCESS_TOKEN') and
          request.form.get("access_token") == settings.ACCESS_TOKEN):
    logger.error("Invalid access token: %s", request.form.get("access_token"))
    return json.dumps({"message": "Unauthorized"}), 403

  mig_row_id = trigger_migration()
  data = {'migration_task_id': mig_row_id,
          'message': 'Migration is running in background'}
  return json.dumps(data), 202


def _turn_on_maintenance_mode():
  """Turn off maintenance mode."""
  db_row = db.session.query(Maintenance).get(1)
  if not db_row:
    db_row = Maintenance(id=1)
  db_row.under_maintenance = True
  db.session.add(db_row)
  db.session.commit()
  return redirect(url_for('index'))


@maintenance_app.route('/maintenance/turn_on_maintenance_mode',
                       methods=['POST'])
def turn_on_maintenance_mode():
  """Allow authenticated user to turn off maintenance mode."""
  if "access_token" not in request.form:
    gae_user = users.get_current_user()
    if not (gae_user and
            gae_user.email() in settings.BOOTSTRAP_ADMIN_USERS):
      return "Unauthorized", 403

    return _turn_on_maintenance_mode() or ""

  if not (hasattr(settings, 'ACCESS_TOKEN') and
          request.form.get("access_token") == settings.ACCESS_TOKEN):
    logger.error("Invalid access token: %s", request.form.get("access_token"))
    return "Unauthorized", 403

  return _turn_on_maintenance_mode(), 202


def _turn_off_maintenance_mode():
  """Turn off maintenance mode."""
  db_row = db.session.query(Maintenance).get(1)
  if db_row:
    db_row.under_maintenance = False
    db.session.add(db_row)
    db.session.commit()
  return redirect(url_for('index'))


@maintenance_app.route('/maintenance/turn_off_maintenance_mode',
                       methods=['POST'])
def turn_off_maintenance_mode():
  """Allow authenticated user to turn off maintenance mode."""
  if "access_token" not in request.form:
    gae_user = users.get_current_user()
    if not (gae_user and
            gae_user.email() in settings.BOOTSTRAP_ADMIN_USERS):
      return "Unauthorized", 403

    return _turn_off_maintenance_mode() or ""

  if not (hasattr(settings, 'ACCESS_TOKEN') and
          request.form.get("access_token") == settings.ACCESS_TOKEN):
    logger.error("Invalid access token: %s", request.form.get("access_token"))
    return "Unauthorized", 403

  return _turn_off_maintenance_mode(), 202


@maintenance_app.route('/maintenance/check_migration_status/<row_id>',
                       methods=['GET'])
def check_migration_status(row_id):
  """Checks and returns the status of migration."""
  try:
    maint_row = db.session.query(Maintenance).get(1)
    mig_row = db.session.query(MigrationLog).get(row_id)
    if not (mig_row and maint_row):
      data = {"status": "Fail",
              "message": "No migration entry in db."}
      return json.dumps(data), 202

    if mig_row.log:
      data = {"status": "Fail",
              "message": "Migration failed : {}".format(mig_row.log)}
      return json.dumps(data), 202

    if not mig_row.is_migration_complete:
      return json.dumps({"status": "In progress"}), 202

    return json.dumps({"status": "Complete"}), 202

  except sqlalchemy.exc.ProgrammingError as e:
    logger.error(e.message)
    if not re.search(r"""\(1146, "Table '.+' doesn't exist"\)$""", e.message):
      raise


@maintenance_app.route('/maintenance/jobs', methods=['GET'])
def trigger_jobs_chain():
  """Starts post-deployment jobs chain"""
  login_app()
  gae_user = users.get_current_user()
  if not (gae_user and gae_user.email() in settings.BOOTSTRAP_ADMIN_USERS):
    return "Unauthorized", 403

  jobs = {key: "Planned" for key, value in request.values.items()
          if key in JOBS and value.lower() == "on"}
  maintenance = request.values.get("maintenance", "off").lower() == "on"
  notify_email = request.values.get("notify_email", "")
  try:
    data = {"jobs": jobs,
            "maintenance": maintenance,
            "notify_email": notify_email,
            "status": "Not Finished"}
    chain = ChainLog(data=json.dumps(data))
    db.session.add(chain)
    db.session.commit()
    if maintenance:
      _turn_on_maintenance_mode()
    trigger_next_job(chain.id)
  except sqlalchemy.exc.ProgrammingError as error:
    if re.search(r"\(1146, \"Table '.+' doesn't exist\"\)$", error.message):
      return error.message, 500
    else:
      raise
  return redirect(url_for('index'))


@maintenance_app.route('/maintenance/chain_status')
def get_chain_status():
  """Return status of last chain"""
  chain = db.session.query(ChainLog).order_by(
      ChainLog.id.desc()).limit(1).first()
  data = json.loads(chain.data)
  return maintenance_app.make_response(
      (data.get("status", "None"), 200, [("Content-Type", "text/html")]))


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
  db.session.rollback()
  chain = db.session.query(ChainLog).get(chain_id)
  data = json.loads(chain.data)
  data["jobs"][job] = status
  chain.data = json.dumps(data)
  db.session.add(chain)
  db.session.commit()


def change_chain_status(chain_id, status):
  """Change status of chain in ChainLog model"""
  db.session.rollback()
  chain = db.session.query(ChainLog).get(chain_id)
  data = json.loads(chain.data)
  data["status"] = status
  chain.data = json.dumps(data)
  db.session.add(chain)
  db.session.commit()


def send_notification(chain_id):
  try:
    chain = db.session.query(ChainLog).get(chain_id)
    data = json.loads(chain.data)
    if not data["notify_email"]:
      return
    title = "{} deployment jobs report".format(settings.APPENGINE_INSTANCE)
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
