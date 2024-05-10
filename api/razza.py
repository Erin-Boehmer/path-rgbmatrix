# This API is currently quite flakey. 
# Seems to be having trouble with load balancing requests, returning frequent 503s
# See https://github.com/mrazza/path-data/issues/23
# Using only as a backup datasource should the NJPath API requests fail.

import os
from adafruit_datetime import datetime

import api.shared_config as config


# --- Adafruit time API setup ---
ADAFRUIT_IO_USERNAME = os.getenv("ADAFRUIT_IO_USERNAME")
ADAFRUIT_IO_KEY = os.getenv("ADAFRUIT_IO_KEY")
TZ = os.getenv("TIMEZONE")


def get_current_time(requests):
    '''
    Retrieves the current time from Adafruit IO's time service.

    Args:
        requests (requests.Session): A session object from the requests library.

    Returns:
        datetime.datetime: The current time retrieved from Adafruit IO.

    Raises:
        Exception: If there's an issue with the HTTP request or parsing the response.
    '''
    try:
        base_url = f"https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/integrations/time/strftime"
        query= f"?x-aio-key={ADAFRUIT_IO_KEY}&tz={TZ}"
        format = "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S"
        full_url = f"{base_url}{query}{format}"

        response = requests.get(full_url)
    except Exception as e:
        raise Exception(f"Failed to get current time from Adafruit's IO service: {e}")

    iso_string = response.text.replace(" ", "T")
    current_time = datetime.fromisoformat(iso_string)

    return current_time


def fetch_data(requests):
    '''
    Fetches real-time data from the Razza API.

    Args:
        requests (requests.Session): A session object from the requests library.

    Returns:
        list: A list containing processed real-time train arrivals from the Razza API.

    Raises:
        Exception: If there's an issue with the HTTP request or processing the response.
    '''
    current_time = get_current_time(requests)

    try:
        url = f"https://path.api.razza.dev/v1/stations/{config.RAZZA_STATION}/realtime"
        headers = {
            "Accept": "application/json; charset=UTF-8",
        }
        response = requests.get(url, headers=headers)
    except Exception as e:
        raise Exception(f"Failed to get path data from Razza API: {e}")

    if response.status_code == 200:
        json_response = response.json()
        return process_data(json_response, current_time)
    else:
        print(f"Request failed with status code {response.status_code}")
        if response.content:
            print(f"Response content: {response.content}")
        return []


def process_data(json_data, current_time):
    arrivals = []

    for arrival in json_data.get("upcomingTrains", []):
        if arrival.get("direction", "-") == config.RAZZA_DIRECTION:
            lineName = arrival.get("headsign", "-")
            lineAbbreviation = config.LINE_NAME_MAP.get(lineName, lineName)
            color = config.LINE_COLOR_MAP.get(lineName, config.DEFAULT_COLOR)
            arrivalTimeMessage = get_minutes_to_arrival(arrival.get("projectedArrival", "-"), current_time)

            arrival_details = {
                "line": lineAbbreviation,
                "color": color,
                "projectedArrival": arrivalTimeMessage,
                "lastUpdated": arrival.get("lastUpdated", "-"),
            }

            arrivals.append(arrival_details)

    return arrivals


def get_minutes_to_arrival(arrival_datetime_str, current_time):
    arrival_datetime = datetime.fromisoformat(arrival_datetime_str.replace("Z", ""))
    minutes_to_arrival = (arrival_datetime - current_time).total_seconds() // 60

    return f"{minutes_to_arrival}m"
