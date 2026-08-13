from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Topic
from app.schemas import TopicCreate, TopicResponse


router = APIRouter()


@router.post("/topics", response_model=TopicResponse)
def create_topic(
    topic: TopicCreate,
    db: Session = Depends(get_db)
):
    db_topic = Topic(
        name=topic.name,
        subject=topic.subject
    )

    db.add(db_topic)
    db.commit()
    db.refresh(db_topic)

    return db_topic


@router.get("/topics", response_model=list[TopicResponse])
def get_topics(
    subject: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Topic)

    if subject:
        query = query.filter(Topic.subject == subject)

    return query.all()


@router.get("/topics/{topic_id}", response_model=TopicResponse)
def get_topic(
    topic_id: int,
    db: Session = Depends(get_db)
):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()

    if topic is None:
        raise HTTPException(
            status_code=404,
            detail="Topic not found"
        )

    return topic