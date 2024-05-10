import api.shared_config as config


def fetch_data(requests):
    '''
    Fetches real-time data from the NJPath API.

    Args:
        requests (requests.Session): A session object from the requests library.

    Returns:
        list: A list containing processed real-time train arrivals from the Razza API.

    Raises:
        Exception: If there's an issue with the HTTP request or processing the response.
    '''

    try:
        url = "https://www.panynj.gov/bin/portauthority/ridepath.json"
        headers = {
            "Accept": "application/json; charset=UTF-8",
        }

        response =  requests.get(url, headers=headers)
    except Exception as e:
        raise Exception(f"Failed to get path data from NJPath API: {e}")

    if response.status_code == 200:
        json_response = response.json()
        return process_data(json_response)
    else:
        print(f"Request failed with status code {response.status_code}")
        if response.content:
            print(f"Response content: {response.content}")
        return []

def process_data(json_data):
    arrivals = []

    for result in json_data.get("results", []):
        if result.get("consideredStation", "-") == config.NJPATH_STATION:
            for destination in result.get("destinations", []):
                if destination.get("label", "-") == config.NJPATH_DIRECTION:
                    for arrival in destination.get("messages", []):
                        lineName = arrival.get("headSign", "-")
                        lineAbbreviation = config.LINE_NAME_MAP.get(lineName, lineName)
                        color = config.LINE_COLOR_MAP.get(lineName, config.DEFAULT_COLOR)
                        arrivalTimeMessage = arrival.get("arrivalTimeMessage", "-").replace(" min", "m")

                        arrival_details = {
                            "line": lineAbbreviation,
                            "color": color,
                            "projectedArrival": arrivalTimeMessage,
                            "lastUpdated": arrival.get("lastUpdated", "-"),
                        }

                        arrivals.append(arrival_details)
    return arrivals
