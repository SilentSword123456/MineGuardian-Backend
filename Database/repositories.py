import hashlib
from typing import List
from Database.perms import SettingsPermissions, PlayersPermissions
from Database.database import *

class UserRepository():
    @staticmethod
    def createUser(username: str, password: str) -> bool:
        if UserRepository.doseUserExist(username):
            return False
        hashPassword = hashlib.sha256(password.encode('utf-8')).hexdigest()
        db.session.add(User(username=username, password=hashPassword))
        db.session.commit()
        return True
    @staticmethod
    def removeUser(username: str) -> bool:
        user = db.session.query(User).filter(User.username == username).first()
        if user is None:
            return False
        db.session.delete(user)
        db.session.commit()
        return True

    @staticmethod
    def verify(username: str, password: str) -> bool:
        if not UserRepository.doseUserExist(username):
            return False
        hashPassword = hashlib.sha256(password.encode('utf-8')).hexdigest()
        user = db.session.query(User).filter(User.username == username, User.password == hashPassword).first()
        if user is None:
            return False
        return True

    def getUserId(username: str) -> int:
        if not UserRepository.doseUserExist(username):
            return 0
        user = db.session.query(User).filter(User.username == username).first()
        if user is None:
            return 0
        return user.id

    @staticmethod
    def getUsername(userId: int) -> str:
        if not UserRepository.doseUserExist(userId):
            return ''
        user = db.session.query(User).filter(User.id == userId).first()
        if user is None:
            return ''
        return user.username

    @staticmethod
    def doseUserExist(userId):
        user = db.session.query(User).filter(User.id == userId).first()
        if user is None:
            return False
        return True

class FavoriteServersRepository():
    @staticmethod
    def addFavoriteServer(serverId: int, userId: int) -> bool:
        if not UserRepository.doseUserExist(userId):
            return False

        if serverId in FavoriteServersRepository.getFavoriteServers(userId):
            return False
        db.session.add(FavoriteServers(user_id=userId, server_id=serverId))
        db.session.commit()
        return True
    @staticmethod
    def removeFavoriteServer(userId: int, serverId:int) -> bool:
        if not UserRepository.doseUserExist(userId):
            return False
        server = db.session.query(FavoriteServers).filter(FavoriteServers.user_id == userId, FavoriteServers.server_id == serverId).first()
        if server is None:
            return False
        db.session.delete(server)
        db.session.commit()
        return True

    @staticmethod
    def getFavoriteServers(userId: int) -> List[int]:
        if not UserRepository.doseUserExist(userId):
            return []
        servers = db.session.query(FavoriteServers).filter(FavoriteServers.user_id == userId).all()
        if not servers:
            return []

        serversId = []
        for server in servers:
            serversId.append(server.server_id)
        return serversId

class PlayerRepository():
    @staticmethod
    def createPlayer(userId: int, name: str, uuid: str) -> bool:
        if not UserRepository.doseUserExist(userId):
            return False
        db.session.add(Player(user_id=userId, name=name, uuid=uuid))
        db.session.commit()
        return True
    @staticmethod
    def removePlayer(userId: int, uuid:str) -> bool:
        if not UserRepository.doseUserExist(userId):
            return False
        player = db.session.query(Player).filter(Player.user_id == userId, Player.uuid == uuid).first()
        if player is None:
            return False
        db.session.delete(player)
        db.session.commit()
        return True
    @staticmethod
    def getAllPlayersUUIDs(userId: int):
        if not UserRepository.doseUserExist(userId):
            return False
        players = db.session.query(Player).filter(Player.user_id == userId).all()
        if not players:
            return False

        playersUUIDs = []
        for player in players:
            playersUUIDs.append(player.uuid)
        return playersUUIDs

    @staticmethod
    def getPlayerId(userId: int, playerUUID:str) -> int:
        if not UserRepository.doseUserExist(userId):
            return 0
        player = db.session.query(Player).filter(Player.userId == userId, Player.uuid == playerUUID).first()
        if player is None:
            return 0
        return player.id

class PlayersPrivilegesRepository():
    @staticmethod
    def addPlayerPrivilege(userId: int, playerUUID: str, privilegeId: int) -> bool:
        if privilegeId not in PlayersPermissions:
            return False
        if not UserRepository.doseUserExist(userId):
            return False

        playerId = PlayerRepository.getPlayerId(userId, playerUUID)
        db.session.add(PlayersPrivileges(playerId=playerId, privilege_id = privilegeId))
        db.session.commit()
        return True
    @staticmethod
    def deletePlayerPrivilege(userId: int, playerUUID: str, privilegeId: int) -> bool:
        if not UserRepository.doseUserExist(userId):
            return False

        playerId = PlayerRepository.getPlayerId(userId, playerUUID)
        if playerId == 0:
            return False

        privileges = db.session.query(PlayersPrivileges).filter(PlayersPrivileges.player_id == playerId, PlayersPrivileges.privilege_id == privilegeId).all()
        if not privileges:
            return False
        for privilege in privileges:
            db.session.delete(privilege)
        db.session.commit()
        return True
    @staticmethod
    def getPlayerPrivileges(userId: int, playerUUID:str) -> List[PlayersPrivileges]:
        playerId = PlayerRepository.getPlayerId(userId, playerUUID)
        if playerId == 0:
            return []
        privileges = db.session.query(PlayersPrivileges).filter(PlayersPrivileges.player_id == playerId).all()
        if not privileges:
            return []
        return privileges

class SettingsRepository():
    @staticmethod
    def addSetting(userId: int, rule, approved=False):
        if not UserRepository.doseUserExist(userId):
            return False
        if rule not in SettingsPermissions:
            return False
        if db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first() is not None:
            return False
        db.session.add(Settings(user_id=userId, rule=rule, approved=approved))
        db.session.commit()
        return True
    @staticmethod
    def removeSetting(userId: int, rule):
        if not UserRepository.doseUserExist(userId):
            return False
        setting = db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first()
        if setting is None:
            return False
        db.session.delete(setting)
        db.session.commit()
        return True
    @staticmethod
    def changeSetting(userId: int, rule, approved=False):
        if not UserRepository.doseUserExist(userId):
            return False
        setting = db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first()
        if setting is None:
            return False
        setting.approved=approved
        db.session.commit()
        return True


