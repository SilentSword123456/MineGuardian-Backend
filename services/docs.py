DOCS = {
    'list_servers': {
        'summary': 'List visible servers for the authenticated user',
        'description': 'Requires JWT Bearer token. Returns server records where the user has ViewServer permission.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'List of available servers returned successfully.',
            401: 'Missing or invalid JWT token.'
        }
    },
    'get_general_server_info': {
        'summary': 'Get server details by server ID',
        'description': 'Requires JWT Bearer token. Path parameter `serverId` must be an integer. Returns runtime process details if running, otherwise stored metadata.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Server details returned successfully.',
            400: 'Invalid serverId.',
            403: 'User lacks GetServerInfo permission.',
            404: 'Server not found.'
        }
    },
    'start_server': {
        'summary': 'Start a server',
        'description': 'Requires JWT Bearer token and StartServer permission. Path parameter `serverId` must be an integer. Starts a server process and registers its socket listener.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Server started successfully.',
            400: 'Invalid serverId or server cannot be started (already running).',
            403: 'User lacks StartServer permission.',
            404: 'Server not found.'
        }
    },
    'stop_server': {
        'summary': 'Stop a server',
        'description': 'Requires JWT Bearer token and StopServer permission. Path parameter `serverId` must be an integer. Stops a running server process for the given server ID.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Server stopped successfully.',
            400: 'Invalid serverId or server cannot be stopped (no instance found).',
            403: 'User lacks StopServer permission.',
            404: 'Server not found.'
        }
    },
    'get_server_stats': {
        'summary': 'Get server runtime stats',
        'description': 'Requires JWT Bearer token and GetServerInfo permission. Path parameter `serverId` must be an integer. Returns cached or live resource metrics for a running server, including max memory in MB.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Server statistics returned successfully.',
            400: 'Invalid serverId.',
            403: 'User lacks GetServerInfo permission.',
            404: 'Server is not running.',
            500: 'Stats retrieval failed.'
        }
    },
    'get_global_stats': {
        'summary': 'Get aggregated runtime stats for all running servers',
        'description': 'Requires JWT Bearer token. Returns combined CPU, memory, capacity, and player metrics only for running sessions where the user has ViewServer permission.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Global statistics returned successfully.',
            401: 'Missing or invalid JWT token.',
            500: 'Global stats retrieval failed.'
        }
    },
    'add_server': {
        'summary': 'Install and register a server',
        'description': 'Requires JWT Bearer token. Installs a server using the provided software and version settings, then registers it in the database for the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Server installed and registered successfully.',
            400: 'Required fields are missing or installation failed.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.',
            500: 'Server was installed but database registration failed.'
        }
    },
    'get_available_versions': {
        'summary': 'List installable versions for software',
        'description': 'Returns available versions for the selected software source.',
        'responses': {
            200: 'Available versions returned successfully.',
            400: 'Software source is invalid or unavailable.'
        }
    },
    'remove_server': {
        'summary': 'Uninstall a server',
        'description': 'Requires JWT Bearer token and UninstallServer permission. Path parameter `serverId` must be an integer. Uninstalls the selected server and removes its record for the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Server uninstalled and removed successfully.',
            400: 'Invalid serverId or uninstall failed.',
            401: 'Missing or invalid JWT token.',
            403: 'User lacks UninstallServer permission.',
            404: 'Server not found or database record could not be removed.'
        }
    },
    'create_user': {
        'summary': 'Create a user',
        'description': 'Creates a new database user record from a `username` and password payload.',
        'responses': {
            200: 'User created successfully.',
            400: 'Bad request.'
        }
    },
    'remove_user': {
        'summary': 'Remove a user',
        'description': 'Requires JWT Bearer token. Removes the authenticated user record. The request `username` must match the authenticated account username.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'User removed successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.',
            403: 'Forbidden when the authenticated account does not match the provided `username`.'
        }
    },
    'login': {
        'summary': 'Authenticate a user',
        'description': 'Validates a `user_id` and password pair and sets the JWT access token in an `accessToken` HttpOnly cookie on success.',
        'responses': {
            200: 'Authentication successful. JWT is returned in `Set-Cookie: accessToken=...`.',
            400: 'Missing `user_id` or password.',
            401: 'Invalid credentials.'
        }
    },
    'is_session_valid': {
        'summary': 'Validate the current JWT session',
        'description': 'Requires JWT Bearer token in the `accessToken` cookie. Returns `status=true` when the token identity maps to an existing user, otherwise returns `status=false` with 401.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Session is valid for an existing user.',
            401: 'Missing/invalid token or token identity no longer maps to an existing user.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'add_favorite_server': {
        'summary': 'Add a favorite server',
        'description': 'Requires JWT Bearer token. Adds a server_id to the authenticated user favorites.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Favorite server added successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'remove_favorite_server': {
        'summary': 'Remove a favorite server',
        'description': 'Requires JWT Bearer token. Removes a server_id from the authenticated user favorites.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Favorite server removed successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'get_favorite_servers': {
        'summary': 'List favorite servers',
        'description': 'Requires JWT Bearer token. Returns favorite server ids for the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Favorite servers returned successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'add_player': {
        'summary': 'Add a player',
        'description': 'Requires JWT Bearer token. Creates a player record for the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Player created successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'remove_player': {
        'summary': 'Remove a player',
        'description': 'Requires JWT Bearer token. Removes a player record for the authenticated user by uuid.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Player removed successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'get_all_players_uuids': {
        'summary': 'List player UUIDs',
        'description': 'Requires JWT Bearer token. Returns UUIDs for all players linked to the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Player UUIDs returned successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'add_player_privilege': {
        'summary': 'Add a player privilege',
        'description': 'Requires JWT Bearer token. Adds a privilege to a player_uuid owned by the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Player privilege added successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'delete_player_privilege': {
        'summary': 'Delete a player privilege',
        'description': 'Requires JWT Bearer token. Removes a privilege from a player_uuid owned by the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Player privilege removed successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'get_player_privileges': {
        'summary': 'List player privileges',
        'description': 'Requires JWT Bearer token. Returns privileges for a player_uuid linked to the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Player privileges returned successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'add_setting': {
        'summary': 'Add a setting',
        'description': 'Requires JWT Bearer token. Creates a setting rule for the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Setting created successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'remove_setting': {
        'summary': 'Remove a setting',
        'description': 'Requires JWT Bearer token. Removes a setting rule for the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Setting removed successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'change_setting': {
        'summary': 'Change a setting',
        'description': 'Requires JWT Bearer token. Updates the approval state of a setting rule for the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Setting updated successfully.',
            400: 'Bad request.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'add_user_permission_for_server': {
        'summary': 'Add a user permission for a server',
        'description': 'Requires JWT Bearer token and AddPermissionToServer permission. Grants a permission on a server to a target user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'User permission added successfully.',
            400: 'Bad request or missing/invalid parameters.',
            401: 'Unauthorized - missing/invalid JWT token or insufficient permissions to add the requested permission.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'remove_user_permission_for_server': {
        'summary': 'Remove a user permission for a server',
        'description': 'Requires JWT Bearer token and RemovePermissionFromServer permission. Revokes a permission on a server from a target user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'User permission removed successfully.',
            400: 'Bad request or missing/invalid parameters.',
            401: 'Unauthorized - missing/invalid JWT token or insufficient permissions to remove the requested permission.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    },
    'get_default_servers_permissions': {
        'summary': 'Get default server permissions',
        'description': 'Returns a mapping of permission names to their integer values.',
        'responses': {
            200: 'Default server permissions returned successfully.'
        }
    },
    'get_users_with_perms_on_server': {
        'summary': 'Get all users with permissions on a server',
        'description': 'Requires JWT Bearer token and ViewServer permission (or server ownership). Path parameter `serverId` must be an integer. Returns a dictionary mapping user IDs to their assigned permissions for the specified server.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'User permissions dictionary returned successfully.',
            400: 'Invalid serverId.',
            401: 'Missing or invalid JWT token or unauthorized to view permissions.',
            422: 'JWT token is malformed or cannot be processed.'
        }
    }
}

