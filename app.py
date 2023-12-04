from flask import Flask, jsonify, request, render_template
import os
import json
import stripe
from flask import Response
from licensespring import *
from cache_funs import *

stripe.api_key = os.environ["STRIPE_PRIVATE_KEY"]

app = Flask(__name__)


@app.route("/")
def home():
    link = stripe.PaymentLink.create(
        line_items=[{"price": os.environ["STRIPE_PRODUCT"], "quantity": 1}],
    )

    return render_template("home.html", link=link)


@app.route("/webhooks", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    event = None
    data = json.loads(payload)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, os.environ["STRIPE_SECRET"])

    except ValueError as e:
        # Invalid payload
        print(f"Error parsing payload: {str(e)}")
        return Response(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Error verifying webhook signature: {str(e)}")
        return Response(status=400)

    # Handle the event
    if event["type"] == "customer.subscription.created":
        event_id = data.get("id", None)
        interval = (
            data.get("data", {})
            .get("object", {})
            .get("items", {})
            .get("data", [{}])[0]
            .get("plan", {})
            .get("interval", None)
        )
        subscription_id = data.get("data", {}).get("object", {}).get("id", None)
        list_events = read("cache.json")
        list_events = check_and_trim(list_events)

        if event_id not in list_events:
            list_events.append(event_id)
            license_key = generate_license()

            stripe.Subscription.modify(
                subscription_id,
                metadata={"license_key": license_key},
            )

            create_order(license_key, interval)
            
           
            write("cache.json", list_events)

    elif event["type"] == "invoice.paid":
        event_id = data.get("id", None)
        license_key = (
            data.get("data", {}).get("object", {}).get("metadata", {}).get("license_key", None)
        )
        line_items = data.get("data", {}).get("object", {}).get("lines", {}).get("data", [])
        interval = line_items[0].get("plan", {}).get("interval") if line_items else None
        list_events = read("cache.json")
        list_events = check_and_trim(list_events)

        if event_id not in list_events:
            list_events.append(event_id)
            if license_key != None:
                license_key = data["data"]["object"]["metadata"]["license_key"]
                interval = data["data"]["object"]["lines"]["data"][0]["plan"]["interval"]

                license_id = find_license_id(license_key)
                validity = retrieve_license_validity(license_id=license_id)
                update_license_subscription(
                    license_id=license_id, interval=interval, validity=validity
                )

    elif event["type"] == "customer.subscription.deleted":
        event_id = data.get("id", None)

        license_key = (
            data.get("data", {}).get("object", {}).get("metadata", {}).get("license_key", None)
        )

        interval = data.get("data", {}).get("object", {}).get("plan", {}).get("interval", None)
        list_events = read("cache.json")
        list_events = check_and_trim(list_events)

        if event_id not in list_events and license_key != None:
            list_events.append(event_id)

            license_id = find_license_id(license_key)
            cancel_sub(license_id=license_id, interval=interval)
            disable_license(license_id=license_id)
            list_events.append(event_id)
            write("cache.json", list_events)

    else:
        # Unexpected event type
        print("Unhandled event type {}".format(event["type"]))

    return jsonify(success=True)


if __name__ == "__main__":
    app.run()
