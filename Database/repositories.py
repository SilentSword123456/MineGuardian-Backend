import hashlib
from typing import List
from Database.perms import SettingsPermissions, PlayersPermissions
from Database.database import *

class UserRepository():
    @staticmethod
    def createUser(username: str, password: str) -> bool:
        if UserRepository.doseUserExist(username):
            return False
        hashPassword = hashlib.sha256(password.encode('utf-8'))
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
        hashPassword = hashlib.sha256(password.encode('utf-8'))
        user = db.session.query(User).filter(User.username == username, User.password == hashPassword).first()
        if user is None:
            return False
        return True

    @staticmethod
    def doseUserExist(username):
        user = db.session.query(User).filter(User.username == username).first()
        if user is None:
            return False
        return True

class FavoriteServersRepository():
    @staticmethod
    def addFavoriteServer(serverId: int, username: str) -> bool:
        if not UserRepository.doseUserExist(username):
            return False

        if serverId in FavoriteServersRepository.getFavoriteServers(username):
            return False
        db.session.add(FavoriteServers(username=username, server_id=serverId))
        db.session.commit()
        return True
    @staticmethod
    def removeFavoriteServer(userId: int, serverId:int) -> bool:
        if not UserRepository.doseUserExist(userId):
            return False
        server = db.session.query(FavoriteServers).filter(FavoriteServers.username == userId, FavoriteServers.server_id == serverId).first()
        if server is None:
            return False
        db.session.delete(server)
        db.session.commit()
        return True

    @staticmethod
    def getFavoriteServers(username: str) -> List[int]:
        if not UserRepository.doseUserExist(username):
            return []
        servers = db.session.query(FavoriteServers).filter(FavoriteServers.username == username).all()
        if not servers:
            return []

        serversId = []
        for server in servers:
            serversId.append(server.server_id)
        return serversId

class PlayerRepository():
    @staticmethod
    def createPlayer(username: str, name: str, uuid: str) -> bool:
        if not UserRepository.doseUserExist(username):
            return False
        db.session.add(Player(username=username, name=name, uuid=uuid))
        db.session.commit()
        return True
    @staticmethod
    def removePlayer(username: str, uuid:str) -> bool:
        if not UserRepository.doseUserExist(username):
            return False
        player = db.session.query(Player).filter(Player.username == username, Player.uuid == uuid).first()
        if player is None:
            return False
        db.session.delete(player)
        db.session.commit()
        return True
    @staticmethod
    def getAllPlayersUUIDs(username: str):
        if not UserRepository.doseUserExist(username):
            return False
        players = db.session.query(Player).filter(Player.username == username).all()
        if not players:
            return False

        playersUUIDs = []
        for player in players:
            playersUUIDs.append(player.uuid)
        return playersUUIDs

    @staticmethod
    def getPlayerId(username: str , playerUUID:str) -> int:
        if not UserRepository.doseUserExist(username):
            return 0
        player = db.session.query(Player).filter(Player.username == username, Player.uuid == playerUUID).first()
        if player is None:
            return 0
        return player.id

class PlayersPrivilegesRepository():
    @staticmethod
    def addPlayerPrivilege(username: str, playerUUID: str, privilegeId: int) -> bool:
        if privilegeId not in PlayersPermissions:
            return False
        if not UserRepository.doseUserExist(username):
            return False

        playerId = PlayerRepository.getPlayerId(username, playerUUID)
        if playerId == 0:
            return False

        db.session.add(PlayersPrivileges(playerId=playerId, privilege_id = privilegeId))
        db.session.commit()
        return True
    @staticmethod
    def deletePlayerPrivilege(username: str, playerUUID: str, privilegeId: int) -> bool:
        if not UserRepository.doseUserExist(username):
            return False

        playerId = PlayerRepository.getPlayerId(username, playerUUID)
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
    def getPlayerPrivileges(username: str, playerUUID:str) -> List[PlayersPrivileges]:
        playerId = PlayerRepository.getPlayerId(username, playerUUID)
        if playerId == 0:
            return []
        privileges = db.session.query(PlayersPrivileges).filter(PlayersPrivileges.player_id == playerId).all()
        if not privileges:
            return []
        return privileges

class SettingsRepository():
    @staticmethod
    def addSetting(username: str, rule, approved=False):
        userId = PlayerRepository.getPlayerId(username, username)
        if userId == 0:
            return False
        if rule not in SettingsPermissions:
            return False
        if db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first() is not None:
            return False
        db.session.add(Settings(userId=userId, rule=rule, approved=approved))
        db.session.commit()
        return True
    @staticmethod
    def removeSetting(username: str, rule):
        userId = PlayerRepository.getPlayerId(username, username)
        if userId == 0:
            return False
        setting = db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first()
        if setting is None:
            return False
        db.session.delete(setting)
        db.session.commit()
        return True
    @staticmethod
    def changeSetting(username: str, rule, approved=False):
        userId = PlayerRepository.getPlayerId(username, username)
        if userId == 0:
            return False
        setting = db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first()
        if setting is None:
            return False
        setting.approved=approved
        db.session.commit()
        return True


