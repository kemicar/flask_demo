from flask import Flask, jsonify, request, render_template,Response
import os,json,stripe
from licensespring import *
from helpers import read,write,check_and_trim

stripe.api_key = os.environ["STRIPE_PRIVATE_KEY"]


app = Flask(__name__)

list_events = read("cache.json")


@app.route("/")
def home():
    """Defines the home page route. When visited, it renders payment link"""
    
    return render_template("home.html", link = os.environ["PAYMENT_LINK"]
)


@app.route("/webhooks", methods=["POST"])
def webhook():
    """Handles incoming webhooks from Stripe."""

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    event = None
    

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, os.environ["STRIPE_SECRET"])
        
        
        check_and_trim(list_events)

        event_id = event.get("id", None)

        if event_id in list_events:
            return Response(status=400)

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

        interval=event["data"]["object"]["plan"]["interval"]
        subscription_id = event.get("data", {}).get("object", {}).get("id", None)
    
        license_key = generate_license()

        stripe.Subscription.modify(subscription_id,metadata={"license_key": license_key},)

        create_order(license_key, interval)
            

    elif event["type"] == "invoice.paid":
        
        license_key = (
            event.get("data", {}).get("object", {}).get("metadata", {}).get("license_key", None)
        )
        line_items = event.get("data", {}).get("object", {}).get("lines", {}).get("data", [])
        interval = line_items[0].get("plan", {}).get("interval") if line_items else None
        
     

        if license_key != None:
            

            license_id = find_license_id(license_key)
            validity = retrieve_license_validity(license_id=license_id)
            update_license_subscription(license_id=license_id, interval=interval, validity=validity)

    elif event["type"] == "customer.subscription.deleted":

        license_key = (
            event.get("data", {}).get("object", {}).get("metadata", {}).get("license_key", None)
        )

        interval = event.get("data", {}).get("object", {}).get("plan", {}).get("interval", None)
        

        if  license_key != None:
    
            license_id = find_license_id(license_key)
            cancel_sub(license_id=license_id, interval=interval)
            disable_license(license_id=license_id)
            

    else:
        # Unexpected event type
        print("Unhandled event type {}".format(event["type"]))
    
    list_events.append(event_id)
    write("cache.json", list_events)

    return jsonify(success=True)


if __name__ == "__main__":
    app.run()
