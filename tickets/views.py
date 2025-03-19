import logging
import os

from django.http import HttpResponse
from django.template import loader
from django_q.tasks import async_task

from club.exceptions import BadRequest
from notifications.email.sender import send_transactional_email

from payments.service import stripe
from payments.helpers import parse_stripe_webhook_event
from tickets.models import Ticket, TicketSale
from users.models.achievements import UserAchievement
from users.models.user import User

log = logging.getLogger()

STRIPE_CAMP_WEBHOOK_SECRET = os.getenv("STRIPE_TICKETS_WEBHOOK_SECRET")
STRIPE_API_KEY = os.getenv("STRIPE_TICKETS_API_KEY")
stripe.api_key = STRIPE_API_KEY


def stripe_ticket_sale_webhook(request):
    try:
        event = parse_stripe_webhook_event(request, STRIPE_CAMP_WEBHOOK_SECRET)
    except BadRequest as ex:
        return HttpResponse(ex.message, status=ex.code)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        customer_email = session["customer_details"]["email"].lower()

        user = User.objects.filter(email=customer_email).first()

        try:
            session_with_items = stripe.checkout.Session.retrieve(
                session_id,
                expand=["line_items", "line_items.data.price.product"]
            )

            emails_to_send = set()

            # Process each item in the purchase
            if session_with_items.line_items:
                for item in session_with_items.line_items.data:
                    stripe_product_id = item.price.product.id

                    # Find the corresponding ticket
                    ticket, _ = Ticket.objects.get_or_create(
                        stripe_product_id=stripe_product_id,
                        defaults=dict(
                            code=stripe_product_id,
                            name=item.price.product.name,
                            limit_quantity=-1  # No limit by default
                        )
                    )

                    # Create ticket sales (one for each quantity)
                    for _ in range(item.quantity):
                        TicketSale.objects.create(
                            user=user,
                            customer_email=customer_email,
                            stripe_payment_id=session.get("payment_intent"),
                            ticket=ticket,
                            metadata={
                                "price_paid": item.price.unit_amount / 100,  # Convert from cents
                                "currency": item.price.currency,
                                "purchased_at": session["created"],
                            }
                        )

                    # Check if number of sales is exceeded
                    if ticket.limit_quantity >= 0 and ticket.stripe_payment_link_id:
                        ticket_sales_count = TicketSale.objects.filter(ticket=ticket).count()
                        if ticket_sales_count >= ticket.limit_quantity:
                            deactivate_payment_link(ticket.stripe_payment_link_id)

                    # Handle achievements
                    if user and ticket.achievement:
                        UserAchievement.objects.get_or_create(
                            user=user,
                            achievement=ticket.achievement,
                        )

                    # Handle emails
                    if ticket.email_template:
                        emails_to_send.add(ticket.email_template)

            for email_template in emails_to_send:
                confirmation_template = loader.get_template(email_template)
                async_task(
                    send_transactional_email,
                    recipient=customer_email,
                    subject=f"🔥 Ждём вас на Вастрик Кэмпе 2025",
                    html=confirmation_template.render({"user": user})
                )

            return HttpResponse("[ok]", status=200)

        except stripe.error.StripeError as e:
            log.error(f"Stripe API error: {str(e)}")
            return HttpResponse(f"Stripe API error: {str(e)}", status=500)

    return HttpResponse("[unknown event]", status=400)


def deactivate_payment_link(payment_link_id):
    try:
        # Call Stripe API to deactivate the payment link
        stripe.payment_link.modify(
            payment_link_id,
            active=False
        )
        log.info(f"Payment link {payment_link_id} has been deactivated due to sales limit")
        return True
    except stripe.error.StripeError as e:
        log.error(f"Failed to deactivate payment link {payment_link_id}: {str(e)}")
        return False
