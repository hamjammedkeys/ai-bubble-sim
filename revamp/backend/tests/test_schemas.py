from datetime import datetime, timezone

from app.models import Edge, Entity
from app.schemas import EdgeOut, EntityOut


def test_entity_out_from_orm():
    e = Entity(id="ent1", name="OpenAI", entity_type="model_company", aliases=["OAI"])
    out = EntityOut.model_validate(e)
    assert out.id == "ent1"
    assert out.aliases == ["OAI"]


def test_edge_out_from_orm_carries_status_and_verification():
    edge = Edge(
        id="edge1",
        source_entity_id="a",
        target_entity_id="b",
        relationship_type="purchase_obligation",
        evidence_class="reported",
        value=11.9,
        status="approved",
        verification={"overall": "pass"},
        created_at=datetime.now(timezone.utc),
    )
    out = EdgeOut.model_validate(edge)
    assert out.id == "edge1"
    assert out.value == 11.9
    assert out.status == "approved"
    assert out.verification == {"overall": "pass"}
    assert out.created_at is not None
