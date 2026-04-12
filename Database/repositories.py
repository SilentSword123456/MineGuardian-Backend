from typing import List

from Database.perms import SettingsPermissions, PlayersPermissions
from Database.database import *

class UserRepository():
    @staticmethod
    def createUser():
        db.session.add(User())
        db.session.commit()
        return True
    @staticmethod
    def removeUser(id):
        users = db.session.query(User).filter(User.id == id).first()
        if users is None:
            return False
        db.session.delete(users)
        db.session.commit()
        return True

    @staticmethod
    def checkUser(userId):
        users = db.session.query(User).filter(User.id == userId).first()
        if users is None:
            return False
        return True

class FavoriteServersRepository():
    @staticmethod
    def addFavoriteServer(serverId: int, userId: int ) -> bool:
        if not UserRepository.checkUser(userId):
            return False

        print("serverId:" + str(serverId))
        print("serversIds: " + str(FavoriteServersRepository.getFavoriteServers(userId)))
        if serverId in FavoriteServersRepository.getFavoriteServers(userId):
            return False
        db.session.add(FavoriteServers(user_id=userId, server_id=serverId))
        db.session.commit()
        return True
    @staticmethod
    def removeFavoriteServer(userId: int, serverId:int) -> bool:
        if not UserRepository.checkUser(userId):
            return False
        server = db.session.query(FavoriteServers).filter(FavoriteServers.user_id == userId, FavoriteServers.server_id == serverId).first()
        if server is None:
            return False
        db.session.delete(server)
        db.session.commit()
        return True

    @staticmethod
    def getFavoriteServers(userId: int) -> List[int]:
        if not UserRepository.checkUser(userId):
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
    def createPlayer(userId, name, uuid):
        db.session.add(Player(userId=userId, name=name, uuid=uuid))
        db.session.commit()
        return True
    @staticmethod
    def removePlayer(id):
        players = db.session.query(Player).filter(Player.id == id).first()
        if players is None:
            return False
        db.session.delete(players)
        db.session.commit()
        return True
    @staticmethod
    def getAllPlayers(userId):
        players = db.session.query(Player).filter(Player.user_id == userId).all()
        if not players:
            return False
        return players
    @staticmethod
    def getPlayerId(userId, uuid):
        player = db.session.query(Player).filter(Player.user_id == userId, Player.uuid == uuid).first()
        if player is None:
            return False
        return player.id

class PlayersPrivilegesRepository():
    @staticmethod
    def addPlayerPrivilege(playerId, privilegeId):
        if privilegeId not in PlayersPermissions:
            return False
        db.session.add(PlayersPrivileges(playerId=playerId, privilege_id = privilegeId))
        db.session.commit()
        return True
    @staticmethod
    def deletePlayerPrivilege(playerId, privilegeId):
        privileges = db.session.query(PlayersPrivileges).filter(PlayersPrivileges.player_id == playerId, PlayersPrivileges.privilege_id == privilegeId).all()
        if not privileges:
            return False
        for privilege in privileges:
            db.session.delete(privilege)
        db.session.commit()
        return True
    @staticmethod
    def getPlayerPrivileges(playerId):
        privileges = db.session.query(PlayersPrivileges).filter(PlayersPrivileges.player_id == playerId).all()
        if not privileges:
            return False
        return privileges
    @staticmethod
    def getPlayerPrivilegeId(playerId, privilegeId):
        privilege = db.session.query(PlayersPrivileges).filter(
            PlayersPrivileges.player_id == playerId,
            PlayersPrivileges.privilege_id == privilegeId
        ).first()
        if privilege is None:
            return False
        return privilege.id

class SettingsRepository():
    @staticmethod
    def addSetting(userId, rule, approved=False):
        if rule not in SettingsPermissions:
            return False
        if(db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first() is not None):
            return False
        db.session.add(Settings(userId=userId, rule=rule, approved=approved))
        db.session.commit()
        return True
    @staticmethod
    def removeSetting(userId, rule):
        setting = db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first()
        if setting is None:
            return False
        db.session.delete(setting)
        db.session.commit()
        return True
    @staticmethod
    def changeSetting(userId, rule, approved=False):
        setting = db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first()
        if setting is None:
            return False
        setting.approved=approved
        db.session.commit()
        return True

    @staticmethod
    def getSettingId(userId, rule):
        setting = db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first()
        if setting is None:
            return False
        return setting.id


