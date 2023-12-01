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
    return render_template("home.html")

@app.route("/create-payment-link")
def create_payment_link():
    try:
        link = stripe.PaymentLink.create(
            line_items=[{"price": os.environ["STRIPE_PRODUCT"], "quantity": 1}],
        )
        return jsonify({"url": link.url})
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/webhooks", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    event = None
    data = json.loads(payload)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ["STRIPE_SECRET"]
        )
    except ValueError as e:
        # Invalid payload
        print(f"Error parsing payload: {str(e)}")
        return Response(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Error verifying webhook signature: {str(e)}")
        return Response(status=400)

    # Handle the event

    if event["type"] == "invoice.paid":
        sub_id = data.get("data", {}).get("object", {}).get("subscription")
        
        sub_ids = read_write("cache.json", read=True, list_=None)

        sub_ids = check_and_trim(sub_ids)

        if not check_if_in_list(sub_ids, sub_id) and event['data']['object']["billing_reason"]=="subscription_create":
            # checking if sub_id in cache_sub_id
            license_key = generate_license()

            order_num = os.environ["STRIPE_PRIVATE_KEY"] + str(license_key)

            stripe.Subscription.modify(
                sub_id,
                metadata={"license_key": license_key},
            )
            sub_retrieve = stripe.Subscription.retrieve(sub_id)
            interval = sub_retrieve["items"]["data"][0]["price"]["recurring"]["interval"]
            # create order
            response = create_order(license_key, order_num, interval)
            license_id = response.json()["order_items"][0]["licenses"][0]["id"]

            sub_ids.append(
                {
                    "sub_id": sub_id,
                    "license_key": license_key,
                    "interval": interval,
                    "license_id": license_id,
                }
            )
            read_write("cache.json", read=False, list_=sub_ids)
        elif check_if_in_list(sub_ids, sub_id):
            sub_id = stripe.Subscription.retrieve(sub_id)
            try:
                index_ = check_where_in_list(sub_ids, sub_id)

                if index_ != -1:
                    validity = retrieve_license_validity(sub_ids[index_]["license_id"])
                    update_license_subscription(
                        sub_ids[index_]["license_id"],
                        sub_ids[index_]["interval"],
                        validity,
                    )

            except Exception as e:
                print("An error occurred: ", e)

            # retrieve license id + validity period

    elif event["type"] == "customer.subscription.deleted":
        sub_id = event["data"]["object"]["id"]

        sub_ids = read_write("cache.json", read=True, list_=None)

        index_ = check_where_in_list(sub_ids, sub_id)

        if index_ != -1:
            cancel_sub(
                license_id=sub_ids[index_]["license_id"],
                interval=sub_ids[index_]["interval"],
            )
            disable_license(license_id=sub_ids[index_]["license_id"])
            sub_ids.pop(index_)
            sub_ids = read_write("cache.json", read=False, list_=sub_ids)

    else:
        # Unexpected event type
        print("Unhandled event type {}".format(event["type"]))

    return jsonify(success=True)


if __name__ == "__main__":
    app.run()
