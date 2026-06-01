from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.outline import OutlineNodeCreate, OutlineNodeOut, OutlineNodeUpdate
from app.services.outline_service import (
    create_outline_node,
    delete_outline_node,
    get_outline_node,
    list_outline_nodes,
    update_outline_node,
    get_outline_tree,
)

router = APIRouter()


class OutlineTreeOut(BaseModel):
    roots: list[Any]
    flat: list[Any]


@router.get("/projects/{project_id}/outline")
async def get_outline_tree_endpoint(project_id: str, db: Session = Depends(get_db)):
    return get_outline_tree(db, project_id)


@router.get("/projects/{project_id}/outline/nodes")
async def list_outline_tree(project_id: str, parent_id: str | None = None, db: Session = Depends(get_db)):
    items = list_outline_nodes(db, project_id, parent_id=parent_id)
    return [OutlineNodeOut.model_validate(it) for it in items]


@router.post("/projects/{project_id}/outline/nodes", response_model=OutlineNodeOut, status_code=201)
async def create_node(project_id: str, payload: OutlineNodeCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    data["project_id"] = project_id
    node = create_outline_node(db, data)
    return OutlineNodeOut.model_validate(node)


@router.get("/projects/{project_id}/outline/nodes/{node_id}", response_model=OutlineNodeOut)
async def get_node(project_id: str, node_id: str, db: Session = Depends(get_db)):
    node = get_outline_node(db, node_id)
    if not node:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="outline node not found")
    return OutlineNodeOut.model_validate(node)


@router.put("/projects/{project_id}/outline/nodes/{node_id}", response_model=OutlineNodeOut)
async def update_node(project_id: str, node_id: str, payload: OutlineNodeUpdate, db: Session = Depends(get_db)):
    node = update_outline_node(db, node_id, payload)
    if not node:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="outline node not found")
    return OutlineNodeOut.model_validate(node)


@router.delete("/projects/{project_id}/outline/nodes/{node_id}")
async def delete_node(project_id: str, node_id: str, db: Session = Depends(get_db)):
    ok = delete_outline_node(db, node_id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="outline node not found")
    return {"ok": True}
