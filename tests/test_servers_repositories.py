import hashlib
import os
import tempfile
import unittest

from flask import Flask

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
        expected_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

        self.assertTrue(UserRepository.createUser(username, password))
        users = db.session.query(User).filter(User.username == username).all()
        self._track_ids(self.created_user_ids, users)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].password, expected_hash)

        self.assertFalse(UserRepository.createUser(username, password))
        users = db.session.query(User).filter(User.username == username).all()
        self._track_ids(self.created_user_ids, users)
        self.assertEqual(len(users), 1)

    def test_verify_accepts_correct_password_and_rejects_wrong_password(self):
        username = 'bob'
        password = 'hunter2'
        self._seed_user(username, hashlib.sha256(password.encode('utf-8')).hexdigest())

        self.assertTrue(UserRepository.verify(username, password))
        self.assertFalse(UserRepository.verify(username, 'wrong-password'))

    def test_get_user_id_returns_id_for_existing_username(self):
        username = 'charlie'
        user_id = self._seed_user(username, hashlib.sha256('pw'.encode('utf-8')).hexdigest())

        self.assertEqual(UserRepository.getUserId(username), user_id)
        self.assertEqual(UserRepository.getUserId('missing-user'), 0)

    def test_get_username_returns_username_for_existing_id(self):
        user_id = self._seed_user('dora', hashlib.sha256('pw'.encode('utf-8')).hexdigest())

        self.assertEqual(UserRepository.getUsername(user_id), 'dora')
        self.assertEqual(UserRepository.getUsername(999999), '')

    def test_remove_user_deletes_existing_user_and_returns_false_when_missing(self):
        self._seed_user('eve', hashlib.sha256('pw'.encode('utf-8')).hexdigest())

        self.assertTrue(UserRepository.removeUser('eve'))
        self.assertEqual(db.session.query(User).filter(User.username == 'eve').count(), 0)
        self.assertFalse(UserRepository.removeUser('eve'))

    def test_dose_user_exist_uses_numeric_id(self):
        user_id = self._seed_user('frank', hashlib.sha256('pw'.encode('utf-8')).hexdigest())

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

        self.assertTrue(ServersRepository.doseServerExist(server_id))
        self.assertEqual(ServersRepository.getServerOwner(server_id), owner_id)
        self.assertFalse(ServersRepository.doseServerExist(999999))
        self.assertEqual(ServersRepository.getServerOwner(999999), 0)


class ServersUsersPermsRepositoryTests(RepositoryTestCase):
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

    def test_add_perm_requires_owner_add_grant_and_creates_target_permission(self):
        owner_id = self._seed_user('perms-add-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perms-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-add-server')

        self.assertFalse(
            ServersUsersPermsRepository.addPerm(
                owner_id,
                server_id,
                target_user_id,
                ServersPermissions.RemovePermissionFromServer.value,
            )
        )

        self._grant_owner_server_permissions(server_id, owner_id)
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

    def test_remove_perm_requires_owner_remove_grant_and_deletes_target_permission(self):
        owner_id = self._seed_user('perms-remove-owner', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        target_user_id = self._seed_user('perms-remove-target', hashlib.sha256('pw'.encode('utf-8')).hexdigest())
        server_id = self._seed_server(owner_id, 'perm-remove-server')
        target_perm_id = self._seed_server_perm(server_id, target_user_id, ServersPermissions.AddPermissionToServer.value)

        self.assertFalse(
            ServersUsersPermsRepository.removePerm(
                owner_id,
                server_id,
                target_user_id,
                ServersPermissions.AddPermissionToServer.value,
            )
        )

        self._grant_owner_server_permissions(server_id, owner_id)
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


if __name__ == '__main__':
    unittest.main()

