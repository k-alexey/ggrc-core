# Copyright (C) 2020 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Import GGRC model hooks."""

from ggrc.models.hooks import common
from ggrc.models.hooks import assessment
from ggrc.models.hooks import audit
from ggrc.models.hooks import comment
from ggrc.models.hooks import custom_attribute_definition
from ggrc.models.hooks import issue
from ggrc.models.hooks import issue_tracker
from ggrc.models.hooks import relationship
from ggrc.models.hooks import acl
from ggrc.models.hooks import access_control_role
from ggrc.models.hooks import with_action


ALL_HOOKS = [
    access_control_role,
    assessment,
    audit,
    comment,
    issue,
    relationship,
    with_action,
    custom_attribute_definition,
    acl,
    common,

    # Keep IssueTracker at the end of list to make sure that all other hooks
    # are already executed and all data is final.
    issue_tracker,
]


def init_hooks():
  for hook in ALL_HOOKS:
    hook.init_hook()
