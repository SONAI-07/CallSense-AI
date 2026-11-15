from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Auth.dependencies import get_current_tenant
from app.core.database import get_db
from app.models.tenant import Tenant
from app.repositories.customer_repo import CustomerRepository
from app.schemas.customer_schema import CustomerResponse
from app.models.customer import Customer
from app.schemas.customer_schema import CustomerCreateRequest
from fastapi import status


router = APIRouter(
    prefix="/customers",
    tags=["customers"],
)

customer_repository = CustomerRepository()


@router.get(
    "",
    response_model=list[CustomerResponse],
)
async def list_customers(
        tenant: Tenant = Depends(get_current_tenant),
        db: AsyncSession = Depends(get_db),
):
    customers = await customer_repository.list_for_tenant(
        session=db,
        tenant_id=tenant.id,
    )

    return customers

@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    customer = Customer(
        tenant_id=tenant.id,
        name=payload.name,
        phone_number=payload.phone_number,
        email=payload.email,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer