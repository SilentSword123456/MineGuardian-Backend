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

