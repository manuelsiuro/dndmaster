from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.db.models import Story
from app.schemas.story import StoryCreate, StoryRead

router = APIRouter(prefix="/stories", tags=["stories"])


@router.post("", response_model=StoryRead, status_code=status.HTTP_201_CREATED)
async def create_story(payload: StoryCreate, current_user: CurrentUser, db: DBSession) -> StoryRead:
    story = Story(
        owner_user_id=current_user.id,
        title=payload.title,
        description=payload.description,
    )
    db.add(story)
    await db.commit()
    await db.refresh(story)
    return StoryRead.model_validate(story)


@router.get("", response_model=list[StoryRead])
async def list_stories(current_user: CurrentUser, db: DBSession) -> list[StoryRead]:
    stories = await db.scalars(
        select(Story)
        .where(Story.owner_user_id == current_user.id)
        .order_by(Story.created_at.desc())
    )
    return [StoryRead.model_validate(item) for item in stories.all()]
