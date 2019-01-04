# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Snapshot API resource extension."""
from collections import defaultdict

from ggrc.services import common
from ggrc import utils
from ggrc.utils import referenced_objects


class SnapshotResource(common.ExtendedResource):
  """Resource handler for Snapshot."""

  # method post is abstract and not used.
  # pylint: disable=abstract-method

  def get(self, *args, **kwargs):
    # This is to extend the get request for additional data.
    # pylint: disable=arguments-differ
    command_map = {
        None: super(SnapshotResource, self).get,
        "related_objects": self.related_objects,
    }
    command = kwargs.pop("command", None)
    if command not in command_map:
      self.not_found_response()
    return command_map[command](*args, **kwargs)

  def related_objects(self, id):
    """Get data for snapshot related_objects page."""
    # id name is used as a kw argument and can't be changed here
    # pylint: disable=invalid-name,redefined-builtin
    from werkzeug.exceptions import Forbidden
    from ggrc import models
    from ggrc.rbac import permissions
    snapshot = models.Snapshot.query.get(id)
    if not snapshot:
      return self.not_found_response()
    if not permissions.is_allowed_read_for(snapshot):
      raise Forbidden()

    data = defaultdict(list)
    for obj in snapshot.related_objects():
      obj_data = _stub(obj)
      if obj.type == "Snapshot":
        child = referenced_objects.get(obj.child_type, obj.child_id)
        obj_data.update({
            "child": _stub(child),
            "revision:": {
                "content": {
                    "title": obj.revision.content.get("title", "")}}
        })
      data[obj.type].append(obj_data)
    return self.json_success_response(data, )


def _stub(obj):
  """Returns stub of object"""
  data = {
      "viewLink": utils.view_url_for(obj),
      "selfLink": utils.url_for(obj),
      "id": obj.id,
      "type": obj.type,
  }
  if hasattr(obj, "title"):
    data.update({"title": obj.title})
  return data
