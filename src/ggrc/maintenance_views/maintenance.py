# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""View functions for maintenance"""

# pylint: disable=invalid-name
# pylint: disable=no-else-return

import re

from logging import getLogger
from ggrc.maintenance import maintenance_app
from ggrc import db
from ggrc import migrate
from ggrc import settings
from ggrc.models.maintenance import Maintenance
from ggrc.models.maintenance import ChainLog
from ggrc.models.maintenance import MigrationLog
from ggrc.utils.maintenance_chain import jobs_status, trigger_next_job, JOBS

from google.appengine.api import users
from google.appengine.ext import deferred

from flask import json
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
import sqlalchemy

logger = getLogger(__name__)


@maintenance_app.route('/maintenance/index')
def index():
  """Renders admin maintenance dashboard."""
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
            "notify_email": notify_email}
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
