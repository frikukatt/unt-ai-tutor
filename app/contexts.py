from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TestContext
from app.schemas import TestContextCreate, TestContextPublic


router = APIRouter()


@router.post("/contexts", response_model=TestContextPublic)
def create_context(
    context: TestContextCreate,
    db: Session = Depends(get_db)
):
    db_context = TestContext(
        subject=context.subject,
        title=context.title,
        content=context.content
    )

    db.add(db_context)
    db.commit()
    db.refresh(db_context)

    return db_context


@router.get("/contexts", response_model=list[TestContextPublic])
def get_contexts(
    db: Session = Depends(get_db)
):
    return db.query(TestContext).all()


@router.get("/contexts/{context_id}", response_model=TestContextPublic)
def get_context(
    context_id: int,
    db: Session = Depends(get_db)
):
    context = (
        db.query(TestContext)
        .filter(TestContext.id == context_id)
        .first()
    )

    if not context:
        raise HTTPException(
            status_code=404,
            detail="Context not found"
        )

    return context