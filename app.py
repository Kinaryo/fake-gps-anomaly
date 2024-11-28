import math
import datetime
from flask import Flask, render_template, request, jsonify
import csv
import os

app = Flask(__name__)

DATA_FILE = 'data/data.csv'
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# Variabel global untuk menyimpan data sebelumnya
last_data = {
    'latitude': None,
    'longitude': None,
    'timestamp': None
}

# Fungsi untuk menghitung jarak menggunakan Haversine
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius bumi dalam km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c  # Hasil dalam km

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_data():
    global last_data

    data = request.json
    current_timestamp = datetime.datetime.fromisoformat(data['timestamp'].replace("Z", "+00:00"))
    current_lat = data['latitude']
    current_lon = data['longitude']

    # Hitung delta time
    delta_time = None
    distance = None
    speed = None
    anomaly = False  # Default tidak anomali

    if last_data['timestamp']:
        # Hitung delta time dalam detik
        delta_time = (current_timestamp - last_data['timestamp']).total_seconds()

        # Hitung jarak (dalam km)
        distance = haversine(
            last_data['latitude'], last_data['longitude'],
            current_lat, current_lon
        )

        # Hitung kecepatan (km/jam)
        if delta_time > 0:
            speed = (distance / (delta_time / 3600))  # km/h

        # Deteksi anomali
        if speed and speed > 1000:  # Kecepatan > 1000 km/jam
            anomaly = True
        elif distance and distance > 1000 and delta_time < 3600:  # Jarak sangat jauh dalam waktu singkat
            anomaly = True

    # Simpan data baru ke CSV
    with open(DATA_FILE, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if csvfile.tell() == 0:
            writer.writerow(['latitude', 'longitude', 'accuracy', 'timestamp', 'delta_time', 'distance', 'speed', 'ip', 'label', 'anomaly'])
        writer.writerow([
            current_lat, current_lon, data['accuracy'], data['timestamp'], 
            delta_time, distance, speed, data['ip'], data['label'], anomaly
        ])

    # Update last_data
    last_data['latitude'] = current_lat
    last_data['longitude'] = current_lon
    last_data['timestamp'] = current_timestamp

    # Return hasil deteksi
    return jsonify({'status': 'success', 'message': 'Data saved successfully!', 'anomaly': anomaly})

@app.route('/data', methods=['GET'])
def get_data():
    """Endpoint untuk membaca data dari CSV dan mengembalikannya dalam format JSON sesuai urutan header."""
    data_list = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Menjamin urutan data sesuai dengan header
                data_list.append({
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'accuracy': row['accuracy'],
                    'timestamp': row['timestamp'],
                    'delta_time': row['delta_time'],
                    'distance': row['distance'],
                    'speed': row['speed'],
                    'ip': row['ip'],
                    'label': row['label'],
                    'anomaly': row['anomaly']
                })
    return jsonify(data_list)

if __name__ == '__main__':
    app.run(debug=True)
