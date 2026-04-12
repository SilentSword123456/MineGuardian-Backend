from apiflask import APIBlueprint
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity

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
@jwt_required()
def removeUser(request_data=None):
    username = get_jwt_identity()
    if request_data is None:
        return {'error': 'bad request'}, 400

    targetUsername = request_data.get('username')
    if targetUsername is None:
        return {'error': 'bad request'}, 400

    if username != targetUsername:
        return {'error': 'forbidden'}, 403

    return {'status': UserRepository.removeUser(targetUsername)}, 200

@db_blueprint.route('/favoriteServers', methods=['POST'])
@db_blueprint.doc(**DOCS['add_favorite_server'])
@db_blueprint.input(UserIdServerIdRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def addFavoriteServer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400
    username = get_jwt_identity()
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
@jwt_required()
def removeFavoriteServer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400
    username = get_jwt_identity()
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
@get_jwt_identity()
def getFavoriteServers(request_data=None):
    username = get_jwt_identity()
    return {'servers': FavoriteServersRepository.getFavoriteServers(username)}, 200

@db_blueprint.route('/player', methods=['POST'])
@db_blueprint.doc(**DOCS['add_player'])
@db_blueprint.input(PlayerCreateRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def addPlayer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = get_jwt_identity()
    name = request_data.get('name')
    uuid = request_data.get('uuid')
    if username is None or name is None or uuid is None:
        return {'error': 'bad request'}, 400

    return {'status': PlayerRepository.createPlayer(username, name, uuid)}, 200

@db_blueprint.route('/player', methods=['DELETE'])
@db_blueprint.doc(**DOCS['remove_player'])
@db_blueprint.input(PlayerUuidRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def removePlayer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = get_jwt_identity()
    uuid = request_data.get('uuid')
    if username is None or uuid is None:
        return {'error': 'bad request'}, 400

    return {'status': PlayerRepository.removePlayer(username, uuid)}, 200

@db_blueprint.route('/player', methods=['GET'])
@db_blueprint.doc(**DOCS['get_all_players_uuids'])
@db_blueprint.input(UserIdRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(PlayerUUIDsOutputSchema, status_code=200)
@jwt_required()
def getAllPlayersUUIDs(request_data=None):
    username = get_jwt_identity()
    return {'players': PlayerRepository.getAllPlayersUUIDs(username)}, 200

@db_blueprint.route('/playerPrivilege', methods=['POST'])
@db_blueprint.doc(**DOCS['add_player_privilege'])
@db_blueprint.input(PlayerPrivilegeRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def addPlayerPrivilege(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = get_jwt_identity()
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
@jwt_required()
def deletePlayerPrivilege(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = get_jwt_identity()
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
@jwt_required()
def getPlayerPrivileges(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = get_jwt_identity()
    player_uuid = request_data.get('player_uuid')
    if username is None or player_uuid is None:
        return {'error': 'bad request'}, 400

    return {'privileges': PlayersPrivilegesRepository.getPlayerPrivileges(username, player_uuid)}, 200

@db_blueprint.route('/setting', methods=['POST'])
@db_blueprint.doc(**DOCS['add_setting'])
@db_blueprint.input(SettingRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def addSetting(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = get_jwt_identity()
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
@jwt_required()
def removeSetting(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = get_jwt_identity()
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
@jwt_required()
def changeSetting(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    username = get_jwt_identity()
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
