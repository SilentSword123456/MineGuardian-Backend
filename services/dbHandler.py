from apiflask import APIBlueprint
from flask import request
from Database.repositories import *

db_blueprint = APIBlueprint('database', __name__)

@db_blueprint.route('/user', methods=['POST'])
def createUser():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    return {'status': UserRepository.createUser()}, 200

@db_blueprint.route('/user', methods=['DELETE'])
def removeUser():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    user_id = request_data.get('user_id')
    if user_id is None:
        return {'error': 'bad request'}, 400

    return {'status': UserRepository.removeUser(user_id)}, 200

@db_blueprint.route('/favoriteServers', methods=['POST'])
def addFavoriteServer():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400
    user_id = request_data.get('user_id')
    server_id = request_data.get('server_id')
    if server_id is None or user_id is None:
        return {'error': 'bad request'}, 400

    try:
        server_id = int(server_id)
        user_id = int(user_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': FavoriteServersRepository.addFavoriteServer(server_id, user_id)}, 200

@db_blueprint.route('/favoriteServers', methods=['DELETE'])
def removeFavoriteServer():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400
    user_id = request_data.get('user_id')
    server_id = request_data.get('server_id')
    if server_id is None or user_id is None:
        return {'error': 'bad request'}, 400
    try:
        server_id = int(server_id)
        user_id = int(user_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': FavoriteServersRepository.removeFavoriteServer(user_id, server_id)}, 200

@db_blueprint.route('/favoriteServers', methods=['GET'])
def getFavoriteServers():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400
    user_id = request_data.get('user_id')
    if user_id is None:
        return {'error': 'bad request'}, 400

    return {'servers': FavoriteServersRepository.getFavoriteServers(user_id)}, 200




