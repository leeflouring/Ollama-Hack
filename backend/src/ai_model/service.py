from fastapi import Depends, HTTPException, status
from fastapi_pagination import Page, Params, set_page
from fastapi_pagination.ext.sqlmodel import apaginate
from sqlalchemy import and_, case, exists, func, or_
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from src.database import DBSessionDep
from src.schema import SortOrder

from .models import AIModelDB, AIModelStatusEnum, EndpointAIModelDB
from .schemas import (
    AIModelFilterParams,
    AIModelInfoWithEndpoint,
    AIModelInfoWithEndpointCount,
    AIModelPerformance,
    AIModelWithEndpointRequest,
    ModelFromEndpointInfo,
)


async def get_ai_models(
    session: DBSessionDep,
    params: AIModelFilterParams = Depends(),
) -> Page[AIModelDB]:
    """
    Get all AI models with filtering, searching and sorting.
    """
    set_page(Page[AIModelDB])
    query = select(AIModelDB)

    # 添加搜索条件
    if params.search:
        if ":" in params.search:
            model_name, model_tag = params.search.split(":", 1)
            query = query.where(
                and_(
                    col(AIModelDB.name).ilike(f"%{model_name}%"),
                    col(AIModelDB.tag).ilike(f"%{model_tag}%"),
                )
            )
        else:
            query = query.where(
                or_(
                    col(AIModelDB.name).ilike(f"%{params.search}%"),
                    col(AIModelDB.tag).ilike(f"%{params.search}%"),
                )
            )

    # 添加基本排序
    if params.order_by:
        order_column = getattr(AIModelDB, params.order_by.value)
        if params.order == SortOrder.DESC:
            order_column = order_column.desc()
        query = query.order_by(order_column)

    if params.is_available:
        subquery = select(EndpointAIModelDB).where(
            (EndpointAIModelDB.ai_model_id == AIModelDB.id)
            & (EndpointAIModelDB.status == AIModelStatusEnum.AVAILABLE)
        )
        query = query.where(exists(subquery))

    return await apaginate(session, query, params)


async def get_endpoint_counts(
    session: DBSessionDep, ai_model_ids: list[int]
) -> dict[int, tuple[int, int]]:
    if not ai_model_ids:
        return {}

    result = await session.execute(
        select(
            EndpointAIModelDB.ai_model_id,
            func.count(),
            func.coalesce(
                func.sum(
                    case((EndpointAIModelDB.status == AIModelStatusEnum.AVAILABLE, 1), else_=0)
                ),
                0,
            ),
        )
        .where(col(EndpointAIModelDB.ai_model_id).in_(ai_model_ids))
        .group_by(EndpointAIModelDB.ai_model_id)
    )
    return {
        model_id: (int(total_count), int(available_count))
        for model_id, total_count, available_count in result.all()
    }


async def get_endpoint_count(session: DBSessionDep, ai_model_id: int) -> tuple[int, int]:
    """
    Get the count of endpoints for an AI model.
    """
    return (await get_endpoint_counts(session, [ai_model_id])).get(ai_model_id, (0, 0))


async def get_ai_models_endpoint_counts(
    session: DBSessionDep, filter_params: AIModelFilterParams = Depends()
) -> Page[AIModelInfoWithEndpointCount]:
    """
    Get all AI models with endpoint count, with support for filtering, searching and sorting.
    """
    ai_models = await get_ai_models(session, filter_params)

    set_page(Page[AIModelInfoWithEndpointCount])

    model_ids = [ai_model.id for ai_model in ai_models.items if ai_model.id is not None]
    endpoint_counts = await get_endpoint_counts(session, model_ids)

    ai_models_with_endpoint_count = []
    for ai_model in ai_models.items:
        if ai_model.id is None:
            continue
        total_endpoint_count, avaliable_endpoint_count = endpoint_counts.get(ai_model.id, (0, 0))
        ai_models_with_endpoint_count.append(
            AIModelInfoWithEndpointCount(
                id=ai_model.id,
                name=ai_model.name,
                tag=ai_model.tag,
                created_at=ai_model.created_at,
                total_endpoint_count=total_endpoint_count,
                avaliable_endpoint_count=avaliable_endpoint_count,
            )
        )

    return Page(
        items=ai_models_with_endpoint_count,
        total=ai_models.total,
        page=ai_models.page,
        size=ai_models.size,
        pages=ai_models.pages,
    )


async def get_ai_model_with_endpoints(
    session: DBSessionDep, request: AIModelWithEndpointRequest = Depends()
) -> AIModelInfoWithEndpoint:
    """
    Get an AI model with its endpoints.
    """
    ai_model = await get_ai_model_by_id(session, request.ai_model_id)
    links = await get_endpoint_links_by_ai_model_id(session, request.ai_model_id, request)
    endpoints: list[ModelFromEndpointInfo] = []
    for link in links.items:
        endpoint = ModelFromEndpointInfo(
            id=link.endpoint_id,
            url=link.endpoint.url,
            name=link.endpoint.name,
            created_at=link.endpoint.created_at,
            status=link.status,
            token_per_second=link.token_per_second,
            max_connection_time=link.max_connection_time,
            model_performances=[
                AIModelPerformance(**performance.model_dump())
                for performance in link.performances[:10]
            ],
        )
        endpoints.append(endpoint)
    total_endpoint_count, avaliable_endpoint_count = await get_endpoint_count(
        session, request.ai_model_id
    )

    return AIModelInfoWithEndpoint(
        id=ai_model.id,
        name=ai_model.name,
        tag=ai_model.tag,
        created_at=ai_model.created_at,
        total_endpoint_count=total_endpoint_count,
        avaliable_endpoint_count=avaliable_endpoint_count,
        endpoints=Page(
            items=endpoints,
            total=links.total,
            page=links.page,
            size=links.size,
            pages=links.pages,
        ),
    )


async def get_ai_model_by_id(session: DBSessionDep, ai_model_id: int) -> AIModelDB:
    """
    Get an AI model by ID.
    """
    query = select(AIModelDB).where(col(AIModelDB.id) == ai_model_id)
    result = await session.execute(query)
    ai_model = result.scalars().first()
    if ai_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI model not found")
    return ai_model


async def get_endpoint_links_by_ai_model_id(
    session: DBSessionDep,
    ai_model_id: int,
    params: Params = Depends(),
) -> Page[EndpointAIModelDB]:
    """
    Get all endpoint links with an AI model.
    """
    await get_ai_model_by_id(session, ai_model_id)

    set_page(Page[EndpointAIModelDB])

    # Base query to get endpoints through the association table
    query = (
        select(EndpointAIModelDB)
        .options(
            selectinload(EndpointAIModelDB.performances),  # type: ignore
            selectinload(EndpointAIModelDB.endpoint),  # type: ignore
        )
        .where(EndpointAIModelDB.ai_model_id == ai_model_id)
        .order_by(col(EndpointAIModelDB.token_per_second).desc())
    )
    return await apaginate(session, query, params)
