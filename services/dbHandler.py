from apiflask import APIBlueprint
from flask import request
from Database.repositories import *
from services.docs import DOCS
from services.schemas import (
    PlayerCreateRequestSchema,
    PlayerPrivilegeRequestSchema,
    PlayerPrivilegesRequestSchema,
    FavoriteServersOutputSchema,
    PlayerUuidRequestSchema,
    SettingRequestSchema,
    PlayerPrivilegesOutputSchema,
    PlayerUUIDsOutputSchema,
    UserIdRequestSchema,
    UserIdServerIdRequestSchema,
    StatusOutputSchema,
)

db_blueprint = APIBlueprint('database', __name__)

@db_blueprint.route('/user', methods=['POST'])
@db_blueprint.doc(**DOCS['create_user'])
@db_blueprint.output(StatusOutputSchema, status_code=200)
def createUser():
    request_data = request.get_json()
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = request_data.get('username')
    password = request_data.get('password')

    return {'status': UserRepository.createUser(username, password)}, 200

@db_blueprint.route('/user', methods=['DELETE'])
@db_blueprint.doc(**DOCS['remove_user'])
@db_blueprint.input(UserIdRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
def removeUser(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = request_data.get('username')
    if username is None:
        return {'error': 'bad request'}, 400

    return {'status': UserRepository.removeUser(username)}, 200

@db_blueprint.route('/favoriteServers', methods=['POST'])
@db_blueprint.doc(**DOCS['add_favorite_server'])
@db_blueprint.input(UserIdServerIdRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
def addFavoriteServer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400
    username = request_data.get('username')
    server_id = request_data.get('server_id')
    if server_id is None or username is None:
        return {'error': 'bad request'}, 400

    try:
        server_id = int(server_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': FavoriteServersRepository.addFavoriteServer(server_id, username)}, 200

@db_blueprint.route('/favoriteServers', methods=['DELETE'])
@db_blueprint.doc(**DOCS['remove_favorite_server'])
@db_blueprint.input(UserIdServerIdRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
def removeFavoriteServer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400
    username = request_data.get('username')
    server_id = request_data.get('server_id')
    if server_id is None or username is None:
        return {'error': 'bad request'}, 400
    try:
        server_id = int(server_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': FavoriteServersRepository.removeFavoriteServer(username, server_id)}, 200

@db_blueprint.route('/favoriteServers', methods=['GET'])
@db_blueprint.doc(**DOCS['get_favorite_servers'])
@db_blueprint.input(UserIdRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(FavoriteServersOutputSchema, status_code=200)
def getFavoriteServers(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400
    username = request_data.get('username')
    if username is None:
        return {'error': 'bad request'}, 400

    return {'servers': FavoriteServersRepository.getFavoriteServers(username)}, 200

@db_blueprint.route('/player', methods=['POST'])
@db_blueprint.doc(**DOCS['add_player'])
@db_blueprint.input(PlayerCreateRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
def addPlayer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = request_data.get('username')
    name = request_data.get('name')
    uuid = request_data.get('uuid')
    if username is None or name is None or uuid is None:
        return {'error': 'bad request'}, 400

    return {'status': PlayerRepository.createPlayer(username, name, uuid)}, 200

@db_blueprint.route('/player', methods=['DELETE'])
@db_blueprint.doc(**DOCS['remove_player'])
@db_blueprint.input(PlayerUuidRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
def removePlayer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = request_data.get('username')
    uuid = request_data.get('uuid')
    if username is None or uuid is None:
        return {'error': 'bad request'}, 400

    return {'status': PlayerRepository.removePlayer(username, uuid)}, 200

@db_blueprint.route('/player', methods=['GET'])
@db_blueprint.doc(**DOCS['get_all_players_uuids'])
@db_blueprint.input(UserIdRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(PlayerUUIDsOutputSchema, status_code=200)
def getAllPlayersUUIDs(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = request_data.get('username')
    if username is None:
        return {'error': 'bad request'}, 400

    return {'players': PlayerRepository.getAllPlayersUUIDs(username)}, 200

@db_blueprint.route('/playerPrivilege', methods=['POST'])
@db_blueprint.doc(**DOCS['add_player_privilege'])
@db_blueprint.input(PlayerPrivilegeRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
def addPlayerPrivilege(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = request_data.get('username')
    player_uuid = request_data.get('player_uuid')
    privilege_id = request_data.get('privilege_id')
    if username is None or player_uuid is None or privilege_id is None:
        return {'error': 'bad request'}, 400

    try:
        privilege_id = int(privilege_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': PlayersPrivilegesRepository.addPlayerPrivilege(username, player_uuid, privilege_id)}, 200

@db_blueprint.route('/playerPrivilege', methods=['DELETE'])
@db_blueprint.doc(**DOCS['delete_player_privilege'])
@db_blueprint.input(PlayerPrivilegeRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
def deletePlayerPrivilege(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = request_data.get('username')
    player_uuid = request_data.get('player_uuid')
    privilege_id = request_data.get('privilege_id')
    if username is None or player_uuid is None or privilege_id is None:
        return {'error': 'bad request'}, 400

    try:
        privilege_id = int(privilege_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': PlayersPrivilegesRepository.deletePlayerPrivilege(username, player_uuid, privilege_id)}, 200

@db_blueprint.route('/playerPrivilege', methods=['GET'])
@db_blueprint.doc(**DOCS['get_player_privileges'])
@db_blueprint.input(PlayerPrivilegesRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(PlayerPrivilegesOutputSchema, status_code=200)
def getPlayerPrivileges(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = request_data.get('username')
    player_uuid = request_data.get('player_uuid')
    if username is None or player_uuid is None:
        return {'error': 'bad request'}, 400

    return {'privileges': PlayersPrivilegesRepository.getPlayerPrivileges(username, player_uuid)}, 200

@db_blueprint.route('/setting', methods=['POST'])
@db_blueprint.doc(**DOCS['add_setting'])
@db_blueprint.input(SettingRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
def addSetting(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = request_data.get('username')
    rule = request_data.get('rule')
    approved = request_data.get('approved', False)
    if username is None or rule is None:
        return {'error': 'bad request'}, 400

    try:
        rule = int(rule)
        approved = bool(approved)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': SettingsRepository.addSetting(username, rule, approved)}, 200

@db_blueprint.route('/setting', methods=['DELETE'])
@db_blueprint.doc(**DOCS['remove_setting'])
@db_blueprint.input(UserIdRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
def removeSetting(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = request_data.get('username')
    rule = request_data.get('rule')
    if username is None or rule is None:
        return {'error': 'bad request'}, 400

    try:
        rule = int(rule)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': SettingsRepository.removeSetting(username, rule)}, 200

@db_blueprint.route('/setting', methods=['PATCH'])
@db_blueprint.doc(**DOCS['change_setting'])
@db_blueprint.input(SettingRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
def changeSetting(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = request_data.get('username')
    rule = request_data.get('rule')
    approved = request_data.get('approved', False)
    if username is None or rule is None:
        return {'error': 'bad request'}, 400

    try:
        rule = int(rule)
        approved = bool(approved)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': SettingsRepository.changeSetting(username, rule, approved)}, 200
