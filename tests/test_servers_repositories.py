import hashlib
import os
import tempfile
import unittest

from flask import Flask
from werkzeug.security import check_password_hash, generate_password_hash

from Database.database import (
    FavoriteServers,
    Player,
    PlayersPrivileges,
    Servers,
    ServersUsersPerms,
    Settings,
    User,
    db,
)
from Database.perms import PlayersPermissions, ServersPermissions, SettingsPermissions
from Database.repositories import (
    FavoriteServersRepository,
    PlayerRepository,
    PlayersPrivilegesRepository,
    ServersRepository,
    ServersUsersPermsRepository,
    SettingsRepository,
    UserRepository,
)


class RepositoryTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix='mineguardian_repo_test_', suffix='.db')
        os.close(fd)

        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{self.db_path}"
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.created_user_ids = set()
        self.created_favorite_ids = set()
        self.created_player_ids = set()
        self.created_player_privilege_ids = set()
        self.created_setting_ids = set()
        self.created_server_ids = set()
        self.created_server_perm_ids = set()

    def tearDown(self):
        db.session.rollback()

        cleanup_order = [
            (ServersUsersPerms, self.created_server_perm_ids),
            (PlayersPrivileges, self.created_player_privilege_ids),
            (FavoriteServers, self.created_favorite_ids),
            (Settings, self.created_setting_ids),
            (Player, self.created_player_ids),
            (Servers, self.created_server_ids),
            (User, self.created_user_ids),
        ]

        for model, ids in cleanup_order:
            if ids:
                db.session.query(model).filter(model.id.in_(list(ids))).delete(synchronize_session=False)

        db.session.commit()
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()

        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _track_ids(self, bucket, rows):
        for row in rows:
            bucket.add(row.id)

    def _seed_user(self, username, password='hash'):
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        self.created_user_ids.add(user.id)
        return user.id

    def _seed_server(self, owner_id, name):
        server = Servers(owner_id=owner_id, name=name)
        db.session.add(server)
        db.session.commit()
        self.created_server_ids.add(server.id)
        return server.id

    def _seed_player(self, user_id, name, uuid):
        player = Player(user_id=user_id, name=name, uuid=uuid)
        db.session.add(player)
        db.session.commit()
        self.created_player_ids.add(player.id)
        return player.id

    def _seed_favorite(self, user_id, server_id):
        favorite = FavoriteServers(user_id=user_id, server_id=server_id)
        db.session.add(favorite)
        db.session.commit()
        self.created_favorite_ids.add(favorite.id)
        return favorite.id

    def _seed_player_privilege(self, player_id, privilege_id):
        privilege = PlayersPrivileges(player_id=player_id, privilege_id=privilege_id)
        db.session.add(privilege)
        db.session.commit()
        self.created_player_privilege_ids.add(privilege.id)
        return privilege.id

    def _seed_setting(self, user_id, rule, approved=False):
        setting = Settings(user_id=user_id, rule=rule, approved=approved)
        db.session.add(setting)
        db.session.commit()
        self.created_setting_ids.add(setting.id)
        return setting.id

    def _seed_server_perm(self, server_id, user_id, perm_id):
        perm = ServersUsersPerms(server_id=server_id, user_id=user_id, perm_id=perm_id)
        db.session.add(perm)
        db.session.commit()
        self.created_server_perm_ids.add(perm.id)
        return perm.id

    def _grant_owner_server_permissions(self, server_id, owner_id):
        self._seed_server_perm(server_id, owner_id, ServersPermissions.AddPermissionToServer.value)
        self._seed_server_perm(server_id, owner_id, ServersPermissions.RemovePermissionFromServer.value)


class UserRepositoryTests(RepositoryTestCase):
    def test_create_user_hashes_password_and_rejects_duplicate_username(self):
        username = 'alice'
        password = 'secret-password'

        self.assertTrue(UserRepository.createUser(username, password))
        users = db.session.query(User).filter(User.username == username).all()
        self._track_ids(self.created_user_ids, users)
        self.assertEqual(len(users), 1)
        self.assertTrue(check_password_hash(users[0].password, password))

        self.assertFalse(UserRepository.createUser(username, password))
        users = db.session.query(User).filter(User.username == username).all()
        self._track_ids(self.created_user_ids, users)
        self.assertEqual(len(users), 1)

    def test_verify_accepts_correct_password_and_rejects_wrong_password(self):
        username = 'bob'
        password = 'hunter2'
        self._seed_user(username, generate_password_hash(password))

        self.assertTrue(UserRepository.verify(username, password))
        self.assertFalse(UserRepository.verify(username, 'wrong-password'))

    def test_get_user_id_returns_id_for_existing_username(self):
        username = 'charlie'
        user_id = self._seed_user(username, generate_password_hash('pw'))

        self.assertEqual(UserRepository.getUserId(username), user_id)
        self.assertEqual(UserRepository.getUserId('missing-user'), 0)

    def test_get_username_returns_username_for_existing_id(self):
        user_id = self._seed_user('dora', generate_password_hash('pw'))

        self.assertEqual(UserRepository.getUsername(user_id), 'dora')
        self.assertEqual(UserRepository.getUsername(999999), '')

    def test_remove_user_deletes_existing_user_and_returns_false_when_missing(self):
        self._seed_user('eve', generate_password_hash('pw'))

        self.assertTrue(UserRepository.removeUser('eve'))
        self.assertEqual(db.session.query(User).filter(User.username == 'eve').count(), 0)
        self.assertFalse(UserRepository.removeUser('eve'))

    def test_dose_user_exist_uses_numeric_id(self):
        user_id = self._seed_user('frank', generate_password_hash('pw'))

        self.assertTrue(UserRepository.doseUserExist(user_id))
        self.assertFalse(UserRepository.doseUserExist(999999))


class FavoriteServersRepositoryTests(RepositoryTestCase):
    def test_add_get_and_remove_favorite_server(self):
        user_id = self._seed_user('fav-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(user_id, 'favorite-server')

        self.assertTrue(FavoriteServersRepository.addFavoriteServer(server_id, user_id))
        favorites = FavoriteServersRepository.getFavoriteServers(user_id)
        self.assertEqual(favorites, [server_id])

        self.assertFalse(FavoriteServersRepository.addFavoriteServer(server_id, user_id))
        self.assertTrue(FavoriteServersRepository.removeFavoriteServer(user_id, server_id))
        self.assertEqual(FavoriteServersRepository.getFavoriteServers(user_id), [])
        self.assertFalse(FavoriteServersRepository.removeFavoriteServer(user_id, server_id))

    def test_get_favorite_servers_returns_empty_list_when_none_exist(self):
        user_id = self._seed_user('fav-empty', hashlib.sha256('pw'.encode('utf-8')).hexdigest())

        self.assertEqual(FavoriteServersRepository.getFavoriteServers(user_id), [])

    def test_add_favorite_server_rejects_missing_user(self):
        server_id = self._seed_server(self._seed_user('fav-server-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest()), 'server')

        self.assertFalse(FavoriteServersRepository.addFavoriteServer(server_id, 999999))


class PlayerRepositoryTests(RepositoryTestCase):
    def test_create_and_remove_player(self):
        user_id = self._seed_user('player-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())

        self.assertTrue(PlayerRepository.createPlayer(user_id, 'Steve', 'uuid-1'))
        player = db.session.query(Player).filter(Player.user_id == user_id, Player.uuid == 'uuid-1').first()
        self.assertIsNotNone(player)
        self.created_player_ids.add(player.id)

        self.assertTrue(PlayerRepository.removePlayer(user_id, 'uuid-1'))
        self.assertIsNone(db.session.query(Player).filter(Player.user_id == user_id, Player.uuid == 'uuid-1').first())
        self.assertFalse(PlayerRepository.removePlayer(user_id, 'uuid-1'))

    def test_create_player_rejects_missing_user(self):
        self.assertFalse(PlayerRepository.createPlayer(999999, 'Steve', 'uuid-missing'))

    def test_get_all_players_uuids_returns_list_and_empty_list_when_none(self):
        user_id = self._seed_user('player-list-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        self.assertEqual(PlayerRepository.getAllPlayersUUIDs(user_id), [])

        self._seed_player(user_id, 'Steve', 'uuid-1')
        self._seed_player(user_id, 'Alex', 'uuid-2')
        self.assertEqual(sorted(PlayerRepository.getAllPlayersUUIDs(user_id)), ['uuid-1', 'uuid-2'])

    def test_get_player_id_returns_player_id_for_user_and_uuid(self):
        user_id = self._seed_user('player-id-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        player_id = self._seed_player(user_id, 'Steve', 'uuid-1')

        self.assertEqual(PlayerRepository.getPlayerId(user_id, 'uuid-1'), player_id)
        self.assertEqual(PlayerRepository.getPlayerId(user_id, 'missing-uuid'), 0)


class PlayersPrivilegesRepositoryTests(RepositoryTestCase):
    def test_add_player_privilege_creates_row_for_existing_player(self):
        user_id = self._seed_user('priv-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        player_id = self._seed_player(user_id, 'Steve', 'uuid-1')

        self.assertTrue(PlayersPrivilegesRepository.addPrivilege(user_id, 'uuid-1', PlayersPermissions.OP.value))
        privilege = db.session.query(PlayersPrivileges).filter(
            PlayersPrivileges.player_id == player_id,
            PlayersPrivileges.privilege_id == PlayersPermissions.OP.value,
        ).first()
        self.assertIsNotNone(privilege)
        self.created_player_privilege_ids.add(privilege.id)

    def test_add_player_privilege_rejects_missing_player(self):
        user_id = self._seed_user('priv-missing-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())

        self.assertFalse(PlayersPrivilegesRepository.addPrivilege(user_id, 'missing-uuid', PlayersPermissions.OP.value))
        self.assertEqual(db.session.query(PlayersPrivileges).count(), 0)

    def test_delete_player_privilege_removes_existing_row(self):
        user_id = self._seed_user('priv-delete-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        player_id = self._seed_player(user_id, 'Steve', 'uuid-1')
        privilege_id = self._seed_player_privilege(player_id, PlayersPermissions.WhitelistedByDefault.value)

        self.assertTrue(PlayersPrivilegesRepository.deletePrivilege(user_id, 'uuid-1', PlayersPermissions.WhitelistedByDefault.value))
        self.assertIsNone(db.session.query(PlayersPrivileges).filter(PlayersPrivileges.id == privilege_id).first())
        self.assertFalse(PlayersPrivilegesRepository.deletePrivilege(user_id, 'uuid-1', PlayersPermissions.WhitelistedByDefault.value))

    def test_get_player_privileges_returns_privileges_for_existing_player_and_empty_list_for_none(self):
        user_id = self._seed_user('priv-list-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        player_id = self._seed_player(user_id, 'Steve', 'uuid-1')
        self.assertEqual(PlayersPrivilegesRepository.getPlayerPrivileges(user_id, 'uuid-1'), [])

        self._seed_player_privilege(player_id, PlayersPermissions.OP.value)
        self._seed_player_privilege(player_id, PlayersPermissions.WhitelistedByDefault.value)
        privileges = PlayersPrivilegesRepository.getPlayerPrivileges(user_id, 'uuid-1')
        self.assertEqual(sorted([p.privilege_id for p in privileges]), [0, 1])


class SettingsRepositoryTests(RepositoryTestCase):
    def test_add_setting_creates_row_and_rejects_duplicates(self):
        user_id = self._seed_user('settings-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())

        self.assertTrue(SettingsRepository.addSetting(user_id, SettingsPermissions.NotBlank.value, True))
        setting = db.session.query(Settings).filter(Settings.user_id == user_id, Settings.rule == SettingsPermissions.NotBlank.value).first()
        self.assertIsNotNone(setting)
        self.assertTrue(setting.approved)
        self.created_setting_ids.add(setting.id)

        self.assertFalse(SettingsRepository.addSetting(user_id, SettingsPermissions.NotBlank.value, False))

    def test_add_setting_rejects_invalid_rule(self):
        user_id = self._seed_user('settings-invalid-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())

        self.assertFalse(SettingsRepository.addSetting(user_id, 999, True))

    def test_change_setting_updates_approval_flag(self):
        user_id = self._seed_user('settings-change-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        setting_id = self._seed_setting(user_id, SettingsPermissions.NotBlank.value, False)

        self.assertTrue(SettingsRepository.changeSetting(user_id, SettingsPermissions.NotBlank.value, True))
        setting = db.session.query(Settings).filter(Settings.id == setting_id).first()
        self.assertTrue(setting.approved)
        self.assertFalse(SettingsRepository.changeSetting(user_id, 999, True))

    def test_remove_setting_deletes_existing_setting(self):
        user_id = self._seed_user('settings-remove-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        setting_id = self._seed_setting(user_id, SettingsPermissions.NotBlank.value, False)

        self.assertTrue(SettingsRepository.removeSetting(user_id, SettingsPermissions.NotBlank.value))
        self.assertIsNone(db.session.query(Settings).filter(Settings.id == setting_id).first())
        self.assertFalse(SettingsRepository.removeSetting(user_id, SettingsPermissions.NotBlank.value))


class ServersRepositoryTests(RepositoryTestCase):
    def test_add_server_creates_server_and_rejects_missing_user(self):
        owner_id = self._seed_user('server-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())

        self.assertTrue(ServersRepository.addServer(owner_id, 'my-server'))
        server = db.session.query(Servers).filter(Servers.owner_id == owner_id, Servers.name == 'my-server').first()
        self.assertIsNotNone(server)
        self.created_server_ids.add(server.id)

        self.assertFalse(ServersRepository.addServer(999999, 'missing-owner-server'))

    def test_remove_server_deletes_existing_server_and_returns_false_when_missing(self):
        owner_id = self._seed_user('server-remove-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'remove-me')

        self.assertTrue(ServersRepository.removeServer(owner_id, 'remove-me'))
        self.assertIsNone(db.session.query(Servers).filter(Servers.id == server_id).first())
        self.assertFalse(ServersRepository.removeServer(owner_id, 'remove-me'))

    def test_change_server_name_updates_server_and_get_server_id_reflects_change(self):
        owner_id = self._seed_user('server-rename-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'old-name')

        self.assertEqual(ServersRepository.getServerId(owner_id, 'old-name'), server_id)
        self.assertTrue(ServersRepository.changeServerName(owner_id, 'old-name', 'new-name'))
        self.assertEqual(ServersRepository.getServerId(owner_id, 'old-name'), 0)
        self.assertEqual(ServersRepository.getServerId(owner_id, 'new-name'), server_id)

    def test_dose_server_exist_and_get_server_owner(self):
        owner_id = self._seed_user('server-exist-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'exists')

        self.assertTrue(ServersRepository.doesServerExist(server_id))
        self.assertEqual(ServersRepository.getServerOwner(server_id), owner_id)
        self.assertFalse(ServersRepository.doesServerExist(999999))
        self.assertEqual(ServersRepository.getServerOwner(999999), 0)

    def test_get_server_name(self):
        owner_id = self._seed_user('server-name-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'lookup-me')

        self.assertEqual(ServersRepository.getServerName(server_id), 'lookup-me')
        self.assertEqual(ServersRepository.getServerName(999999), '')



class ServersUsersPermsRepositoryTests(RepositoryTestCase):
    def test_add_perm_rejects_if_target_is_owner(self):
        owner_id = self._seed_user('perms-owner-target-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = owner_id
        server_id = self._seed_server(owner_id, 'perm-owner-target-server')
        
        # Another user tries to add perm to owner (even if they have AddPermissionToServer)
        other_user_id = self._seed_user('perms-other', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        self._seed_server_perm(server_id, other_user_id, ServersPermissions.AddPermissionToServer.value)
        
        self.assertFalse(ServersUsersPermsRepository.addPerm(other_user_id, server_id, target_user_id, ServersPermissions.ViewServer.value))

    def test_add_perm_rejects_if_already_exists(self):
        owner_id = self._seed_user('perms-exists-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perms-exists-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-exists-server')
        self._seed_server_perm(server_id, target_user_id, ServersPermissions.ViewServer.value)

        self.assertFalse(ServersUsersPermsRepository.addPerm(owner_id, server_id, target_user_id, ServersPermissions.ViewServer.value))

    def test_add_perm_rejects_if_requester_lacks_permission(self):
        owner_id = self._seed_user('perms-no-grant-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        requester_id = self._seed_user('perms-no-grant-requester', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perms-no-grant-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-no-grant-server')

        # Requester has ViewServer but not AddPermissionToServer
        self._seed_server_perm(server_id, requester_id, ServersPermissions.ViewServer.value)

        self.assertFalse(ServersUsersPermsRepository.addPerm(requester_id, server_id, target_user_id, ServersPermissions.ViewServer.value))

    def test_remove_perm_rejects_if_requester_lacks_permission(self):
        owner_id = self._seed_user('perms-no-rem-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        requester_id = self._seed_user('perms-no-rem-requester', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perms-no-rem-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-no-rem-server')

        self._seed_server_perm(server_id, target_user_id, ServersPermissions.ViewServer.value)
        # Requester has ViewServer but not RemovePermissionFromServer
        self._seed_server_perm(server_id, requester_id, ServersPermissions.ViewServer.value)

        self.assertFalse(ServersUsersPermsRepository.removePerm(requester_id, server_id, target_user_id, ServersPermissions.ViewServer.value))

    def test_dose_user_have_perm_returns_true_for_owner(self):
        owner_id = self._seed_user('perm-owner-check', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-owner-check-server')

        self.assertTrue(ServersUsersPermsRepository.doesUserHavePerm(owner_id, server_id, ServersPermissions.ViewServer.value))
    def test_get_perms_returns_permission_ids_for_user_and_server(self):
        owner_id = self._seed_user('perms-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-server')
        self._seed_server_perm(server_id, owner_id, ServersPermissions.AddPermissionToServer.value)
        self._seed_server_perm(server_id, owner_id, ServersPermissions.RemovePermissionFromServer.value)

        self.assertEqual(
            sorted(ServersUsersPermsRepository.getPerms(owner_id, server_id)),
            [
                ServersPermissions.AddPermissionToServer.value,
                ServersPermissions.RemovePermissionFromServer.value,
            ],
        )
        self.assertEqual(ServersUsersPermsRepository.getPerms(owner_id, 999999), [])

    def test_add_perm_allows_owner_without_add_grant_and_creates_target_permission(self):
        owner_id = self._seed_user('perms-add-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perms-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-add-server')

        self.assertTrue(
            ServersUsersPermsRepository.addPerm(
                owner_id,
                server_id,
                target_user_id,
                ServersPermissions.RemovePermissionFromServer.value,
            )
        )

        perm = db.session.query(ServersUsersPerms).filter(
            ServersUsersPerms.server_id == server_id,
            ServersUsersPerms.user_id == target_user_id,
            ServersUsersPerms.perm_id == ServersPermissions.RemovePermissionFromServer.value,
        ).first()
        self.assertIsNotNone(perm)
        self.created_server_perm_ids.add(perm.id)

    def test_remove_perm_allows_owner_without_remove_grant_and_deletes_target_permission(self):
        owner_id = self._seed_user('perms-remove-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perms-remove-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-remove-server')
        target_perm_id = self._seed_server_perm(server_id, target_user_id, ServersPermissions.AddPermissionToServer.value)

        self.assertTrue(
            ServersUsersPermsRepository.removePerm(
                owner_id,
                server_id,
                target_user_id,
                ServersPermissions.AddPermissionToServer.value,
            )
        )
        self.assertIsNone(db.session.query(ServersUsersPerms).filter(ServersUsersPerms.id == target_perm_id).first())

    def test_add_perm_rejects_invalid_permission_id(self):
        owner_id = self._seed_user('perms-invalid-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perms-invalid-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-invalid-server')
        self._grant_owner_server_permissions(server_id, owner_id)

        self.assertFalse(ServersUsersPermsRepository.addPerm(owner_id, server_id, target_user_id, 999))

    def test_dose_user_have_perm_returns_true_when_user_has_permission(self):
        owner_id = self._seed_user('perm-check-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perm-check-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-check-server')
        self._grant_owner_server_permissions(server_id, owner_id)

        self._seed_server_perm(server_id, target_user_id, ServersPermissions.RemovePermissionFromServer.value)

        self.assertTrue(ServersUsersPermsRepository.doesUserHavePerm(target_user_id, server_id, ServersPermissions.RemovePermissionFromServer.value))

    def test_dose_user_have_perm_returns_false_when_user_does_not_have_permission(self):
        owner_id = self._seed_user('perm-no-check-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perm-no-check-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-no-check-server')

        self.assertFalse(ServersUsersPermsRepository.doesUserHavePerm(target_user_id, server_id, ServersPermissions.RemovePermissionFromServer.value))

    def test_dose_user_have_perm_returns_false_for_missing_user(self):
        owner_id = self._seed_user('perm-missing-user-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-missing-user-server')

        self.assertFalse(ServersUsersPermsRepository.doesUserHavePerm(999999, server_id, ServersPermissions.RemovePermissionFromServer.value))

    def test_dose_user_have_perm_returns_false_for_missing_server(self):
        user_id = self._seed_user('perm-missing-server-user', hashlib.sha256('pw'.encode('utf-8')).hexdigest())

        self.assertFalse(ServersUsersPermsRepository.doesUserHavePerm(user_id, 999999, ServersPermissions.RemovePermissionFromServer.value))

    def test_dose_user_have_perm_returns_false_when_user_has_different_permission(self):
        owner_id = self._seed_user('perm-different-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perm-different-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-different-server')

        self._seed_server_perm(server_id, target_user_id, ServersPermissions.AddPermissionToServer.value)

        self.assertFalse(ServersUsersPermsRepository.doesUserHavePerm(target_user_id, server_id, ServersPermissions.RemovePermissionFromServer.value))
        self.assertTrue(ServersUsersPermsRepository.doesUserHavePerm(target_user_id, server_id, ServersPermissions.AddPermissionToServer.value))

    def test_dose_user_have_perm_with_multiple_permissions(self):
        owner_id = self._seed_user('perm-multi-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perm-multi-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-multi-server')

        self._seed_server_perm(server_id, target_user_id, ServersPermissions.AddPermissionToServer.value)
        self._seed_server_perm(server_id, target_user_id, ServersPermissions.RemovePermissionFromServer.value)

        self.assertTrue(ServersUsersPermsRepository.doesUserHavePerm(target_user_id, server_id, ServersPermissions.AddPermissionToServer.value))
        self.assertTrue(ServersUsersPermsRepository.doesUserHavePerm(target_user_id, server_id, ServersPermissions.RemovePermissionFromServer.value))

    def test_get_servers_with_user_perm_returns_matching_server_ids(self):
        owner_id = self._seed_user('perm-view-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perm-view-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_a = self._seed_server(owner_id, 'perm-view-a')
        server_b = self._seed_server(owner_id, 'perm-view-b')

        self._seed_server_perm(server_a, target_user_id, ServersPermissions.ViewServer.value)
        self._seed_server_perm(server_b, target_user_id, ServersPermissions.ViewServer.value)

        self.assertEqual(
            sorted(ServersUsersPermsRepository.getServersWithUserPerm(target_user_id, ServersPermissions.ViewServer.value)),
            sorted([server_a, server_b]),
        )
        self.assertEqual(ServersUsersPermsRepository.getServersWithUserPerm(target_user_id, 999), [])

    # --- Owner-bypass tests ---

    def test_does_user_have_perm_returns_true_for_owner_without_explicit_row(self):
        """Server owner has implicit access to every permission, even without a DB row."""
        owner_id = self._seed_user('owner-bypass-user', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'owner-bypass-server')

        for perm in ServersPermissions:
            self.assertTrue(
                ServersUsersPermsRepository.doesUserHavePerm(owner_id, server_id, perm.value),
                msg=f"Owner should have implicit access to {perm.name}",
            )

    def test_does_user_have_perm_non_owner_still_requires_explicit_row(self):
        """A non-owner user must have an explicit permission row."""
        owner_id = self._seed_user('owner-explicit-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        non_owner_id = self._seed_user('owner-explicit-non-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'owner-explicit-server')

        self.assertFalse(
            ServersUsersPermsRepository.doesUserHavePerm(non_owner_id, server_id, ServersPermissions.ViewServer.value)
        )

        self._seed_server_perm(server_id, non_owner_id, ServersPermissions.ViewServer.value)
        self.assertTrue(
            ServersUsersPermsRepository.doesUserHavePerm(non_owner_id, server_id, ServersPermissions.ViewServer.value)
        )

    def test_get_servers_with_user_perm_does_not_include_owned_servers_without_explicit_row(self):
        """getServersWithUserPerm only returns servers with an explicit grant row; ownership alone is not enough."""
        owner_id = self._seed_user('gswup-owner-only', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_a = self._seed_server(owner_id, 'gswup-owned-a')
        server_b = self._seed_server(owner_id, 'gswup-owned-b')

        # No explicit ViewServer row — owned servers must NOT appear.
        result = ServersUsersPermsRepository.getServersWithUserPerm(owner_id, ServersPermissions.ViewServer.value)
        self.assertNotIn(server_a, result)
        self.assertNotIn(server_b, result)

    def test_get_servers_with_user_perm_returns_only_explicit_grants(self):
        """When the user has an explicit grant on a server they don't own, only that server is returned."""
        owner_id = self._seed_user('gswup-other-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        user_id = self._seed_user('gswup-granted-user', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        owned_server = self._seed_server(owner_id, 'gswup-other-owned')
        granted_server = self._seed_server(owner_id, 'gswup-granted')

        self._seed_server_perm(granted_server, user_id, ServersPermissions.ViewServer.value)

        result = ServersUsersPermsRepository.getServersWithUserPerm(user_id, ServersPermissions.ViewServer.value)
        self.assertIn(granted_server, result)
        self.assertNotIn(owned_server, result)

