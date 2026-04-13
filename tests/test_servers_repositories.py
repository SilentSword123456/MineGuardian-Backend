import os
import tempfile
import unittest

from flask import Flask

from Database.database import Servers, ServersUsersPerms, User, db
from Database.perms import ServersPermissions
from Database.repositories import ServersRepository, ServersUsersPermsRepository


class ServersRepositoriesTests(unittest.TestCase):
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

        self.created_user_ids = []
        self.created_server_ids = []
        self.created_perm_ids = []

    def tearDown(self):
        db.session.rollback()

        if self.created_perm_ids:
            db.session.query(ServersUsersPerms).filter(ServersUsersPerms.id.in_(self.created_perm_ids)).delete(
                synchronize_session=False
            )

        if self.created_server_ids:
            db.session.query(ServersUsersPerms).filter(ServersUsersPerms.server_id.in_(self.created_server_ids)).delete(
                synchronize_session=False
            )
            db.session.query(Servers).filter(Servers.id.in_(self.created_server_ids)).delete(synchronize_session=False)

        if self.created_user_ids:
            db.session.query(ServersUsersPerms).filter(ServersUsersPerms.user_id.in_(self.created_user_ids)).delete(
                synchronize_session=False
            )
            db.session.query(User).filter(User.id.in_(self.created_user_ids)).delete(synchronize_session=False)

        db.session.commit()
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()

        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _create_user(self, username):
        user = User(username=username, password='hash')
        db.session.add(user)
        db.session.commit()
        self.created_user_ids.append(user.id)
        return user.id

    def _create_server(self, owner_id, name):
        server = Servers(owner_id=owner_id, name=name)
        db.session.add(server)
        db.session.commit()
        self.created_server_ids.append(server.id)
        return server.id

    def _create_perm(self, server_id, user_id, perm_id):
        perm = ServersUsersPerms(server_id=server_id, user_id=user_id, perm_id=perm_id)
        db.session.add(perm)
        db.session.commit()
        self.created_perm_ids.append(perm.id)
        return perm.id

    def _grant_owner_perms(self, server_id, owner_id):
        self._create_perm(server_id, owner_id, ServersPermissions.AddPermissionToServer.value)
        self._create_perm(server_id, owner_id, ServersPermissions.RemovePermissionFromServer.value)

    def test_add_server_creates_server_for_existing_user(self):
        owner_id = self._create_user('owner_add_server')

        added = ServersRepository.addServer(owner_id, 'repo-add-server')

        self.assertTrue(added)
        server = db.session.query(Servers).filter(Servers.owner_id == owner_id, Servers.name == 'repo-add-server').first()
        self.assertIsNotNone(server)
        self.created_server_ids.append(server.id)

    def test_add_server_returns_false_for_unknown_user(self):
        added = ServersRepository.addServer(999999, 'repo-add-server')

        self.assertFalse(added)

    def test_remove_server_deletes_existing_server(self):
        owner_id = self._create_user('owner_remove_server')
        server_id = self._create_server(owner_id, 'repo-remove-server')

        removed = ServersRepository.removeServer(owner_id, 'repo-remove-server')

        self.assertTrue(removed)
        server = db.session.query(Servers).filter(Servers.id == server_id).first()
        self.assertIsNone(server)

    def test_remove_server_returns_false_when_missing(self):
        owner_id = self._create_user('owner_remove_missing')

        removed = ServersRepository.removeServer(owner_id, 'missing-server')

        self.assertFalse(removed)

    def test_dose_server_exist_and_get_server_owner(self):
        owner_id = self._create_user('owner_exist')
        server_id = self._create_server(owner_id, 'existing-server')

        self.assertTrue(ServersRepository.doseServerExist(server_id))
        self.assertEqual(ServersRepository.getServerOwner(server_id), owner_id)

        self.assertFalse(ServersRepository.doseServerExist(999999))
        self.assertEqual(ServersRepository.getServerOwner(999999), 0)

    def test_get_perms_returns_all_user_permissions_for_server(self):
        owner_id = self._create_user('owner_get_perms')
        server_id = self._create_server(owner_id, 'repo-get-perms')
        self._create_perm(server_id, owner_id, ServersPermissions.AddPermissionToServer.value)
        self._create_perm(server_id, owner_id, ServersPermissions.RemovePermissionFromServer.value)

        perms = ServersUsersPermsRepository.getPerms(owner_id, server_id)

        self.assertEqual(
            sorted(perms),
            sorted([
                ServersPermissions.AddPermissionToServer.value,
                ServersPermissions.RemovePermissionFromServer.value,
            ]),
        )

    def test_add_perm_requires_owner_add_permission_then_creates_perm(self):
        owner_id = self._create_user('owner_add_perm')
        target_user_id = self._create_user('target_add_perm')
        server_id = self._create_server(owner_id, 'repo-add-perm')

        denied = ServersUsersPermsRepository.addPerm(
            owner_id,
            server_id,
            target_user_id,
            ServersPermissions.RemovePermissionFromServer.value,
        )
        self.assertFalse(denied)

        self._grant_owner_perms(server_id, owner_id)

        added = ServersUsersPermsRepository.addPerm(
            owner_id,
            server_id,
            target_user_id,
            ServersPermissions.RemovePermissionFromServer.value,
        )

        self.assertTrue(added)
        added_perm = db.session.query(ServersUsersPerms).filter(
            ServersUsersPerms.server_id == server_id,
            ServersUsersPerms.user_id == target_user_id,
            ServersUsersPerms.perm_id == ServersPermissions.RemovePermissionFromServer.value,
        ).first()
        self.assertIsNotNone(added_perm)
        self.created_perm_ids.append(added_perm.id)

    def test_add_perm_rejects_invalid_permission_id(self):
        owner_id = self._create_user('owner_add_perm_invalid')
        target_user_id = self._create_user('target_add_perm_invalid')
        server_id = self._create_server(owner_id, 'repo-add-perm-invalid')
        self._grant_owner_perms(server_id, owner_id)

        added = ServersUsersPermsRepository.addPerm(owner_id, server_id, target_user_id, 999)

        self.assertFalse(added)

    def test_remove_perm_requires_owner_remove_permission_then_deletes_perm(self):
        owner_id = self._create_user('owner_remove_perm')
        target_user_id = self._create_user('target_remove_perm')
        server_id = self._create_server(owner_id, 'repo-remove-perm')
        self._create_perm(server_id, target_user_id, ServersPermissions.AddPermissionToServer.value)

        denied = ServersUsersPermsRepository.removePerm(
            owner_id,
            server_id,
            target_user_id,
            ServersPermissions.AddPermissionToServer.value,
        )
        self.assertFalse(denied)

        self._grant_owner_perms(server_id, owner_id)

        removed = ServersUsersPermsRepository.removePerm(
            owner_id,
            server_id,
            target_user_id,
            ServersPermissions.AddPermissionToServer.value,
        )
        self.assertTrue(removed)
        perm = db.session.query(ServersUsersPerms).filter(
            ServersUsersPerms.server_id == server_id,
            ServersUsersPerms.user_id == target_user_id,
            ServersUsersPerms.perm_id == ServersPermissions.AddPermissionToServer.value,
        ).first()
        self.assertIsNone(perm)


if __name__ == '__main__':
    unittest.main()



