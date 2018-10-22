# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Remove ACR for background tasks. Alter column background_tasks.name

Create Date: 2018-10-18 16:29:40.409113
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

import datetime
import sqlalchemy as sa

from sqlalchemy.dialects import mysql
from alembic import op
from ggrc.migrations.utils import acr_propagation


# revision identifiers, used by Alembic.
revision = 'd9c56989ac07'
down_revision = 'cb58d1d52368'

ROLE_NAME = "Admin"
OBJECT_TYPE = "BackgroundTask"


def upgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  condition = sa.and_(
      acr_propagation.ACR_TABLE.c.name == ROLE_NAME,
      acr_propagation.ACR_TABLE.c.object_type == OBJECT_TYPE,
  )
  op.execute(
      acr_propagation.ACL_TABLE.delete().where(
          acr_propagation.ACL_TABLE.c.ac_role_id.in_(
              sa.select([acr_propagation.ACR_TABLE.c.id]).where(condition)
          )
      )
  )
  op.execute(acr_propagation.ACR_TABLE.delete().where(condition))

  sql = """
      UPDATE background_tasks b
      SET b.name = UUID()
      WHERE b.name is null
  """
  op.execute(sql)

  sql = """
      UPDATE background_tasks b1
      JOIN background_tasks b2
      ON b1.name = b2.name AND b1.id != b2.id AND b1.id > b2.id
      SET b1.name = CONCAT(UUID(), "_", b1.name)
  """
  op.execute(sql)

  op.alter_column(
      'background_tasks',
      'name',
      existing_type=mysql.VARCHAR(length=250),
      nullable=False
  )
  op.create_unique_constraint(None, 'background_tasks', ['name'])


def downgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.execute(
      acr_propagation.ACR_TABLE.insert().values(
          name=ROLE_NAME,
          object_type=OBJECT_TYPE,
          parent_id=None,
          created_at=datetime.datetime.now(),
          updated_at=datetime.datetime.now(),
          internal=False,
          non_editable=True,
          read=True,
          update=True,
          delete=True,
          my_work=False,
      )
  )

  op.drop_constraint(None, 'background_tasks', type_='unique')
  op.alter_column(
      'background_tasks',
      'name',
      existing_type=mysql.VARCHAR(length=250),
      nullable=True
  )
