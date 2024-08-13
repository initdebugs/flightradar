from flask import Flask, send_from_directory, jsonify, request
import requests
from flask_caching import Cache
from threading import Thread, Event
import time
import os
import logging

app = Flask(__name__, static_folder='static')

# Configure Flask-Caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Configure logging
logging.basicConfig(level=logging.INFO)

# Replace this with your API key
RAPIDAPI_KEY = 'df9adb206dmsh555d4817e595b82p1b6168jsn37ba641eff85'
RAPIDAPI_HOST = 'adsbexchange-com1.p.rapidapi.com'

# Global variable to store the latest flight data
latest_flight_data = []
stop_event = Event()

def fetch_flight_data():
    logging.info("Fetching flight data from API...")
    url = f"https://{RAPIDAPI_HOST}/v2/lat/0/lon/0/dist/5000/"
    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    response = requests.get(url, headers=headers)
    flights = []

    if response.status_code == 200:
        flight_data = response.json()
        if 'ac' in flight_data:
            flights = [
                {
                    "lat": flight["lat"],
                    "lon": flight["lon"],
                    "icao": flight["hex"],
                    "callsign": flight.get("flight", "N/A"),
                    "track": flight.get("track", 0),
                    "altitude": flight.get("alt_baro", 0),  # Altitude in feet
                    "speed": flight.get("gs", 0)  # Ground speed in knots
                }
                for flight in flight_data['ac']
                if flight.get("lat") and flight.get("lon")
            ]
        logging.info(f"Fetched {len(flights)} flights.")
    else:
        logging.error(f"Error fetching data: {response.status_code} - {response.text}")

    return flights

def cache_flight_data_periodically():
    global latest_flight_data
    while True:
        with app.app_context():
            if stop_event.is_set():
                logging.info("Stopping data fetch thread.")
                break
            latest_flight_data = fetch_flight_data()
            logging.info("Cache updated.")
        time.sleep(30)

@app.before_first_request
def start_fetching_thread():
    logging.info("Starting the data fetching thread.")
    stop_event.clear()
    fetch_thread = Thread(target=cache_flight_data_periodically)
    fetch_thread.daemon = True
    fetch_thread.start()

@app.route('/')
def index():
    # Serve the index.html from the root folder
    return send_from_directory(os.getcwd(), 'index.html')

@app.route('/get_flights', methods=['POST'])
def get_flights():
    global latest_flight_data

    logging.info("Client requested flight data.")

    # Get the bounding box from the client
    min_lat = float(request.form['min_lat'])
    max_lat = float(request.form['max_lat'])
    min_lon = float(request.form['min_lon'])
    max_lon = float(request.form['max_lon'])

    # Filter flights based on bounding box
    filtered_flights = [
        flight for flight in latest_flight_data
        if min_lat <= flight['lat'] <= max_lat and min_lon <= flight['lon'] <= max_lon
    ]

    logging.info(f"Returning {len(filtered_flights)} filtered flights to client.")
    return jsonify(filtered_flights)

if __name__ == '__main__':
    app.run(debug=True)
