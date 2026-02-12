"""
Stripe payment endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
import stripe as stripe_lib

from app.core.async_database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.db.models.user import User
from app.services.stripe_service import stripe_service
from app.core.config import settings


router = APIRouter()


# Pydantic schemas for Stripe endpoints
class CreateCustomerRequest(BaseModel):
    payment_method_id: Optional[str] = None


class CreatePaymentIntentRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in cents (e.g., 1000 = $10.00)")
    currency: Optional[str] = None
    description: Optional[str] = None


class CreateConnectAccountRequest(BaseModel):
    country: str = Field(default="US", description="Country code")
    account_type: str = Field(default="express", description="express, standard, or custom")


class CreateAccountLinkRequest(BaseModel):
    return_url: str
    refresh_url: str
    link_type: str = Field(default="account_onboarding")


class AttachPaymentMethodRequest(BaseModel):
    payment_method_id: str


class CreateSubscriptionRequest(BaseModel):
    price_id: str


class CancelSubscriptionRequest(BaseModel):
    cancel_at_period_end: bool = True


@router.post("/customers")
async def create_customer(
    request: CreateCustomerRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Stripe customer for the current user
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    try:
        customer_id = await stripe_service.create_customer(
            db=db,
            user=current_user,
            payment_method_id=request.payment_method_id
        )
        return {
            "customer_id": customer_id,
            "message": "Stripe customer created successfully"
        }
    except stripe_lib.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/customers/me")
async def get_my_customer(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's Stripe customer information
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Stripe customer found for this user"
        )

    try:
        customer = await stripe_service.get_customer(current_user.stripe_customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stripe customer not found"
            )
        return customer
    except stripe_lib.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/payment-intents")
async def create_payment_intent(
    request: CreatePaymentIntentRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a payment intent for the current user
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    # Ensure user has a Stripe customer
    if not current_user.stripe_customer_id:
        customer_id = await stripe_service.create_customer(db, current_user)
    else:
        customer_id = current_user.stripe_customer_id

    try:
        intent = await stripe_service.create_payment_intent(
            amount=request.amount,
            currency=request.currency,
            customer_id=customer_id,
            metadata={
                "user_id": str(current_user.id),
                "username": current_user.username,
                "description": request.description or ""
            }
        )
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id
        }
    except stripe_lib.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/connect/accounts")
async def create_connect_account(
    request: CreateConnectAccountRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Stripe Connect account for the current user
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    try:
        account_id = await stripe_service.create_connect_account(
            db=db,
            user=current_user,
            country=request.country,
            account_type=request.account_type
        )
        return {
            "account_id": account_id,
            "message": "Stripe Connect account created successfully"
        }
    except stripe_lib.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/connect/account-links")
async def create_account_link(
    request: CreateAccountLinkRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create an account link for Connect onboarding
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    if not current_user.stripe_connect_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Stripe Connect account found for this user"
        )

    try:
        account_link = await stripe_service.create_account_link(
            account_id=current_user.stripe_connect_id,
            return_url=request.return_url,
            refresh_url=request.refresh_url,
            link_type=request.link_type
        )
        return {
            "url": account_link.url,
            "expires_at": account_link.expires_at
        }
    except stripe_lib.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/connect/accounts/me")
async def get_my_connect_account(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's Stripe Connect account information
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    if not current_user.stripe_connect_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Stripe Connect account found for this user"
        )

    try:
        account = await stripe_service.get_account(current_user.stripe_connect_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stripe Connect account not found"
            )
        return account
    except stripe_lib.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/payment-methods/attach")
async def attach_payment_method(
    request: AttachPaymentMethodRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Attach a payment method to the current user's Stripe customer
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    # Ensure user has a Stripe customer
    if not current_user.stripe_customer_id:
        customer_id = await stripe_service.create_customer(db, current_user)
    else:
        customer_id = current_user.stripe_customer_id

    try:
        payment_method = await stripe_service.attach_payment_method(
            payment_method_id=request.payment_method_id,
            customer_id=customer_id
        )
        return {
            "payment_method_id": payment_method.id,
            "message": "Payment method attached successfully"
        }
    except stripe_lib.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/payment-methods")
async def list_payment_methods(
    current_user: User = Depends(get_current_active_user)
):
    """
    List payment methods for the current user
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    if not current_user.stripe_customer_id:
        return {"payment_methods": []}

    try:
        payment_methods = await stripe_service.list_payment_methods(
            customer_id=current_user.stripe_customer_id
        )
        return {"payment_methods": payment_methods}
    except stripe_lib.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/subscriptions")
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a subscription for the current user
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    # Ensure user has a Stripe customer
    if not current_user.stripe_customer_id:
        customer_id = await stripe_service.create_customer(db, current_user)
    else:
        customer_id = current_user.stripe_customer_id

    try:
        subscription = await stripe_service.create_subscription(
            customer_id=customer_id,
            price_id=request.price_id,
            metadata={
                "user_id": str(current_user.id),
                "username": current_user.username
            }
        )
        return subscription
    except stripe_lib.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: str,
    request: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancel a subscription
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    try:
        subscription = await stripe_service.cancel_subscription(
            subscription_id=subscription_id,
            cancel_at_period_end=request.cancel_at_period_end
        )
        return subscription
    except stripe_lib.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/webhooks")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature")
):
    """
    Handle Stripe webhooks

    Configure this URL in your Stripe Dashboard:
    https://yourdomain.com/api/v1/stripe/webhooks
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature header"
        )

    # Get raw body
    payload = await request.body()

    try:
        event = stripe_service.construct_webhook_event(payload, stripe_signature)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature"
        )

    # Handle different event types
    event_type = event['type']

    # Payment intent events
    if event_type == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        # Handle successful payment
        print(f"Payment succeeded: {payment_intent['id']}")

    elif event_type == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        # Handle failed payment
        print(f"Payment failed: {payment_intent['id']}")

    # Customer events
    elif event_type == 'customer.created':
        customer = event['data']['object']
        print(f"Customer created: {customer['id']}")

    elif event_type == 'customer.deleted':
        customer = event['data']['object']
        print(f"Customer deleted: {customer['id']}")

    # Subscription events
    elif event_type == 'customer.subscription.created':
        subscription = event['data']['object']
        print(f"Subscription created: {subscription['id']}")

    elif event_type == 'customer.subscription.updated':
        subscription = event['data']['object']
        print(f"Subscription updated: {subscription['id']}")

    elif event_type == 'customer.subscription.deleted':
        subscription = event['data']['object']
        print(f"Subscription deleted: {subscription['id']}")

    # Connect account events
    elif event_type == 'account.updated':
        account = event['data']['object']
        print(f"Connect account updated: {account['id']}")

    # Add more event handlers as needed

    return {"status": "success"}


@router.get("/config")
async def get_stripe_config(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get Stripe publishable key for client-side usage
    """
    if not settings.STRIPE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not enabled"
        )

    return {
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "currency": settings.STRIPE_CURRENCY
    }
