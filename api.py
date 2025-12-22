from flask import Flask, jsonify, request
import psutil
import os

DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'API is running'
    })


@app.route('/resources', methods=['GET'])
def get_resources():
    cpuUsage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(DIR)
    return jsonify({
        'cpu': cpuUsage,
        'memory': {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'percent': memory.percent
        },
        'disk': {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent
        }
    })

@app.route('/files/<path:location>', methods=['GET'])
def list_files(location):
    target_dir = os.path.join(DIR, location)
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return jsonify({'error': 'Directory not found'}), 404

    files = os.listdir(target_dir)
    return jsonify({
        'location': location,
        'files': files
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

