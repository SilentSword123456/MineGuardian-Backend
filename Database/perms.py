from enum import Enum

class PlayersPermissions(Enum):
    WhitelistedByDefault = 0
    OP = 1

class SettingsPermissions(Enum):
    NotBlank = 0

class ServersPermissions(Enum):
    AddPermissionToServer = 1
    RemovePermissionFromServer = 2
    GetServerInfo = 3
    StartServer = 4
    StopServer = 5
