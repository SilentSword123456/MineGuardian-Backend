from apiflask.schemas import Schema
from marshmallow.fields import Boolean, Float, Integer, List, Nested, String


class ServerListItemSchema(Schema):
    name = String(required=True)
    id = Integer(required=True)
    isRunning = Boolean(required=True)
    max_memory_mb = Integer(required=True)


class ListServersOutputSchema(Schema):
    servers = List(Nested(ServerListItemSchema), required=True)


class GeneralServerInfoOutputSchema(Schema):
    name = String(required=True)
    is_running = Boolean(required=True)
    pid = Integer(required=True)
    uptime_seconds = Float(required=True)
    max_memory_mb = Integer(required=True)
    online_players = Nested(lambda: GeneralOnlinePlayersOutputSchema(), required=True)


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
    warning = String(required=True)


class GetAvailableVersionsOutputSchema(Schema):
    versions = List(String(), required=True)


class RemoveServerOutputSchema(Schema):
    error = String(required=True)


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


class UserIdRequestSchema(Schema):
    user_id = Integer(required=True)


class UserIdServerIdRequestSchema(Schema):
    user_id = Integer(required=True)
    server_id = Integer(required=True)


class PlayerCreateRequestSchema(Schema):
    user_id = Integer(required=True)
    name = String(required=True)
    uuid = String(required=True)


class PlayerUuidRequestSchema(Schema):
    user_id = Integer(required=True)
    uuid = String(required=True)


class PlayerPrivilegeRequestSchema(Schema):
    player_id = Integer(required=True)
    privilege_id = Integer(required=True)


class PlayerPrivilegesRequestSchema(Schema):
    user_id = Integer(required=True)
    player_uuid = String(required=True)


class SettingRequestSchema(Schema):
    user_id = Integer(required=True)
    rule = Integer(required=True)
    approved = Boolean(load_default=False)


