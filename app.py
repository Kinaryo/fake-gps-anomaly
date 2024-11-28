import math
import datetime
import csv
import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Mengaktifkan CORS

# Tentukan file data CSV
DATA_FILE = 'data/data.csv'
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

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

# Fungsi untuk mendapatkan ID berikutnya
def get_next_id():
    """Mengambil ID berikutnya untuk data baru"""
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        with open(DATA_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            if rows:
                last_row = rows[-1]
                return int(last_row['id']) + 1
    return 1  # Jika file kosong, mulai dengan ID 1

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_data():
    data = request.json
    try:
        # Pastikan format timestamp yang diterima sesuai ISO 8601
        current_timestamp = datetime.datetime.fromisoformat(data['timestamp'].replace("Z", "+00:00"))
    except ValueError as e:
        return jsonify({'status': 'error', 'message': 'Invalid timestamp format'}), 400

    current_lat = data['latitude']
    current_lon = data['longitude']
    accuracy = data['accuracy']

    # Menghitung jarak dan kecepatan
    delta_time = None
    distance = 0  # Jarak default
    speed = None
    anomaly = False  # Default tidak anomali

    # Hitung delta_time dan deteksi anomali berdasarkan data sebelumnya
    last_data = get_last_data()

    if last_data:
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
        # Menulis header hanya jika file kosong
        if csvfile.tell() == 0:
            writer.writerow(['id', 'latitude', 'longitude', 'accuracy', 'timestamp', 'delta_time', 'distance', 'speed', 'ip', 'label', 'anomaly', 'from_to'])
        from_to = f"From ({last_data['latitude']}, {last_data['longitude']}) to ({current_lat}, {current_lon})" if last_data else "N/A"
        writer.writerow([get_next_id(), current_lat, current_lon, accuracy, data['timestamp'], delta_time, distance, speed, data['ip'], data['label'], anomaly, from_to])

    return jsonify({'status': 'success', 'message': 'Data saved successfully!', 'anomaly': anomaly, 'distance': distance, 'from_to': from_to})

def get_last_data():
    """Mengambil data terakhir dari file CSV"""
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        with open(DATA_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            if rows:
                last_row = rows[-1]
                return {
                    'latitude': float(last_row['latitude']),
                    'longitude': float(last_row['longitude']),
                    'timestamp': datetime.datetime.fromisoformat(last_row['timestamp'].replace("Z", "+00:00"))
                }
    return None

@app.route('/data', methods=['GET'])
def get_data():
    """Endpoint untuk membaca data dari CSV dan mengembalikannya dalam format JSON sesuai urutan header."""
    order = request.args.get('order', 'desc')  # Default 'desc' untuk dari terbaru ke terlama
    data_list = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

            # Mengurutkan data berdasarkan timestamp
            rows.sort(key=lambda x: datetime.datetime.fromisoformat(x['timestamp'].replace("Z", "+00:00")), reverse=(order == 'desc'))

            for row in rows:
                # Menjamin urutan data sesuai dengan header
                data_list.append({
                    'id': row['id'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'accuracy': row['accuracy'],
                    'timestamp': row['timestamp'],
                    'delta_time': row['delta_time'],
                    'distance': row['distance'],
                    'speed': row['speed'],
                    'ip': row['ip'],
                    'label': row['label'],
                    'anomaly': row['anomaly'],
                    'from_to': row['from_to']
                })
    return jsonify(data_list)

@app.route('/delete/<int:id>', methods=['DELETE'])
def delete_data(id):
    """Menghapus data berdasarkan ID"""
    rows = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

        # Filter data yang bukan ID yang akan dihapus
        rows = [row for row in rows if int(row['id']) != id]

        # Simpan kembali data ke file CSV
        with open(DATA_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['id', 'latitude', 'longitude', 'accuracy', 'timestamp', 'delta_time', 'distance', 'speed', 'ip', 'label', 'anomaly', 'from_to'])
            writer.writeheader()
            writer.writerows(rows)

    return jsonify({'status': 'success', 'message': f'Data with ID {id} has been deleted.'})

@app.route('/delete_all', methods=['DELETE'])
def delete_all_data():
    """Menghapus semua data"""
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    return jsonify({'status': 'success', 'message': 'All data has been deleted.'})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
