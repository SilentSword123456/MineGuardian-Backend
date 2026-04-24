import logging
from apiflask import APIBlueprint
from flask_jwt_extended import jwt_required, get_jwt_identity
from Database.repositories import ServersRepository, ServersUsersPermsRepository
from Database.perms import ServersPermissions
import Database.perms
from Database.repositories import *
from services.docs import DOCS
from services.schemas import (
    PlayerCreateRequestSchema,
    PlayerPrivilegeRequestSchema,
    PlayerPrivilegesRequestSchema,
    FavoriteServersOutputSchema,
    PlayerUuidRequestSchema,
    RuleRequestSchema,
    ServerIdRequestSchema,
    SettingRequestSchema,
    PlayerPrivilegesOutputSchema,
    PlayerUUIDsOutputSchema,
    UserCreateRequestSchema,
    UserIdRequestSchema,
    UserPermReqSchema,
    StatusOutputSchema,
    DefaultPermissionsOutputSchema,
    UserServerPermsOutputSchema,
)

db_blueprint = APIBlueprint('database', __name__)
logger = logging.getLogger(__name__)

@db_blueprint.route('/user', methods=['POST'])
@db_blueprint.doc(**DOCS['create_user'])
@db_blueprint.input(UserCreateRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
def createUser(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    email = request_data.get('email')
    username = request_data.get('username')
    password = request_data.get('password')
    if email is None or username is None or password is None:
        return {'error': 'bad request'}, 400


    return {'status': UserRepository.createUser(email, username, password)}, 200

@db_blueprint.route('/sendVerificationToken', methods=['GET'])
def sendVerificationToken(request_data=None):
    email = request_data.get('email')
    userId = UserRepository.getUserId(email)
    if userId is None:
        return {'error': 'bad request'}, 400
    return {'status': UserRepository.sendVerificationToken(userId)}, 200

@db_blueprint.route('/user', methods=['DELETE'])
@db_blueprint.doc(**DOCS['remove_user'])
@db_blueprint.input(UserIdRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def removeUser(request_data=None):
    userId = int(get_jwt_identity())
    if request_data is None:
        return {'error': 'bad request'}, 400

    targetUsername = request_data.get('username')
    if targetUsername is None:
        return {'error': 'bad request'}, 400

    username = UserRepository.getUsername(userId)

    if username != targetUsername:
        return {'error': 'forbidden'}, 403

    return {'status': UserRepository.removeUser(targetUsername)}, 200

@db_blueprint.route('/favoriteServers', methods=['POST'])
@db_blueprint.doc(**DOCS['add_favorite_server'])
@db_blueprint.input(ServerIdRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def addFavoriteServer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400
    userId = int(get_jwt_identity())
    server_id = request_data.get('server_id')
    if server_id is None or userId is None:
        return {'error': 'bad request'}, 400

    try:
        server_id = int(server_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': FavoriteServersRepository.addFavoriteServer(server_id, userId)}, 200

@db_blueprint.route('/favoriteServers', methods=['DELETE'])
@db_blueprint.doc(**DOCS['remove_favorite_server'])
@db_blueprint.input(ServerIdRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def removeFavoriteServer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400
    userId = int(get_jwt_identity())
    server_id = request_data.get('server_id')
    if server_id is None or userId is None:
        return {'error': 'bad request'}, 400
    try:
        server_id = int(server_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': FavoriteServersRepository.removeFavoriteServer(userId, server_id)}, 200

@db_blueprint.route('/favoriteServers', methods=['GET'])
@db_blueprint.doc(**DOCS['get_favorite_servers'])
@db_blueprint.output(FavoriteServersOutputSchema, status_code=200)
@jwt_required()
def getFavoriteServers():
    userId = int(get_jwt_identity())
    return {'servers': FavoriteServersRepository.getFavoriteServers(userId)}, 200

@db_blueprint.route('/player', methods=['POST'])
@db_blueprint.doc(**DOCS['add_player'])
@db_blueprint.input(PlayerCreateRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def addPlayer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    userId = int(get_jwt_identity())
    name = request_data.get('name')
    uuid = request_data.get('uuid')
    if userId is None or name is None or uuid is None:
        return {'error': 'bad request'}, 400

    return {'status': PlayerRepository.createPlayer(userId, name, uuid)}, 200

@db_blueprint.route('/player', methods=['DELETE'])
@db_blueprint.doc(**DOCS['remove_player'])
@db_blueprint.input(PlayerUuidRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def removePlayer(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    userId = int(get_jwt_identity())
    uuid = request_data.get('uuid')
    if userId is None or uuid is None:
        return {'error': 'bad request'}, 400

    return {'status': PlayerRepository.removePlayer(userId, uuid)}, 200

@db_blueprint.route('/player', methods=['GET'])
@db_blueprint.doc(**DOCS['get_all_players_uuids'])
@db_blueprint.output(PlayerUUIDsOutputSchema, status_code=200)
@jwt_required()
def getAllPlayersUUIDs():
    userId = int(get_jwt_identity())
    return {'players': PlayerRepository.getAllPlayersUUIDs(userId)}, 200

@db_blueprint.route('/playerPrivilege', methods=['POST'])
@db_blueprint.doc(**DOCS['add_player_privilege'])
@db_blueprint.input(PlayerPrivilegeRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def addPlayerPrivilege(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    userId = int(get_jwt_identity())
    player_uuid = request_data.get('player_uuid')
    privilege_id = request_data.get('privilege_id')
    if userId is None or player_uuid is None or privilege_id is None:
        return {'error': 'bad request'}, 400

    try:
        privilege_id = int(privilege_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': PlayersPrivilegesRepository.addPrivilege(userId, player_uuid, privilege_id)}, 200

@db_blueprint.route('/playerPrivilege', methods=['DELETE'])
@db_blueprint.doc(**DOCS['delete_player_privilege'])
@db_blueprint.input(PlayerPrivilegeRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def deletePlayerPrivilege(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    userId = int(get_jwt_identity())
    player_uuid = request_data.get('player_uuid')
    privilege_id = request_data.get('privilege_id')
    if userId is None or player_uuid is None or privilege_id is None:
        return {'error': 'bad request'}, 400

    try:
        privilege_id = int(privilege_id)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': PlayersPrivilegesRepository.deletePrivilege(userId, player_uuid, privilege_id)}, 200

@db_blueprint.route('/playerPrivilege', methods=['GET'])
@db_blueprint.doc(**DOCS['get_player_privileges'])
@db_blueprint.input(PlayerPrivilegesRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(PlayerPrivilegesOutputSchema, status_code=200)
@jwt_required()
def getPlayerPrivileges(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    userId = int(get_jwt_identity())
    player_uuid = request_data.get('player_uuid')
    if userId is None or player_uuid is None:
        return {'error': 'bad request'}, 400

    return {'privileges': PlayersPrivilegesRepository.getPlayerPrivileges(userId, player_uuid)}, 200

@db_blueprint.route('/setting', methods=['POST'])
@db_blueprint.doc(**DOCS['add_setting'])
@db_blueprint.input(SettingRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def addSetting(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    userId = int(get_jwt_identity())
    rule = request_data.get('rule')
    approved = request_data.get('approved', False)
    if userId is None or rule is None:
        return {'error': 'bad request'}, 400

    try:
        rule = int(rule)
        approved = bool(approved)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': SettingsRepository.addSetting(userId, rule, approved)}, 200

@db_blueprint.route('/setting', methods=['DELETE'])
@db_blueprint.doc(**DOCS['remove_setting'])
@db_blueprint.input(RuleRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def removeSetting(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    userId = int(get_jwt_identity())
    rule = request_data.get('rule')
    if userId is None or rule is None:
        return {'error': 'bad request'}, 400

    try:
        rule = int(rule)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': SettingsRepository.removeSetting(userId, rule)}, 200

@db_blueprint.route('/setting', methods=['PATCH'])
@db_blueprint.doc(**DOCS['change_setting'])
@db_blueprint.input(SettingRequestSchema, location='json', arg_name='request_data', validation=False)
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def changeSetting(request_data=None):
    if request_data is None:
        return {'error': 'bad request'}, 400

    userId = int(get_jwt_identity())
    rule = request_data.get('rule')
    approved = request_data.get('approved', False)
    if userId is None or rule is None:
        return {'error': 'bad request'}, 400

    try:
        rule = int(rule)
        approved = bool(approved)
    except (ValueError, TypeError):
        return {'error': 'bad request'}, 400

    return {'status': SettingsRepository.changeSetting(userId, rule, approved)}, 200

@db_blueprint.route('/userPermission', methods=['POST'])
@db_blueprint.doc(**DOCS['add_user_permission_for_server'])
@db_blueprint.input(UserPermReqSchema, location='json', arg_name='request_data')
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def addUserPermissionForServer(request_data):
    userId = int(get_jwt_identity())
    target_user_id = request_data.get('user_id')
    server_id = request_data.get('server_id')
    perm_id = request_data.get('perm_id')

    result = ServersUsersPermsRepository.addPerm(userId, server_id, target_user_id, perm_id)
    if not result:
        return {'error': 'Failed to add permission to the records.'}, 401

    return {'status': True}, 200

@db_blueprint.route('/userPermission', methods=['DELETE'])
@db_blueprint.doc(**DOCS['remove_user_permission_for_server'])
@db_blueprint.input(UserPermReqSchema, location='json', arg_name='request_data')
@db_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def removeUserPermissionForServer(request_data):
    userId = int(get_jwt_identity())
    target_user_id = request_data.get('user_id')
    server_id = request_data.get('server_id')
    perm_id = request_data.get('perm_id')

    result = ServersUsersPermsRepository.removePerm(userId, server_id, target_user_id, perm_id)
    if not result:
        return {'error': 'Failed to remove permission from the records.'}, 401

    return {'status': True}, 200

@db_blueprint.route('/getDefaultServersPermissions', methods=['GET'])
@db_blueprint.doc(**DOCS['get_default_servers_permissions'])
@db_blueprint.output(DefaultPermissionsOutputSchema, status_code=200)
def getDefaultServersPermissions():
    permsList = Database.perms.ServersPermissions
    permsDict = {perm.name: perm.value for perm in permsList}
    return permsDict, 200

@db_blueprint.route('/servers/<int:server_id>/permissions', methods=['GET'])
@db_blueprint.doc(**DOCS['get_users_with_perms_on_server'])
@db_blueprint.output(UserServerPermsOutputSchema, status_code=200)
@jwt_required()
def getUsersWithPermsOnServer(server_id):
    userId = int(get_jwt_identity())
    
    logger.info("getUsersWithPermsOnServer: Fetching permissions server_id=%s userId=%s", server_id, userId)

    if ServersRepository.getServerOwner(server_id) != userId and not ServersUsersPermsRepository.doesUserHavePerm(userId, server_id, ServersPermissions.ViewServer.value):
        logger.warning("getUsersWithPermsOnServer: Unauthorized access attempt server_id=%s userId=%s", server_id, userId)
        return {'error': 'Unauthorized', 'permissions': {}}, 401

    perms = ServersUsersPermsRepository.getUsersWithPermsOnServer(server_id)
    logger.debug("getUsersWithPermsOnServer: Permissions fetched successfully server_id=%s count=%d", server_id, len(perms))
    return {'permissions': perms}, 200

