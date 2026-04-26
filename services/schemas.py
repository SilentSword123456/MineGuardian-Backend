from apiflask.schemas import Schema
from marshmallow.fields import Boolean, Dict, Float, Integer, List, Nested, String


class ServerListItemSchema(Schema):
    name = String(required=True)
    server_id = Integer(required=True)
    isRunning = Boolean(required=True)
    max_memory_mb = Integer(required=True)
    online_players = Nested(lambda: GeneralOnlinePlayersOutputSchema(), required=True)


class ListServersOutputSchema(Schema):
    servers = List(Nested(ServerListItemSchema), required=True)


class GeneralServerInfoOutputSchema(Schema):
    server_id = Integer(required=True)
    is_running = Boolean(required=True)
    pid = Integer(required=True)
    uptime_seconds = Float(required=True)
    max_memory_mb = Integer(required=True)
    max_players = Integer(required=True)
    server_port = Integer(required=True)


class GeneralOnlinePlayersOutputSchema(Schema):
    max = Integer(required=True)


class StartServerOutputSchema(Schema):
    message = String(required=True)


class StopServerOutputSchema(Schema):
    message = String(required=True)


class OnlinePlayersOutputSchema(Schema):
    online = Integer(required=True)
    max = Integer(required=True)
    players = List(String(), required=True)


class GetServerStatsOutputSchema(Schema):
    cpu_usage_percent = Float(required=True)
    memory_usage_mb = Float(required=True)
    max_memory_mb = Integer(required=True)
    online_players = Nested(OnlinePlayersOutputSchema, required=True)


class AddServerOutputSchema(Schema):
    status = Boolean(required=True)
    message = String(required=True)


class GetAvailableVersionsOutputSchema(Schema):
    versions = List(String(), required=True)


class RemoveServerOutputSchema(Schema):
    status = Boolean(required=True)
    message = String(required=True)


class StatusOutputSchema(Schema):
    status = Boolean()
    error = String()


class FavoriteServersOutputSchema(Schema):
    servers = List(Integer())
    error = String()


class PlayerUUIDsOutputSchema(Schema):
    players = List(String())
    error = String()


class PlayerPrivilegeItemSchema(Schema):
    id = Integer()
    player_id = Integer()
    privilege_id = Integer()


class PlayerPrivilegesOutputSchema(Schema):
    privileges = List(Nested(PlayerPrivilegeItemSchema))
    error = String()


class UserCreateRequestSchema(Schema):
    email = String(required=True)
    firstName = String(required=True)
    username = String(required=True)
    password = String(required=True)


class SendVerificationTokenRequestSchema(Schema):
    email = String(load_default=None)
    username = String(load_default=None)


class UserIdRequestSchema(Schema):
    username = String(required=True)


class LoginRequestSchema(Schema):
    user_id = String(required=True)
    password = String(required=True)


class LoginOutputSchema(Schema):
    # Login success returns token via Set-Cookie, not JSON fields.
    pass


class UserPermReqSchema(Schema):
    user_id = Integer(required=True)
    server_id = Integer(required=True)
    perm_id = Integer(required=True)


class ServerIdRequestSchema(Schema):
    server_id = Integer(required=True)


class PlayerCreateRequestSchema(Schema):
    name = String(required=True)
    uuid = String(required=True)


class PlayerUuidRequestSchema(Schema):
    uuid = String(required=True)


class PlayerPrivilegeRequestSchema(Schema):
    player_uuid = String(required=True)
    privilege_id = Integer(required=True)


class PlayerPrivilegesRequestSchema(Schema):
    player_uuid = String(required=True)


class SettingRequestSchema(Schema):
    rule = Integer(required=True)
    approved = Boolean(load_default=False)


class RuleRequestSchema(Schema):
    rule = Integer(required=True)


class DefaultPermissionsOutputSchema(Schema):
    AddPermissionToServer = Integer()
    RemovePermissionFromServer = Integer()
    GetServerInfo = Integer()
    StartServer = Integer()
    StopServer = Integer()
    ViewServer = Integer()
    UninstallServer = Integer()


class UserServerPermsOutputSchema(Schema):
    permissions = Dict(keys=Integer(), values=List(Integer()))
    error = String()