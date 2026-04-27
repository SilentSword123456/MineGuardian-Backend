from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
import services.emailService
from Database.perms import SettingsPermissions, PlayersPermissions, ServersPermissions
from Database.database import *
from utils import getConfig

s = URLSafeTimedSerializer(getConfig()["flaskConfig"]["SECRET_KEY"])


class UserRepository():
    @staticmethod
    def createUser(email:str, username: str, password: str, firstName: str) -> bool:
        if (db.session.query(User).filter(User.username == username).first() is not None
                or db.session.query(User).filter(User.email == email).first() is not None):
            return False
        hashPassword = generate_password_hash(password)
        db.session.add(User(email = email, username=username, password=hashPassword, first_name=firstName))
        db.session.commit()
        user = db.session.query(User).filter(User.email == email).first()
        # Send verification email immediately after account creation
        UserRepository.sendVerificationToken(user.id)
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
    def verify(identifier: str, password: str) -> bool:
        user = db.session.query(User).filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()
        if user is None:
            return False
        if user.is_verified is not True:
            return False
        return check_password_hash(user.password, password)

    @staticmethod
    def getUserId(identifier: str) -> int:
        user = db.session.query(User).filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()
        return user.id if user else 0

    @staticmethod
    def getUsername(userId: int) -> str:
        if not UserRepository.doesUserExist(userId):
            return ''
        user = db.session.query(User).filter(User.id == userId).first()
        if user is None:
            return ''
        return user.username

    @staticmethod
    def doesUserExist(userId):
        user = db.session.query(User).filter(User.id == userId).first()
        if user is None:
            return False
        return True

    @staticmethod
    def createVerificationToken(userId: int) -> str:
        if not UserRepository.doesUserExist(userId):
            return ""
        return s.dumps(userId, salt='email-confirm')

    @staticmethod
    def verifyToken(userId: int, token: str) -> bool:
        try:
            token_userId = s.loads(token, salt='email-confirm', max_age=86400)
        except:
            return False

        if token_userId != userId:
            return False

        user = db.session.query(User).filter(User.id == userId).first()
        if user is None:
            return False
        user.is_verified = True
        db.session.commit()
        return True

    @staticmethod
    def verifyEmailToken(token: str) -> bool:
        try:
            userId = s.loads(token, salt='email-confirm', max_age=86400)
        except Exception:
            return False

        user = db.session.query(User).filter(User.id == userId).first()
        if user is None:
            return False

        user.is_verified = True
        db.session.commit()
        return True

    @staticmethod
    def sendVerificationToken(userId: int) -> bool:
        if not UserRepository.doesUserExist(userId):
            return False
        token = UserRepository.createVerificationToken(userId)
        user = db.session.query(User).filter(User.id == userId).first()
        result = services.emailService.send_verification_email(user.email, token, user.first_name)
        return result

class FavoriteServersRepository():
    @staticmethod
    def addFavoriteServer(serverId: int, userId: int) -> bool:
        if not UserRepository.doesUserExist(userId):
            return False

        if serverId in FavoriteServersRepository.getFavoriteServers(userId):
            return False
        db.session.add(FavoriteServers(user_id=userId, server_id=serverId))
        db.session.commit()
        return True

    @staticmethod
    def removeFavoriteServer(userId: int, serverId:int) -> bool:
        if not UserRepository.doesUserExist(userId):
            return False
        server = db.session.query(FavoriteServers).filter(FavoriteServers.user_id == userId, FavoriteServers.server_id == serverId).first()
        if server is None:
            return False
        db.session.delete(server)
        db.session.commit()
        return True

    @staticmethod
    def getFavoriteServers(userId: int) -> list[int]:
        if not UserRepository.doesUserExist(userId):
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
        if not UserRepository.doesUserExist(userId):
            return False
        db.session.add(Player(user_id=userId, name=name, uuid=uuid))
        db.session.commit()
        return True

    @staticmethod
    def removePlayer(userId: int, uuid:str) -> bool:
        if not UserRepository.doesUserExist(userId):
            return False
        player = db.session.query(Player).filter(Player.user_id == userId, Player.uuid == uuid).first()
        if player is None:
            return False
        db.session.delete(player)
        db.session.commit()
        return True

    @staticmethod
    def getAllPlayersUUIDs(userId: int) -> list[str]:
        if not UserRepository.doesUserExist(userId):
            return []
        players = db.session.query(Player).filter(Player.user_id == userId).all()
        if not players:
            return []

        playersUUIDs = []
        for player in players:
            playersUUIDs.append(player.uuid)
        return playersUUIDs

    @staticmethod
    def getPlayerId(userId: int, playerUUID:str) -> int:
        if not UserRepository.doesUserExist(userId):
            return 0
        player = db.session.query(Player).filter(Player.user_id == userId, Player.uuid == playerUUID).first()
        if player is None:
            return 0
        return player.id

class PlayersPrivilegesRepository():
    @staticmethod
    def addPrivilege(userId: int, playerUUID: str, privilegeId: int) -> bool:
        try:
            PlayersPermissions(privilegeId)
        except ValueError:
            return False
        if not UserRepository.doesUserExist(userId):
            return False

        playerId = PlayerRepository.getPlayerId(userId, playerUUID)
        if playerId == 0:
            return False
        if db.session.query(PlayersPrivileges).filter(PlayersPrivileges.player_id == playerId,PlayersPrivileges.privilege_id == privilegeId).first() is not None:
            return False

        db.session.add(PlayersPrivileges(player_id=playerId, privilege_id = privilegeId))
        db.session.commit()
        return True

    @staticmethod
    def deletePrivilege(userId: int, playerUUID: str, privilegeId: int) -> bool:
        if not UserRepository.doesUserExist(userId):
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
    def getPlayerPrivileges(userId: int, playerUUID: str) -> list[int]:
        if not UserRepository.doesUserExist(userId):
            return []

        playerId = PlayerRepository.getPlayerId(userId, playerUUID)
        if playerId == 0:
            return []

        privileges = db.session.query(PlayersPrivileges).filter(PlayersPrivileges.player_id == playerId).all()
        return [p.privilege_id for p in privileges]

class SettingsRepository():
    @staticmethod
    def addSetting(userId: int, rule, approved=False):
        if not UserRepository.doesUserExist(userId):
            return False
        try:
            SettingsPermissions(rule)
        except ValueError:
            return False
        if db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first() is not None:
            return False
        db.session.add(Settings(user_id=userId, rule=rule, approved=approved))
        db.session.commit()
        return True

    @staticmethod
    def removeSetting(userId: int, rule):
        if not UserRepository.doesUserExist(userId):
            return False
        setting = db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first()
        if setting is None:
            return False
        db.session.delete(setting)
        db.session.commit()
        return True

    @staticmethod
    def changeSetting(userId: int, rule, approved=False):
        if not UserRepository.doesUserExist(userId):
            return False
        setting = db.session.query(Settings).filter(Settings.user_id == userId, Settings.rule == rule).first()
        if setting is None:
            return False
        setting.approved=approved
        db.session.commit()
        return True


class ServersRepository():
    @staticmethod
    def addServer(userId: int, serverName: str, serverVersion: str) -> bool:
        if not UserRepository.doesUserExist(userId):
            return False
        if db.session.query(Servers).filter(Servers.owner_id == userId,Servers.name == serverName).first() is not None:
            return False

        db.session.add(Servers(owner_id=userId, name=serverName, server_version=serverVersion))
        db.session.commit()
        return True

    @staticmethod
    def removeServer(userId: int, serverName: str) -> bool:
        if not UserRepository.doesUserExist(userId):
            return False

        server = db.session.query(Servers).filter(Servers.owner_id==userId, Servers.name==serverName).first()
        if server is None:
            return False
        db.session.delete(server)
        db.session.commit()
        return True

    @staticmethod
    def changeServerName(userId: int, currentServerName: str, newServerName: str) -> bool:
        if not UserRepository.doesUserExist(userId):
            return False
        server = db.session.query(Servers).filter(Servers.owner_id==userId, Servers.name==currentServerName).first()
        if server is None:
            return False
        if db.session.query(Servers).filter(Servers.owner_id == userId,Servers.name == newServerName).first() is not None:
            return False

        server.name = newServerName
        db.session.commit()
        return True

    @staticmethod
    def doesServerExist(serverId: int) -> bool:
        server = db.session.query(Servers).filter(Servers.id == serverId).first()
        if server is None:
            return False
        return True

    @staticmethod
    def getServerOwner(serverId: int) -> int:
        server = db.session.query(Servers).filter(Servers.id == serverId).first()
        if server is None:
            return 0
        return server.owner_id

    @staticmethod
    def getServerId(userId: int, serverName: str) -> int:
        if not UserRepository.doesUserExist(userId):
            return 0
        server = db.session.query(Servers).filter(Servers.owner_id == userId, Servers.name == serverName).first()
        if server is None:
            return 0
        return server.id

    @staticmethod
    def getServerName(serverId: int) -> str:
        server = db.session.query(Servers).filter(Servers.id == serverId).first()
        if server is None:
            return ''
        return server.name
    @staticmethod
    def getServerVersion(serverId: int) -> str:
        if not ServersRepository.doesServerExist(serverId):
            return ''
        server = db.session.query(Servers).filter(Servers.id == serverId).first()
        if server is None:
            return ''
        return server.server_version

class ServersUsersPermsRepository():
    @staticmethod
    def addPerm(userId: int, serverId: int, targetUserId: int, permId: int) -> bool:
        if not UserRepository.doesUserExist(userId) or not UserRepository.doesUserExist(targetUserId):
            return False
        if not ServersRepository.doesServerExist(serverId):
            return False
        if (ServersRepository.getServerOwner(serverId) != userId and not ServersUsersPermsRepository.doesUserHavePerm(userId, serverId, ServersPermissions.AddPermissionToServer.value)):
            return False
        if ServersRepository.getServerOwner(serverId) == targetUserId:
            return False
        try:
            ServersPermissions(permId)
        except ValueError:
            return False
        if db.session.query(ServersUsersPerms).filter(ServersUsersPerms.user_id==targetUserId, ServersUsersPerms.server_id==serverId, ServersUsersPerms.perm_id==permId).first() is not None:
            return False

        db.session.add(ServersUsersPerms(user_id=targetUserId, server_id=serverId, perm_id=permId))
        db.session.commit()
        return True

    @staticmethod
    def getPerms(userId: int, serverId: int) -> list[int]:
        if not UserRepository.doesUserExist(userId):
            return []
        if not ServersRepository.doesServerExist(serverId):
            return []
        perms = db.session.query(ServersUsersPerms).filter(ServersUsersPerms.user_id == userId, ServersUsersPerms.server_id == serverId).all()
        if not perms:
            return []

        permsPermsId = []
        for perm in perms:
            permsPermsId.append(perm.perm_id)

        return permsPermsId

    @staticmethod
    def removePerm(userId: int, serverId: int, targetUserId: int, permId: int) -> bool:
        if not UserRepository.doesUserExist(userId) or not UserRepository.doesUserExist(targetUserId):
            return False
        if not ServersRepository.doesServerExist(serverId):
            return False
        if ServersRepository.getServerOwner(serverId) != userId and not ServersUsersPermsRepository.doesUserHavePerm(userId, serverId, ServersPermissions.RemovePermissionFromServer.value):
            return False

        perm = db.session.query(ServersUsersPerms).filter(ServersUsersPerms.user_id == targetUserId, ServersUsersPerms.server_id == serverId, ServersUsersPerms.perm_id == permId).first()
        if perm is None:
            return False
        db.session.delete(perm)
        db.session.commit()
        return True

    @staticmethod
    def doesUserHavePerm(userId: int, serverId: int, permId: int) -> bool:
        if not UserRepository.doesUserExist(userId):
            return False
        if not ServersRepository.doesServerExist(serverId):
            return False

        # Server owners have implicit access to every permission.
        if ServersRepository.getServerOwner(serverId) == userId:
            return True

        perms = ServersUsersPermsRepository.getPerms(userId, serverId)
        if not perms:
            return False

        for perm in perms:
            if perm == permId:
                return True

        return False

    @staticmethod
    def getServersWithUserPerm(userId: int, permId: int) -> list[int]:
        if not UserRepository.doesUserExist(userId):
            return []

        try:
            ServersPermissions(permId)
        except ValueError:
            return []

        rows = db.session.query(ServersUsersPerms).filter(
            ServersUsersPerms.user_id == userId,
            ServersUsersPerms.perm_id == permId,
            ).all()

        return [row.server_id for row in rows]

    @staticmethod
    def getUsersWithPermsOnServer(serverId: int) -> dict[int, list[int]]:
        if not ServersRepository.doesServerExist(serverId):
            return {}

        rows = db.session.query(ServersUsersPerms).filter(
            ServersUsersPerms.server_id == serverId,
            ).all()

        result = {}
        for row in rows:
            if row.user_id not in result:
                result[row.user_id] = []
            result[row.user_id].append(row.perm_id)
        return result