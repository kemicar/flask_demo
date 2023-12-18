import os
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import uuid

def date_return(interval,validity):
    
    if interval == "day":
        # Add one day to the current UTC time
        time_later = validity + timedelta(days=1)
        
        
    elif interval == "week":
        time_later = validity + timedelta(weeks=1)

    elif interval == "month":
        time_later = validity + relativedelta(months=1)

    else:
        time_later = validity + relativedelta(year=1)

    date = time_later.strftime("%Y-%m-%d")

    return date


def find_license_id(license_key):
    response = requests.get(
        url="{}{}".format(os.environ["BASE_URL"], "/api/v1/licenses/"),
        headers={"Authorization": "Api-Key {}".format(os.environ["API_MANAGEMENT_KEY"])},
        params={"license_key":license_key}
    )
    try:
        return response.json()["results"][0]["id"]
    except Exception as e:
        print(f"An exception occurred: {e}")
        

def disable_license(license_id):
    requests.post(
        url="{}{}".format(os.environ["BASE_URL"], f"/api/v1/licenses/{license_id}/disable/"),
        headers={"Authorization": "Api-Key {}".format(os.environ["API_MANAGEMENT_KEY"])},
    )


def retrieve_license_validity(license_id):
    response = requests.get(
        url="{}{}".format(os.environ["BASE_URL"], f"/api/v1/licenses/{license_id}/"),
        headers={"Authorization": "Api-Key {}".format(os.environ["API_MANAGEMENT_KEY"])},
    )
    return response.json()["validity_period"]


def cancel_sub(license_id, interval):
    if interval == "day":
        valid_duration = "1d"

    elif interval == "week":
        valid_duration = "1w"

    elif interval == "month":
        valid_duration = "1m"

    else:
        valid_duration = "1y"

    body = {"is_trial": False, "valid_duration": valid_duration}

    requests.patch(
        url="{}{}".format(os.environ["BASE_URL"], f"/api/v1/licenses/{license_id}/"),
        json=body,
        headers={"Authorization": "Api-Key {}".format(os.environ["API_MANAGEMENT_KEY"])},
    )


def update_license_subscription(license_id, interval, validity):
    
    date = date_return(interval,validity)

    body = {"is_trial": False, "validity_period": date}

    response = requests.patch(
        url="{}{}".format(os.environ["BASE_URL"], f"/api/v1/licenses/{license_id}/"),
        json=body,
        headers={"Authorization": "Api-Key {}".format(os.environ["API_MANAGEMENT_KEY"])},
    )

    return response


def create_order(license_key, interval):
    now_utc = datetime.utcnow()

    date = date_return(interval,now_utc)
    
    body = {
        "id": str(uuid.uuid4()),
        "items": [
            {
                "product_code": os.environ["PRODUCT_SHORT_CODE"],
                "licenses": [
                    {
                        "license_type": "subscription",
                        "validity_period": date,
                        "is_trial": "false",
                        "key": license_key,
                    }
                ],
            }
        ],
    }
    response = requests.post(
        url="{}{}".format(os.environ["BASE_URL"], "/api/v1/orders/create_order/"),
        json=body,
        headers={"Authorization": "Api-Key {}".format(os.environ["API_MANAGEMENT_KEY"])},
    )
    return response


def generate_license():
    response = requests.get(
        url="{}{}".format(os.environ["BASE_URL"], "/api/v1/orders/generate_license/"),
        params={"product": os.environ["PRODUCT_SHORT_CODE"], "quantity": 1},
        headers={"Authorization": "Api-Key {}".format(os.environ["API_MANAGEMENT_KEY"])},
    )
    return response.json()[0]
