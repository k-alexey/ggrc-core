# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Add task_name to ImportExport

Create Date: 2018-09-25 12:38:16.424880
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from alembic import op

# revision identifiers, used by Alembic.
revision = 'ecbb2a60aeb1'
down_revision = 'b75a3fba7d6e'


def upgrade():
    """Upgrade database schema and/or data, creating a new revision."""
    op.add_column('import_exports', sa.Column('task_name', mysql.VARCHAR(length=250), nullable=True))

def downgrade():
    """Downgrade database schema and/or data back to the previous revision."""
    op.drop_column('import_exports', 'task_name')
