# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Add chain_logs

Create Date: 2018-12-04 18:01:45.989319
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '0d75d69ac2ea'
down_revision = '53e115488aec'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.create_table(
      'chain_log',
      sa.Column('id', sa.Integer(), nullable=False),
      sa.Column('created_at', sa.DateTime(), nullable=False),
      sa.Column('data', sa.Text, nullable=False),
      sa.PrimaryKeyConstraint('id')
  )


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  op.drop_table('chain_log')
