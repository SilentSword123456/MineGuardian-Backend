DOCS = {
    'list_servers': {
        'summary': 'List all discovered servers',
        'description': 'Returns all configured local Minecraft servers.',
        'responses': {
            200: 'List of available servers returned successfully.'
        }
    },
    'get_general_server_info': {
        'summary': 'Get server details by server_id',
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
        'description': 'Installs a server using the provided software and version settings.',
        'responses': {
            200: 'Server installation request completed.',
            400: 'Required fields are missing.'
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
        'description': 'Uninstalls and removes the selected server from local storage.',
        'responses': {
            200: 'Server uninstall request completed.',
            400: 'Missing server server_id.'
        }
    },
    'create_user': {
        'summary': 'Create a user',
        'description': 'Creates a new database user record.',
        'responses': {
            200: 'User created successfully.',
            400: 'Bad request.'
        }
    },
    'remove_user': {
        'summary': 'Remove a user',
        'description': 'Removes a database user record by username.',
        'responses': {
            200: 'User removed successfully.',
            400: 'Bad request.'
        }
    },
    'add_favorite_server': {
        'summary': 'Add a favorite server',
        'description': 'Adds a server_id to the specified username favorites.',
        'responses': {
            200: 'Favorite server added successfully.',
            400: 'Bad request.'
        }
    },
    'remove_favorite_server': {
        'summary': 'Remove a favorite server',
        'description': 'Removes a server_id from the specified username favorites.',
        'responses': {
            200: 'Favorite server removed successfully.',
            400: 'Bad request.'
        }
    },
    'get_favorite_servers': {
        'summary': 'List favorite servers',
        'description': 'Returns the favorite server ids for a username.',
        'responses': {
            200: 'Favorite servers returned successfully.',
            400: 'Bad request.'
        }
    },
    'add_player': {
        'summary': 'Add a player',
        'description': 'Creates a player record for the specified username.',
        'responses': {
            200: 'Player created successfully.',
            400: 'Bad request.'
        }
    },
    'remove_player': {
        'summary': 'Remove a player',
        'description': 'Removes a player record by username and uuid.',
        'responses': {
            200: 'Player removed successfully.',
            400: 'Bad request.'
        }
    },
    'get_all_players_uuids': {
        'summary': 'List player UUIDs',
        'description': 'Returns the UUIDs for all players linked to a username.',
        'responses': {
            200: 'Player UUIDs returned successfully.',
            400: 'Bad request.'
        }
    },
    'add_player_privilege': {
        'summary': 'Add a player privilege',
        'description': 'Adds a privilege to a player specified by username and player_uuid.',
        'responses': {
            200: 'Player privilege added successfully.',
            400: 'Bad request.'
        }
    },
    'delete_player_privilege': {
        'summary': 'Delete a player privilege',
        'description': 'Removes a privilege from a player specified by username and player_uuid.',
        'responses': {
            200: 'Player privilege removed successfully.',
            400: 'Bad request.'
        }
    },
    'get_player_privileges': {
        'summary': 'List player privileges',
        'description': 'Returns the privileges assigned to a player specified by username and player_uuid.',
        'responses': {
            200: 'Player privileges returned successfully.',
            400: 'Bad request.'
        }
    },
    'add_setting': {
        'summary': 'Add a setting',
        'description': 'Creates a setting rule for a username.',
        'responses': {
            200: 'Setting created successfully.',
            400: 'Bad request.'
        }
    },
    'remove_setting': {
        'summary': 'Remove a setting',
        'description': 'Removes a setting rule for a username.',
        'responses': {
            200: 'Setting removed successfully.',
            400: 'Bad request.'
        }
    },
    'change_setting': {
        'summary': 'Change a setting',
        'description': 'Updates the approval state of a setting rule for a username.',
        'responses': {
            200: 'Setting updated successfully.',
            400: 'Bad request.'
        }
    }
}

