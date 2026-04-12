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

@db_blueprint.route('/player', methods=['POST'])
def addPlayer():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    user_id = request_data.get('user_id')
    name = request_data.get('name')
    uuid = request_data.get('uuid')
    if user_id is None or name is None or uuid is None:
        return {'error': 'bad request'}, 400

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': PlayerRepository.createPlayer(user_id, name, uuid)}, 200

@db_blueprint.route('/player', methods=['DELETE'])
def removePlayer():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    user_id = request_data.get('user_id')
    uuid = request_data.get('uuid')
    if user_id is None or uuid is None:
        return {'error': 'bad request'}, 400

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': PlayerRepository.removePlayer(user_id, uuid)}, 200

@db_blueprint.route('/player', methods=['GET'])
def getAllPlayersUUIDs():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    user_id = request_data.get('user_id')
    if user_id is None:
        return {'error': 'bad request'}, 400

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'players': PlayerRepository.getAllPlayersUUIDs(user_id)}, 200

@db_blueprint.route('/playerPrivilege', methods=['POST'])
def addPlayerPrivilege():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    player_id = request_data.get('player_id')
    privilege_id = request_data.get('privilege_id')
    if player_id is None or privilege_id is None:
        return {'error': 'bad request'}, 400

    try:
        player_id = int(player_id)
        privilege_id = int(privilege_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': PlayersPrivilegesRepository.addPlayerPrivilege(player_id, privilege_id)}, 200

@db_blueprint.route('/playerPrivilege', methods=['DELETE'])
def deletePlayerPrivilege():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    player_id = request_data.get('player_id')
    privilege_id = request_data.get('privilege_id')
    if player_id is None or privilege_id is None:
        return {'error': 'bad request'}, 400

    try:
        player_id = int(player_id)
        privilege_id = int(privilege_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': PlayersPrivilegesRepository.deletePlayerPrivilege(player_id, privilege_id)}, 200

@db_blueprint.route('/playerPrivilege', methods=['GET'])
def getPlayerPrivileges():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    user_id = request_data.get('user_id')
    player_uuid = request_data.get('player_uuid')
    if user_id is None or player_uuid is None:
        return {'error': 'bad request'}, 400

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'privileges': PlayersPrivilegesRepository.getPlayerPrivileges(user_id, player_uuid)}, 200

@db_blueprint.route('/setting', methods=['POST'])
def addSetting():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    user_id = request_data.get('user_id')
    rule = request_data.get('rule')
    approved = request_data.get('approved', False)
    if user_id is None or rule is None:
        return {'error': 'bad request'}, 400

    try:
        user_id = int(user_id)
        rule = int(rule)
        approved = bool(approved)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': SettingsRepository.addSetting(user_id, rule, approved)}, 200

@db_blueprint.route('/setting', methods=['DELETE'])
def removeSetting():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    user_id = request_data.get('user_id')
    rule = request_data.get('rule')
    if user_id is None or rule is None:
        return {'error': 'bad request'}, 400

    try:
        user_id = int(user_id)
        rule = int(rule)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': SettingsRepository.removeSetting(user_id, rule)}, 200

@db_blueprint.route('/setting', methods=['PATCH'])
def changeSetting():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    user_id = request_data.get('user_id')
    rule = request_data.get('rule')
    approved = request_data.get('approved', False)
    if user_id is None or rule is None:
        return {'error': 'bad request'}, 400

    try:
        user_id = int(user_id)
        rule = int(rule)
        approved = bool(approved)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': SettingsRepository.changeSetting(user_id, rule, approved)}, 200
