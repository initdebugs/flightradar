from flask import Flask, send_from_directory, jsonify, request
import requests
from flask_caching import Cache
from threading import Thread
import time
import os

app = Flask(__name__)

# Configure Flask-Caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Replace this with your API key
RAPIDAPI_KEY = 'df9adb206dmsh555d4817e595b82p1b6168jsn37ba641eff85'
RAPIDAPI_HOST = 'adsbexchange-com1.p.rapidapi.com'

def fetch_flight_data():
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
    else:
        print(f"Error fetching data: {response.status_code} - {response.text}")

    return flights

# Cache the flight data every 30 seconds
@cache.cached(timeout=30, key_prefix='all_flights')
def get_cached_flight_data():
    return fetch_flight_data()

def cache_flight_data_periodically():
    while True:
        with app.app_context():
            get_cached_flight_data()
        time.sleep(30)

@app.route('/')
def index():
    # Serve the index.html from the root folder
    return send_from_directory(os.getcwd(), 'index.html')

@app.route('/get_flights', methods=['POST'])
def get_flights():
    flights = get_cached_flight_data()

    # Get the bounding box from the client
    min_lat = float(request.form['min_lat'])
    max_lat = float(request.form['max_lat'])
    min_lon = float(request.form['min_lon'])
    max_lon = float(request.form['max_lon'])

    # Filter flights based on bounding box
    filtered_flights = [
        flight for flight in flights
        if min_lat <= flight['lat'] <= max_lat and min_lon <= flight['lon'] <= max_lon
    ]

    return jsonify(filtered_flights)

if __name__ == '__main__':
    # Start the background thread to periodically cache flight data
    cache_thread = Thread(target=cache_flight_data_periodically)
    cache_thread.daemon = True
    cache_thread.start()

    app.run(debug=True)
