from enum import Enum

class PlayersPermissions(Enum):
    WhitelistedByDefault = 0
    OP = 1

class SettingsPermissions(Enum):
    NotBlank = 0