"""
Stripe payment service
"""
import stripe
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.user import User


# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service for handling Stripe operations"""

    async def create_customer(
        self,
        db: AsyncSession,
        user: User,
        payment_method_id: Optional[str] = None
    ) -> str:
        """
        Create a Stripe customer for a user

        Args:
            db: Database session
            user: User object
            payment_method_id: Optional payment method to attach

        Returns:
            Stripe customer ID
        """
        if user.stripe_customer_id:
            return user.stripe_customer_id

        # Create customer in Stripe
        customer_data = {
            "email": user.email,
            "name": user.full_name or user.username,
            "metadata": {
                "user_id": str(user.id),
                "username": user.username
            }
        }

        if payment_method_id:
            customer_data["payment_method"] = payment_method_id

        customer = stripe.Customer.create(**customer_data)

        # Save customer ID to database
        user.stripe_customer_id = customer.id
        db.add(user)
        await db.commit()
        await db.refresh(user)

        return customer.id

    async def get_customer(self, customer_id: str) -> Optional[stripe.Customer]:
        """
        Get Stripe customer by ID

        Args:
            customer_id: Stripe customer ID

        Returns:
            Stripe customer object or None
        """
        try:
            return stripe.Customer.retrieve(customer_id)
        except stripe.error.StripeError:
            return None

    async def create_payment_intent(
        self,
        amount: int,
        currency: str = None,
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> stripe.PaymentIntent:
        """
        Create a payment intent

        Args:
            amount: Amount in cents (e.g., 1000 = $10.00)
            currency: Currency code (default from settings)
            customer_id: Optional Stripe customer ID
            metadata: Optional metadata dict

        Returns:
            Stripe PaymentIntent object
        """
        intent_data = {
            "amount": amount,
            "currency": currency or settings.STRIPE_CURRENCY,
            "automatic_payment_methods": {"enabled": True}
        }

        if customer_id:
            intent_data["customer"] = customer_id

        if metadata:
            intent_data["metadata"] = metadata

        return stripe.PaymentIntent.create(**intent_data)

    async def create_connect_account(
        self,
        db: AsyncSession,
        user: User,
        country: str = "US",
        account_type: str = "express"
    ) -> str:
        """
        Create a Stripe Connect account for a user

        Args:
            db: Database session
            user: User object
            country: Country code (default: US)
            account_type: Account type (express, standard, custom)

        Returns:
            Stripe Connect account ID
        """
        if user.stripe_connect_id:
            return user.stripe_connect_id

        # Create Connect account
        account = stripe.Account.create(
            type=account_type,
            country=country,
            email=user.email,
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True}
            },
            metadata={
                "user_id": str(user.id),
                "username": user.username
            }
        )

        # Save Connect account ID to database
        user.stripe_connect_id = account.id
        db.add(user)
        await db.commit()
        await db.refresh(user)

        return account.id

    async def create_account_link(
        self,
        account_id: str,
        return_url: str,
        refresh_url: str,
        link_type: str = "account_onboarding"
    ) -> stripe.AccountLink:
        """
        Create an account link for Connect onboarding

        Args:
            account_id: Stripe Connect account ID
            return_url: URL to redirect after onboarding
            refresh_url: URL to redirect if link expires
            link_type: Type of link (account_onboarding, account_update)

        Returns:
            Stripe AccountLink object
        """
        return stripe.AccountLink.create(
            account=account_id,
            return_url=return_url,
            refresh_url=refresh_url,
            type=link_type
        )

    async def get_account(self, account_id: str) -> Optional[stripe.Account]:
        """
        Get Stripe Connect account by ID

        Args:
            account_id: Stripe Connect account ID

        Returns:
            Stripe Account object or None
        """
        try:
            return stripe.Account.retrieve(account_id)
        except stripe.error.StripeError:
            return None

    async def create_transfer(
        self,
        amount: int,
        destination: str,
        currency: str = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> stripe.Transfer:
        """
        Create a transfer to a Connect account

        Args:
            amount: Amount in cents
            destination: Stripe Connect account ID
            currency: Currency code
            metadata: Optional metadata

        Returns:
            Stripe Transfer object
        """
        transfer_data = {
            "amount": amount,
            "currency": currency or settings.STRIPE_CURRENCY,
            "destination": destination
        }

        if metadata:
            transfer_data["metadata"] = metadata

        return stripe.Transfer.create(**transfer_data)

    async def attach_payment_method(
        self,
        payment_method_id: str,
        customer_id: str
    ) -> stripe.PaymentMethod:
        """
        Attach a payment method to a customer

        Args:
            payment_method_id: Stripe PaymentMethod ID
            customer_id: Stripe Customer ID

        Returns:
            Stripe PaymentMethod object
        """
        payment_method = stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id
        )

        # Set as default payment method
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id}
        )

        return payment_method

    async def list_payment_methods(
        self,
        customer_id: str,
        method_type: str = "card"
    ) -> list:
        """
        List payment methods for a customer

        Args:
            customer_id: Stripe Customer ID
            method_type: Payment method type (card, us_bank_account, etc.)

        Returns:
            List of PaymentMethod objects
        """
        payment_methods = stripe.PaymentMethod.list(
            customer=customer_id,
            type=method_type
        )
        return payment_methods.data

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> stripe.Subscription:
        """
        Create a subscription for a customer

        Args:
            customer_id: Stripe Customer ID
            price_id: Stripe Price ID
            metadata: Optional metadata

        Returns:
            Stripe Subscription object
        """
        subscription_data = {
            "customer": customer_id,
            "items": [{"price": price_id}],
            "payment_behavior": "default_incomplete",
            "payment_settings": {"save_default_payment_method": "on_subscription"},
            "expand": ["latest_invoice.payment_intent"]
        }

        if metadata:
            subscription_data["metadata"] = metadata

        return stripe.Subscription.create(**subscription_data)

    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_at_period_end: bool = True
    ) -> stripe.Subscription:
        """
        Cancel a subscription

        Args:
            subscription_id: Stripe Subscription ID
            cancel_at_period_end: If True, cancel at period end; if False, cancel immediately

        Returns:
            Stripe Subscription object
        """
        if cancel_at_period_end:
            return stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
        else:
            return stripe.Subscription.cancel(subscription_id)

    def construct_webhook_event(
        self,
        payload: bytes,
        sig_header: str
    ) -> stripe.Event:
        """
        Construct and verify a webhook event

        Args:
            payload: Raw request payload
            sig_header: Stripe signature header

        Returns:
            Stripe Event object

        Raises:
            ValueError: If webhook signature is invalid
        """
        return stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )


# Create singleton instance
stripe_service = StripeService()
