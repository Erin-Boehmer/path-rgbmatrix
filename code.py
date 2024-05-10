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
from displayio import Group

import api.njpath as njpath
import api.razza as razza


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

# --- Matrix setup ---
display_group = Group()

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

# --- Networking setup ---
context = ssl.create_default_context()
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, context)


def fetch_data():

    data = None

    try:
        data = njpath.fetch_data(requests)
        print(f"Data retrieved from NJPath API: {data}")
    except:
        data = razza.fetch_data(requests)
        print(f"Data retrieved from Razza API: {data}")

    return data


def create_line_name_labels(data, y_positions):
    line_name_labels = []

    for i, arrival in enumerate(data):
        y_position = y_positions[i]

        text_label = adafruit_display_text.label.Label(
                FONT, color=arrival["color"], x=3, y=y_position, text=arrival["line"]
            )
        line_name_labels.append(text_label)

    return line_name_labels

def create_arrival_time_labels(data, y_positions):
    arrival_time_labels = []

    for i, arrival in enumerate(data):
        y_position = y_positions[i]

        text_label = adafruit_display_text.label.Label(
            FONT, color=arrival["color"], x=44, y=y_position, text=arrival["projectedArrival"]
        )
        arrival_time_labels.append(text_label)

    return arrival_time_labels

def update_display(path_train_data, display_group):
    # Clear previously displayed arrival information
    while len(display_group):
        display_group.pop()

    # Calculate the y position for each of 2 (static) NYC bound arrivals
    y_positions = [
        GAP_BETWEEN_ARRIVALS + DISPLAY_HEIGHT // 2 * i
        for i in range(2)
    ]

    line_name_labels = create_line_name_labels(path_train_data, y_positions)
    arrival_time_labels = create_arrival_time_labels(path_train_data, y_positions)

    for l in line_name_labels:
        display_group.append(l)

    for a in arrival_time_labels:
        display_group.append(a)

    display.root_group = display_group

    return line_name_labels

def display_no_arrivals():
    # Clear previously displayed arrival information
    while len(display_group):
        display_group.pop()

    # Create a label for "Looking for arrivals..."
    checking_label = adafruit_display_text.label.Label(
        FONT, color=0xc7c7c7, text="Waiting on", x=0, y=6
    )
    api_label = adafruit_display_text.label.Label(
        FONT, color=0xc7c7c7, text="PATH api", x=0, y=20
    )

    display_group.append(checking_label)
    display_group.append(api_label)

    # Update the display with the new group
    display.root_group = display_group


display_no_arrivals()

path_train_data = fetch_data()

if path_train_data:
    update_display(
        path_train_data, display_group
    )

last_network_call_time = time.monotonic()

while True:
    # Refresh the display
    # display.refresh(minimum_frames_per_second=0)
    current_time = time.monotonic()

    # Check if NETWORK_CALL_INTERVAL seconds have passed
    if (current_time - last_network_call_time) >= NETWORK_CALL_INTERVAL:
        print("Fetching new path train data...")
        path_train_data = fetch_data()

        if path_train_data:
            # If PATH train arrival data is found, update the display with it
            new_text_labels = update_display(path_train_data, display_group)

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
