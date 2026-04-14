DOCS = {
    'list_servers': {
        'summary': 'List all discovered servers',
        'description': 'Returns all configured local Minecraft servers.',
        'responses': {
            200: 'List of available servers returned successfully.'
        }
    },
    'get_general_server_info': {
        'summary': 'Get server details by server name',
        'description': 'Returns runtime process details if running, otherwise stored metadata.',
        'responses': {
            200: 'Server details returned successfully.',
            404: 'Server not found.'
        }
    },
    'start_server': {
        'summary': 'Start a server',
        'description': 'Starts a server process and registers its socket listener.',
        'responses': {
            200: 'Server started successfully.',
            400: 'Missing or invalid server server_id.'
        }
    },
    'stop_server': {
        'summary': 'Stop a server',
        'description': 'Stops a running server process for the given server server_id.',
        'responses': {
            200: 'Server stopped successfully.',
            400: 'Missing or invalid server server_id.'
        }
    },
    'get_server_stats': {
        'summary': 'Get server runtime stats',
        'description': 'Returns cached or live resource metrics for a running server, including max memory in MB.',
        'responses': {
            200: 'Server statistics returned successfully.',
            404: 'Server is not running.',
            500: 'Stats retrieval failed.'
        }
    },
    'get_global_stats': {
        'summary': 'Get aggregated runtime stats for all running servers',
        'description': 'Returns combined CPU, memory, capacity, and player metrics for all currently running server sessions.',
        'responses': {
            200: 'Global statistics returned successfully.',
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
        'description': 'Requires JWT Bearer token. Uninstalls and removes the selected server from local storage and unregisters it for the authenticated user.',
        'security': [{'BearerAuth': []}],
        'responses': {
            200: 'Server uninstalled and removed successfully.',
            400: 'Missing server server name or uninstall failed.',
            401: 'Missing or invalid JWT token.',
            422: 'JWT token is malformed or cannot be processed.',
            404: 'Server uninstall succeeded but database record could not be removed.'
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
        'description': 'Validates a `user_id` and password pair and returns a JWT access token on success.',
        'responses': {
            200: 'Access token returned successfully.',
            400: 'Missing `user_id` or password.',
            401: 'Invalid credentials.'
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
    }
}

