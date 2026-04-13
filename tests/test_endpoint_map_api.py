import unittest

from api import app


class EndpointMapApiTests(unittest.TestCase):
	def test_openapi_documents_bearer_auth_for_protected_db_routes(self):
		response = app.test_client().get('/openapi.json')
		self.assertEqual(response.status_code, 200)

		spec = response.get_json()
		self.assertIn('securitySchemes', spec['components'])
		self.assertIn('BearerAuth', spec['components']['securitySchemes'])

		favorite_servers_get = spec['paths']['/favoriteServers']['get']
		self.assertEqual(favorite_servers_get.get('security'), [{'BearerAuth': []}])
		self.assertIn('Requires JWT Bearer token', favorite_servers_get.get('description', ''))

		manage_add_server_post = spec['paths']['/manage/addServer']['post']
		self.assertEqual(manage_add_server_post.get('security'), [{'BearerAuth': []}])
		self.assertIn('Requires JWT Bearer token', manage_add_server_post.get('description', ''))

		remove_server_delete = spec['paths']['/servers/{serverName}/uninstall']['delete']
		self.assertEqual(remove_server_delete.get('security'), [{'BearerAuth': []}])
		self.assertIn('Requires JWT Bearer token', remove_server_delete.get('description', ''))

		create_user_post = spec['paths']['/user']['post']
		self.assertNotIn('security', create_user_post)

	def test_current_routes_are_registered(self):
		routes = {}
		for rule in app.url_map.iter_rules():
			routes.setdefault(rule.rule, set()).update(rule.methods)

		expected_routes = {
			'/health': {'GET'},
			'/login': {'POST'},
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



if __name__ == '__main__':
	unittest.main()

