# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Tests for /api/snapshot endpoints."""
import sqlalchemy as sa

from ggrc.models import all_models
from ggrc.models import Relationship
from integration.ggrc import api_helper
from integration.ggrc.models import factories
from integration.ggrc.services import TestCase


class TestSnapshotResourceDelete(TestCase):
  """Tests for special people api endpoints."""

  def setUp(self):
    super(TestSnapshotResourceDelete, self).setUp()
    self.client.get("/login")
    self.api = api_helper.Api()

  def _get_related_objects(self, snapshot_id):
    """Helper for retrieving snapshot related objects."""
    url = "/api/snapshots/{}/related_objects".format(snapshot_id)
    return self.client.get(url).json

  def test_snapshot_deletion(self):
    """Test that snapshot can be deleted only when it connected to audit"""
    # Prepare assessment with control and objective and raised issue
    control = factories.ControlFactory()
    revision = all_models.Revision.query.filter(
        all_models.Revision.resource_id == control.id,
        all_models.Revision.resource_type == control.__class__.__name__
    ).order_by(all_models.Revision.id.desc()).first()
    objective = factories.ObjectiveFactory()
    revision_o = all_models.Revision.query.filter(
        all_models.Revision.resource_id == control.id,
        all_models.Revision.resource_type == control.__class__.__name__
    ).order_by(all_models.Revision.id.desc()).first()
    with factories.single_commit():
      program = factories.ProgramFactory()
      audit = factories.AuditFactory(program=program)
      snapshot_c = factories.SnapshotFactory(
          parent=audit,
          child_id=control.id,
          child_type=control.__class__.__name__,
          revision_id=revision.id)
      snapshot_o = factories.SnapshotFactory(
          parent=audit,
          child_id=objective.id,
          child_type=objective.__class__.__name__,
          revision_id=revision_o.id)
      snapshot_c_id = snapshot_c.id
      assessment = factories.AssessmentFactory(audit=audit)
      assessment_id = assessment.id
      issue = factories.IssueFactory()
      issue_id = issue.id
      factories.RelationshipFactory(source=program, destination=control)
      factories.RelationshipFactory(source=program, destination=audit)
      factories.RelationshipFactory(source=snapshot_c, destination=audit)
      factories.RelationshipFactory(source=snapshot_o, destination=audit)
      factories.RelationshipFactory(source=assessment, destination=audit)
      factories.RelationshipFactory(source=snapshot_c, destination=assessment)
      factories.RelationshipFactory(source=snapshot_o, destination=assessment)
      factories.RelationshipFactory(source=issue, destination=audit)
      factories.RelationshipFactory(source=issue, destination=assessment)
      factories.RelationshipFactory(source=issue, destination=snapshot_c)
      factories.RelationshipFactory(source=issue, destination=snapshot_o)
      factories.RelationshipFactory(source=snapshot_c, destination=snapshot_o)

    # Check related_objects endpoint
    related_objects = self._get_related_objects(snapshot_c_id)
    self.assertEqual(len(related_objects), 4)
    self.assertEqual(len(related_objects["Assessment"]), 1)
    self.assertEqual(len(related_objects["Audit"]), 1)
    self.assertEqual(len(related_objects["Issue"]), 1)
    self.assertEqual(len(related_objects["Snapshot"]), 1)

    # Check validation forbids deletion with linked asmts and issues
    resp = self.api.delete(all_models.Snapshot, snapshot_c_id)
    self.assertEqual(resp.status_code, 409)

    # Unmap assessment and issue from control snapshot
    issue = all_models.Issue.query.get(issue_id)
    assessment = all_models.Assessment.query.get(assessment_id)
    snapshot_c = all_models.Snapshot.query.get(snapshot_c_id)
    issue_snapshot = Relationship.find_related(issue, snapshot_c).id
    asmt_snapshot = Relationship.find_related(assessment, snapshot_c).id
    self.api.delete(Relationship, issue_snapshot)
    self.api.delete(Relationship, asmt_snapshot)

    # Check related_objects endpoint
    related_objects = self._get_related_objects(snapshot_c_id)
    self.assertEqual(len(related_objects), 2)
    self.assertEqual(len(related_objects["Audit"]), 1)
    self.assertEqual(len(related_objects["Snapshot"]), 1)

    # Check successful deletion of control snapshot
    resp = self.api.delete(all_models.Snapshot, snapshot_c_id)
    self.assertEqual(resp.status_code, 200)
    self.assertFalse(all_models.Snapshot.query.get(snapshot_c_id))

    # Check that snapshot unmapped from all objects successfully
    relationships = Relationship.query.filter(
        sa.or_(
            sa.and_(
                Relationship.destination_id == snapshot_c_id,
                Relationship.destination_type == all_models.Snapshot.__name__),
            sa.and_(
                Relationship.source_id == snapshot_c_id,
                Relationship.source_type == all_models.Snapshot.__name__)
        )).all()
    self.assertFalse(relationships)
