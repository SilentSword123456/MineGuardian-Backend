DOCS = {
    'list_servers': {
        'summary': 'List all discovered servers',
        'description': 'Returns all configured local Minecraft servers.',
        'responses': {
            200: 'List of available servers returned successfully.'
        }
    },
    'get_general_server_info': {
        'summary': 'Get server details by name',
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
            400: 'Missing or invalid server name.'
        }
    },
    'stop_server': {
        'summary': 'Stop a server',
        'description': 'Stops a running server process for the given server name.',
        'responses': {
            200: 'Server stopped successfully.',
            400: 'Missing or invalid server name.'
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
            400: 'Missing server name.'
        }
    }
}

