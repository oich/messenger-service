"""Fixed, named teams - defined once, reusable across rooms/projects for
bulk-inviting a whole group at once instead of one user at a time.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_admin_user, get_current_user
from app.database import get_db
from app.models import Team, UserMapping
from app.schemas.teams import TeamCreate, TeamOut, TeamUpdate, TeamMemberOut

logger = logging.getLogger("teams")
router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


def _to_out(team: Team, db: Session) -> TeamOut:
    member_ids = team.member_hub_user_ids or []
    users = {
        u.hub_user_id: u
        for u in db.query(UserMapping).filter(UserMapping.hub_user_id.in_(member_ids)).all()
    }
    members = [
        TeamMemberOut(
            hub_user_id=hub_user_id,
            display_name=users[hub_user_id].display_name if hub_user_id in users else None,
        )
        for hub_user_id in member_ids
    ]
    return TeamOut(
        id=team.id,
        name=team.name,
        members=members,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


@router.get("", response_model=List[TeamOut])
async def list_teams(
    current_user: UserMapping = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all teams - any authenticated user can see them, needed for the
    invite-a-team picker in the chat UI (only create/edit/delete is admin-only)."""
    teams = db.query(Team).order_by(Team.name).all()
    return [_to_out(t, db) for t in teams]


@router.post("", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
async def create_team(
    body: TeamCreate,
    admin: UserMapping = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")

    team = Team(name=name, member_hub_user_ids=list(dict.fromkeys(body.member_hub_user_ids)))
    db.add(team)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ein Team mit diesem Namen existiert bereits")
    db.refresh(team)
    return _to_out(team, db)


@router.patch("/{team_id}", response_model=TeamOut)
async def update_team(
    team_id: int,
    body: TeamUpdate,
    admin: UserMapping = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team nicht gefunden")

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Name darf nicht leer sein")
        team.name = name
    if body.member_hub_user_ids is not None:
        team.member_hub_user_ids = list(dict.fromkeys(body.member_hub_user_ids))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ein Team mit diesem Namen existiert bereits")
    db.refresh(team)
    return _to_out(team, db)


@router.delete("/{team_id}")
async def delete_team(
    team_id: int,
    admin: UserMapping = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team nicht gefunden")
    db.delete(team)
    db.commit()
    return {"ok": True, "deleted": team_id}
