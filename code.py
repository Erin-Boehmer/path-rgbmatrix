import os
import ssl
import time
import board
import wifi
import terminalio
import socketpool
import adafruit_requests
import displayio
import rgbmatrix
import framebufferio
import adafruit_display_text.label
from adafruit_datetime import datetime
from displayio import Group


# Release any existing displays
displayio.release_displays()

# --- Matrix Properties ---
DISPLAY_WIDTH = 64
DISPLAY_HEIGHT = 32
BIT_DEPTH = 2

# 30 seconds
NETWORK_CALL_INTERVAL = 60

# --- Text Properties ---
FONT = terminalio.FONT
GAP_BETWEEN_ARRIVALS = 6
LINE_NAME_MAP = {
    "World Trade Center": "WTC",
    "33rd Street": "33rd"
}
LINE_COLOR_MAP = {
    "World Trade Center": 0xD93A30,
    "33rd Street": 0xFF9900
}

# Initialize the main display group
line_name_group = Group()

# Initialize the arrival time group (this remains static on the display)
arrival_time_group = Group()

# --- Matrix setup ---

displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=DISPLAY_WIDTH,
    height=DISPLAY_HEIGHT,
    bit_depth=BIT_DEPTH,
    rgb_pins=[
        board.MTX_R1,
        board.MTX_G1,
        board.MTX_B1,
        board.MTX_R2,
        board.MTX_G2,
        board.MTX_B2,
    ],
    addr_pins=[
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD,
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
    tile=1,
    serpentine=True,
    doublebuffer=True,
)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

# --- Wi-Fi setup ---

# Wi-Fi debug
# for network in wifi.radio.start_scanning_networks():
#     print(network, network.ssid, network.channel)
# wifi.radio.stop_scanning_networks()

print(f"Connecting to the wifi {os.getenv('WIFI_SSID')}...")
wifi.radio.connect(
    os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD")
)
print(f"Connected to {os.getenv('WIFI_SSID')}")

# --- Adafruit time API setup ---
ADAFRUIT_IO_USERNAME = os.getenv("ADAFRUIT_IO_USERNAME")
ADAFRUIT_IO_KEY = os.getenv("ADAFRUIT_IO_KEY")
TZ = os.getenv("TIMEZONE")

# --- Networking setup ---
context = ssl.create_default_context()
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, context)


def get_current_time():
    base_url = f"https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/integrations/time/strftime"
    query= f"?x-aio-key={ADAFRUIT_IO_KEY}&tz={TZ}"
    format = "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S"

    full_url = f"{base_url}{query}{format}"
    response = requests.get(full_url)
    iso_string = response.text.replace(" ", "T")
    current_time = datetime.fromisoformat(iso_string)

    return current_time

def fetch_path_train_data():
    print("Running fetch_path_train_data")

    url = "https://path.api.razza.dev/v1/stations/grove_street/realtime"

    headers = {
        "Accept": "application/json; charset=UTF-8",
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        json_response = response.json()  # Parse JSON only once
        return process_path_train_data(json_response)  # Process flights and return
    else:
        print(f"Request failed with status code {response.status_code}")
        if response.content:
            print(f"Response content: {response.content}")
        return []


def process_path_train_data(json_data):
    # Initialize an empty list to hold processed flight data
    ny_bound_train_arrivals = []

    for arrival in json_data.get("upcomingTrains", []):
        # Use 'get' with default values to avoid KeyError
        arrival_details = {
            "lineName": arrival.get("lineName", "-"),
            "direction": arrival.get("direction", "-"),
            "projectedArrival": arrival.get("projectedArrival", "-").replace("Z", ""),
            "lastUpdated": arrival.get("lastUpdated", "-"),
            "status": arrival.get("status", "-"),
        }
        # Only add train if NY bound and not '-'
        if arrival_details["direction"] == "TO_NY":
            ny_bound_train_arrivals.append(arrival_details)

    return ny_bound_train_arrivals


def create_line_name_labels(path_train_data, y_positions):
    line_name_labels = []

    for i, arrival in enumerate(path_train_data):
        y_position = y_positions[i]

        lineName = arrival.get("lineName", "-")
        status = arrival.get("status", "-")
        color = LINE_COLOR_MAP.get(lineName, 0xc2c2c2)

        # Shorten line names for display
        lineName = LINE_NAME_MAP.get(lineName, lineName)

        # Only include the status if not ON_TIME or null
        if status in ["ON_TIME", "-"]:
            status = ""
        else:
            status = f" ({status})"

        display_text = f"{lineName}{status}"
        text_label = adafruit_display_text.label.Label(
                FONT, color=color, x=3, y=y_position, text=display_text
            )
        line_name_labels.append(text_label)

    return line_name_labels

def create_arrival_time_labels(path_train_data, y_positions):
    arrival_time_labels = []

    for i, arrival in enumerate(path_train_data):
        y_position = y_positions[i]


        arrival_time = arrival.get("projectedArrival", "-")
        lineName = arrival.get("lineName", "-")
        color = LINE_COLOR_MAP.get(lineName, 0xc2c2c2)

        current_time = get_current_time()
        minutes_to_arrival = "-"

        if arrival_time != "-":
            arrival_time = datetime.fromisoformat(arrival_time)

            minutes_to_arrival = (arrival_time - current_time).total_seconds() // 60

        text_label = adafruit_display_text.label.Label(
            FONT, color=color, x=44, y=y_position, text=f"{minutes_to_arrival}m"
        )
        arrival_time_labels.append(text_label)

    return arrival_time_labels

def update_display(path_train_data, line_name_group, arrival_time_group):
    # Clear previously displayed line names
    while len(line_name_group):
        line_name_group.pop()

    # Clear previously displayed arrival times
    while len(arrival_time_group):
        arrival_time_group.pop()
    # Calculate the y position for each of 2 (static) NYC bound arrivals
    y_positions = [
        GAP_BETWEEN_ARRIVALS + DISPLAY_HEIGHT // 2 * i
        for i in range(2)
    ]

    line_name_labels = create_line_name_labels(path_train_data, y_positions)
    arrival_time_labels = create_arrival_time_labels(path_train_data, y_positions)

    for l in line_name_labels:
        line_name_group.append(l)

    for a in arrival_time_labels:
        arrival_time_group.append(a)

    line_name_group.append(arrival_time_group)

    # Show the updated group on the display
    display.root_group = line_name_group
    return line_name_labels


def display_no_arrivals():
    # Clear the previous group content
    while len(line_name_group):
        line_name_group.pop()

    while len(arrival_time_group):
        arrival_time_group.pop()

    # Create a label for "Looking for arrivals..."
    checking_label = adafruit_display_text.label.Label(
        FONT, color=0xc7c7c7, text="Waiting on", x=0, y=6
    )
    razza_label = adafruit_display_text.label.Label(
        FONT, color=0xc7c7c7, text="PATH api", x=0, y=20
    )

    line_name_group.append(checking_label)
    line_name_group.append(razza_label)

    # Update the display with the new group
    display.root_group = line_name_group


display_no_arrivals()

path_train_data = fetch_path_train_data()

# Check if we received any flight data
if path_train_data:
    flight_data_labels = update_display(
        path_train_data, line_name_group, arrival_time_group
    )

last_network_call_time = time.monotonic()

while True:
    # Refresh the display
    # display.refresh(minimum_frames_per_second=0)
    current_time = time.monotonic()

    # Check if NETWORK_CALL_INTERVAL seconds have passed
    if (current_time - last_network_call_time) >= NETWORK_CALL_INTERVAL:
        print("Fetching new path train data...")
        path_train_data = fetch_path_train_data()

        if path_train_data:
            # If PATH train arrival data is found, update the display with it
            new_text_labels = update_display(
                path_train_data, line_name_group, arrival_time_group
            )

            # Keep API ping at 60 seconds. All is working.
            NETWORK_CALL_INTERVAL = 60
        else:
            # If no data is found, display the "Looking for arrivals..." message
            display_no_arrivals()

            # Shorten network call interval to 5 seconds since we failed to get the data
            NETWORK_CALL_INTERVAL = 5

        # Reset the last network call time
        last_network_call_time = current_time

        # Sleep for a short period to prevent maxing out your CPU
        time.sleep(1)  # Sleep for 1 second
