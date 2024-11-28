import math
import datetime
from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# MongoDB Connection
app.config["MONGO_URI"] = "mongodb+srv://kinaryo733huda:b6D1Ue8JQ8JmeRGt@cluster0.k0ezp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo = PyMongo(app)

# Fungsi untuk menghitung jarak menggunakan Haversine
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# Fungsi untuk mendapatkan ID berikutnya
def get_next_id():
    last_data = mongo.db.data.find_one(sort=[("id", -1)])
    return last_data['id'] + 1 if last_data else 1

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_data():
    data = request.json
    try:
        current_timestamp = datetime.datetime.fromisoformat(data['timestamp'].replace("Z", "+00:00"))
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid timestamp format'}), 400

    current_lat, current_lon, accuracy = data['latitude'], data['longitude'], data['accuracy']
    delta_time, distance, speed, anomaly = None, 0, None, False
    last_data = get_last_data()

    if last_data:
        delta_time = (current_timestamp - last_data['timestamp']).total_seconds()
        distance = haversine(last_data['latitude'], last_data['longitude'], current_lat, current_lon)
        if delta_time > 0:
            speed = (distance / (delta_time / 3600))
        if speed and speed > 1000 or (distance > 1000 and delta_time < 3600):
            anomaly = True

    mongo.db.data.insert_one({
        "id": get_next_id(),
        "latitude": current_lat,
        "longitude": current_lon,
        "accuracy": accuracy,
        "timestamp": current_timestamp,
        "delta_time": delta_time,
        "distance": distance,
        "speed": speed,
        "ip": data['ip'],
        "label": data['label'],
        "anomaly": anomaly,
        "from_to": f"From ({last_data['latitude']}, {last_data['longitude']}) to ({current_lat}, {current_lon})" if last_data else "N/A"
    })

    return jsonify({'status': 'success', 'message': 'Data saved successfully!', 'anomaly': anomaly, 'distance': distance})

def get_last_data():
    last_data = mongo.db.data.find_one(sort=[("timestamp", -1)])
    if last_data:
        return {
            'latitude': last_data['latitude'],
            'longitude': last_data['longitude'],
            'timestamp': last_data['timestamp']
        }
    return None

@app.route('/data', methods=['GET'])
def get_data():
    order = request.args.get('order', 'desc')
    cursor = mongo.db.data.find().sort("timestamp", -1 if order == 'desc' else 1)
    return jsonify([{
        'id': row['id'],
        'latitude': row['latitude'],
        'longitude': row['longitude'],
        'accuracy': row['accuracy'],
        'timestamp': row['timestamp'],
        'delta_time': row.get('delta_time'),
        'distance': row.get('distance'),
        'speed': row.get('speed'),
        'ip': row.get('ip'),
        'label': row.get('label'),
        'anomaly': row.get('anomaly'),
        'from_to': row.get('from_to')
    } for row in cursor])

@app.route('/delete/<int:id>', methods=['DELETE'])
def delete_data(id):
    mongo.db.data.delete_one({"id": id})
    return jsonify({'status': 'success', 'message': f'Data with ID {id} has been deleted.'})

@app.route('/delete_all', methods=['DELETE'])
def delete_all_data():
    mongo.db.data.delete_many({})
    return jsonify({'status': 'success', 'message': 'All data has been deleted.'})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
