import datetime
import uuid
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, Request, status
from fastapi_pagination import Page, set_page
from fastapi_pagination.ext.sqlmodel import apaginate
from sqlalchemy import case, false, func, or_
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from src.database import DBSessionDep
from src.logging import get_logger
from src.plan.models import PlanDB
from src.plan.service import get_user_plan
from src.schema import SortOrder
from src.user.models import UserDB
from src.user.service import get_current_user, get_user_by_id
from src.utils import now

from .models import ApiKeyDB, ApiKeyUsageLogDB
from .schemas import (
    ApiKeyCreate,
    ApiKeyFilterParams,
    ApiKeyInfo,
    ApiKeyUsageStats,
)

logger = get_logger(__name__)


def generate_api_key() -> str:
    """Generate a new random API key"""
    return str(uuid.uuid4())


async def create_api_key(
    session: DBSessionDep,
    api_key_data: ApiKeyCreate,
    user: UserDB = Depends(get_current_user),
) -> ApiKeyDB:
    """Create a new API key for the current user"""
    # Create the API key
    api_key = ApiKeyDB(
        key=generate_api_key(),
        name=api_key_data.name,
        user_id=user.id or 0,  # Ensure non-null value
    )

    # Save to database
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    return api_key


async def get_api_keys_for_user(
    session: DBSessionDep,
    user: UserDB = Depends(get_current_user),
    params: ApiKeyFilterParams = Depends(),
) -> Page[ApiKeyInfo]:
    """Get all API keys for the current user with filtering, searching and sorting"""
    # For admin users, return all API keys
    query = (
        select(ApiKeyDB)
        .options(selectinload(ApiKeyDB.user))  # type: ignore
        .where(ApiKeyDB.revoked == false())
    )

    if not user.is_admin:
        query = query.where(ApiKeyDB.user_id == user.id)

    # 添加搜索条件
    if params.search:
        search_term = f"%{params.search}%"
        query = query.where(or_(col(ApiKeyDB.name).ilike(search_term)))

    # 添加排序
    if params.order_by:
        order_column = getattr(ApiKeyDB, params.order_by.value)
        if params.order == SortOrder.DESC:
            order_column = order_column.desc()
        query = query.order_by(order_column)

    set_page(Page[ApiKeyDB])
    api_key_db_page: Page[ApiKeyDB] = await apaginate(session, query, params)

    set_page(Page[ApiKeyInfo])
    return Page(
        items=[
            ApiKeyInfo(
                user_name=item.user.username,
                **item.model_dump(),
            )
            for item in api_key_db_page.items
        ],
        page=api_key_db_page.page,
        size=api_key_db_page.size,
        total=api_key_db_page.total,
        pages=api_key_db_page.pages,
    )


async def get_api_key_by_id(
    session: DBSessionDep,
    api_key_id: int,
    user: UserDB = Depends(get_current_user),
) -> ApiKeyDB:
    """Get an API key by ID"""
    # For admin users, allow access to any API key
    query = (
        select(ApiKeyDB)
        .options(selectinload(ApiKeyDB.user))  # type: ignore
        .where(ApiKeyDB.id == api_key_id)
    )

    if not user.is_admin:
        query = query.where(ApiKeyDB.user_id == user.id)

    result = await session.execute(query)
    api_key = result.scalars().first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return api_key


async def delete_api_key(
    session: DBSessionDep,
    api_key_id: int,
    user: UserDB = Depends(get_current_user),
) -> None:
    """Delete (revoke) an API key"""
    api_key = await get_api_key_by_id(session, api_key_id, user)

    # Mark as revoked instead of deleting
    api_key.revoked = True

    await session.commit()


async def get_api_key_by_key(
    session: DBSessionDep,
    key: str,
) -> ApiKeyDB:
    """Get an API key by the actual key value"""
    result = await session.execute(
        select(ApiKeyDB).where(ApiKeyDB.key == key, ApiKeyDB.revoked == false())
    )
    api_key = result.scalars().first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key


async def validate_api_key(
    session: DBSessionDep,
    key: str,
) -> Tuple[ApiKeyDB, UserDB, PlanDB]:
    """Validate an API key and return the key, user and plan"""
    api_key = await get_api_key_by_key(session, key)

    # Update last used time
    api_key.last_used_at = now()

    # Get user separately to avoid async/greenlet issues
    user = await get_user_by_id(session, api_key.user_id)

    # Get plan
    plan = await get_user_plan(session, user)
    await session.commit()

    return api_key, user, plan


async def log_api_key_usage(
    session: DBSessionDep,
    api_key_id: int,
    endpoint: str,
    method: str,
    model: Optional[str],
    status_code: int,
) -> Optional[ApiKeyUsageLogDB]:
    """Log API key usage"""
    # Create usage log
    usage_log = ApiKeyUsageLogDB(
        api_key_id=api_key_id,
        endpoint=endpoint,
        method=method,
        model=model,
        status_code=status_code,
    )

    # Save to database
    session.add(usage_log)
    await session.commit()
    await session.refresh(usage_log)

    return usage_log


async def get_api_key_from_request(
    request: Request,
    session: DBSessionDep,
) -> Tuple[ApiKeyDB, UserDB, PlanDB]:
    """Extract and validate API key from request"""
    # Get API key from header or query param
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        # Try to get from query param
        api_key = request.query_params.get("api_key")

    if not api_key:
        # Try to get from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header.replace("Bearer ", "")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing",
        )

    return await validate_api_key(session, api_key)


async def check_rate_limits(
    session: DBSessionDep,
    api_key: ApiKeyDB,
    plan: PlanDB,
) -> None:
    """Check if the API key has exceeded rate limits"""
    await session.refresh(api_key)
    await session.refresh(plan)
    _now = now()

    # Check RPM (requests per minute)
    one_minute_ago = _now - datetime.timedelta(minutes=1)
    rpm_result = await session.execute(
        select(func.count())
        .select_from(ApiKeyUsageLogDB)
        .where(
            ApiKeyUsageLogDB.api_key_id == api_key.id,
            ApiKeyUsageLogDB.timestamp >= one_minute_ago,
            ApiKeyUsageLogDB.status_code < 400,
        )
    )
    rpm_count = rpm_result.scalar_one()

    if rpm_count >= plan.rpm:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {rpm_count}/{plan.rpm} requests per minute",
        )

    # Check RPD (requests per day)
    today_start = _now.replace(hour=0, minute=0, second=0, microsecond=0)
    rpd_result = await session.execute(
        select(func.count())
        .select_from(ApiKeyUsageLogDB)
        .where(
            ApiKeyUsageLogDB.api_key_id == api_key.id,
            ApiKeyUsageLogDB.timestamp >= today_start,
            ApiKeyUsageLogDB.status_code < 400,
        )
    )
    rpd_count = rpd_result.scalar_one()

    if rpd_count >= plan.rpd:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {rpd_count}/{plan.rpd} requests per day",
        )


async def get_api_key_usage_stats(
    session: DBSessionDep,
    api_key_id: int,
    user: UserDB = Depends(get_current_user),
) -> ApiKeyUsageStats:
    """Get usage statistics for an API key"""
    # Get the API key (this function now handles admin permissions)
    api_key = await get_api_key_by_id(session, api_key_id, user)

    _now = now()
    today_start = _now.replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = _now - datetime.timedelta(days=30)

    summary = (
        await session.execute(
            select(
                func.count().label("total_requests"),
                func.coalesce(
                    func.sum(case((ApiKeyUsageLogDB.timestamp >= thirty_days_ago, 1), else_=0)),
                    0,
                ).label("last_30_days_requests"),
                func.coalesce(
                    func.sum(case((ApiKeyUsageLogDB.timestamp >= today_start, 1), else_=0)),
                    0,
                ).label("requests_today"),
                func.coalesce(
                    func.sum(case((ApiKeyUsageLogDB.status_code < 400, 1), else_=0)),
                    0,
                ).label("successful_requests"),
                func.coalesce(
                    func.sum(case((ApiKeyUsageLogDB.status_code >= 400, 1), else_=0)),
                    0,
                ).label("failed_requests"),
            )
            .select_from(ApiKeyUsageLogDB)
            .where(ApiKeyUsageLogDB.api_key_id == api_key.id)
        )
    ).one()

    daily_start = today_start - datetime.timedelta(days=29)
    day_expression = func.date(ApiKeyUsageLogDB.timestamp)
    daily_result = await session.execute(
        select(day_expression, func.count())
        .where(
            ApiKeyUsageLogDB.api_key_id == api_key.id,
            ApiKeyUsageLogDB.timestamp >= daily_start,
            ApiKeyUsageLogDB.timestamp < today_start + datetime.timedelta(days=1),
        )
        .group_by(day_expression)
    )
    daily_counts = {str(day): int(count) for day, count in daily_result.all()}
    daily_stats = []
    for i in range(30):
        day = _now - datetime.timedelta(days=i)
        date = day.strftime("%Y-%m-%d")
        daily_stats.append({"date": date, "count": daily_counts.get(date, 0)})

    return ApiKeyUsageStats(
        total_requests=summary.total_requests,
        last_30_days_requests=summary.last_30_days_requests,
        requests_today=summary.requests_today,
        successful_requests=summary.successful_requests,
        failed_requests=summary.failed_requests,
        requests_per_day=daily_stats,
    )
