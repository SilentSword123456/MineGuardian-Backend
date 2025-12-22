from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'message': 'Welcome to MineGuardian API',
        'status': 'running'
    })


@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({
        'data': [],
        'count': 0
    })


@app.route('/api/data', methods=['POST'])
def create_data():
    data = request.get_json()
    return jsonify({
        'message': 'Data received',
        'data': data
    }), 201


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

