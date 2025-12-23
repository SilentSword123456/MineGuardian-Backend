from flask import Flask, jsonify
import os
from flask_cors import CORS

DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        'status': 'API is running'
    })


@app.route('/servers', methods=['GET'])
def list_servers():
    servers = []
    i = 1
    for name in os.listdir(os.path.join(DIR, "servers")):
        servers.append({
            'name': name,
            'id': i
        })
        i += 1
    return jsonify({
        'servers': servers
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

