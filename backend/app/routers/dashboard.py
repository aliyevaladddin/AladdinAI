from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.agent import Agent
from app.models.deal import Deal
from app.models.contact import Contact
from app.models.activity import Activity
from app.models.user import User
from app.security import get_current_user
from app.schemas.crm import ActivityResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats")
async def get_dashboard_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Count active agents
    agents_result = await db.execute(select(func.count(Agent.id)).where(Agent.user_id == user.id, Agent.status == "running"))
    active_agents = agents_result.scalar() or 0

    # Count deals in progress (not won/lost)
    deals_result = await db.execute(
        select(func.count(Deal.id)).where(
            Deal.user_id == user.id, 
            Deal.stage.notin_(["won", "lost"])
        )
    )
    deals_in_progress = deals_result.scalar() or 0

    # Count total contacts
    contacts_result = await db.execute(select(func.count(Contact.id)).where(Contact.user_id == user.id))
    total_contacts = contacts_result.scalar() or 0

    # Get recent activities
    activities_result = await db.execute(
        select(Activity)
        .where(Activity.user_id == user.id)
        .order_by(Activity.created_at.desc())
        .limit(5)
    )
    recent_activities = activities_result.scalars().all()

    return {
        "active_agents": active_agents,
        "deals_in_progress": deals_in_progress,
        "total_contacts": total_contacts,
        "recent_activities": recent_activities,
        "system_status": "SECURE",
        "protocol": "RCF/2.0.3"
    }
