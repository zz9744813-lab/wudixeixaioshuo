from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import OutlineNode


def list_outline_nodes(
    db: Session,
    project_id: str,
    *,
    parent_id: str | None = None,
) -> list[OutlineNode]:
    stmt = (
        select(OutlineNode)
        .where(OutlineNode.project_id == project_id)
        .order_by(OutlineNode.order_index)
    )
    if parent_id is None:
        stmt = stmt.where(OutlineNode.parent_id.is_(None))
    else:
        stmt = stmt.where(OutlineNode.parent_id == parent_id)
    return list(db.execute(stmt).scalars().all())


def get_outline_node(db: Session, node_id: str) -> OutlineNode | None:
    return db.get(OutlineNode, node_id)


def create_outline_node(db: Session, payload: Any) -> OutlineNode:
    node = OutlineNode(**payload.model_dump())
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def update_outline_node(
    db: Session, node_id: str, payload: Any
) -> OutlineNode | None:
    node = db.get(OutlineNode, node_id)
    if not node:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(node, field, value)
    db.commit()
    db.refresh(node)
    return node


def delete_outline_node(db: Session, node_id: str) -> bool:
    node = db.get(OutlineNode, node_id)
    if not node:
        return False
    # Cascade: reassign children to parent
    children = db.execute(
        select(OutlineNode).where(OutlineNode.parent_id == node_id)
    ).scalars().all()
    for child in children:
        child.parent_id = node.parent_id
    db.delete(node)
    db.commit()
    return True


def get_outline_tree(db: Session, project_id: str) -> dict | None:
    """Return outline as a nested tree (root nodes with children)."""
    all_nodes = list_outline_nodes(db, project_id)
    node_map: dict[str, Any] = {}
    roots: list[Any] = []
    for n in all_nodes:
        node_map[str(n.id)] = {
            **{
                k: getattr(n, k)
                for k in [
                    "id",
                    "project_id",
                    "node_type",
                    "order_index",
                    "title",
                    "summary",
                    "target_words",
                    "parent_id",
                    "metadata",
                ]
            },
            "children": [],
        }
    for n in all_nodes:
        nid = str(n.id)
        if n.parent_id and str(n.parent_id) in node_map:
            node_map[str(n.parent_id)]["children"].append(node_map[nid])
        else:
            roots.append(node_map[nid])
    return {
        "roots": roots,
        "flat": [node_map[str(n.id)] for n in all_nodes],
    }
