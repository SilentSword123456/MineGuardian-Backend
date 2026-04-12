import unittest

from api import app


class EndpointMapApiTests(unittest.TestCase):
	def test_current_routes_are_registered(self):
		routes = {}
		for rule in app.url_map.iter_rules():
			routes.setdefault(rule.rule, set()).update(rule.methods)

		expected_routes = {
			'/health': {'GET'},
			'/servers': {'GET'},
			'/servers/<serverName>': {'GET'},
			'/servers/<serverName>/start': {'POST'},
			'/servers/<serverName>/stop': {'POST'},
			'/servers/<serverName>/stats': {'GET'},
			'/servers/<serverName>/uninstall': {'DELETE'},
			'/servers/globalStats': {'GET'},
			'/manage/addServer': {'POST'},
			'/manage/<software>/getAvailableVersions': {'GET'},
			'/user': {'POST', 'DELETE'},
			'/favoriteServers': {'GET', 'POST', 'DELETE'},
			'/player': {'GET', 'POST', 'DELETE'},
			'/playerPrivilege': {'GET', 'POST', 'DELETE'},
			'/setting': {'POST', 'DELETE', 'PATCH'},
		}

		for path, methods in expected_routes.items():
			self.assertIn(path, routes)
			self.assertTrue(methods.issubset(routes[path]))

		self.assertNotIn('/servers/<serverName>/files/tree', routes)


if __name__ == '__main__':
	unittest.main()

