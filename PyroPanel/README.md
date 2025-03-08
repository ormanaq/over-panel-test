# PyroPanel

A Python-based game server management panel similar to Pterodactyl, designed to provide a web interface for managing game servers running in Docker containers.

## Features

- **Web-based Control Panel**: Manage your game servers through an intuitive web interface
- **Docker Integration**: Run game servers in isolated Docker containers
- **Resource Monitoring**: Track CPU, memory, and disk usage of your game servers
- **User Management**: Create users with different permission levels
- **API Access**: RESTful API for programmatic access to your servers
- **Backup System**: Create and restore backups of your game servers
- **File Management**: Browse and edit server files through the web interface
- **Console Access**: Access server console and send commands

## Architecture

PyroPanel consists of two main components:

1. **Web Panel**: A FastAPI-based web application that provides the user interface and API
2. **Daemon**: A Python daemon that runs on each host machine and manages the Docker containers

## Installation

### Prerequisites

- Python 3.8 or higher
- Docker
- PostgreSQL, MySQL, or SQLite

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/pyropanel.git
   cd pyropanel
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up the database:
   ```
   python main.py setup
   ```

4. Create an admin user:
   ```
   python main.py setup --admin-username admin --admin-password yourpassword --admin-email admin@example.com
   ```

5. Start the web panel:
   ```
   python main.py web
   ```

6. Start the daemon (on each host machine):
   ```
   python main.py daemon
   ```

## Configuration

### Web Panel

The web panel can be configured through environment variables or a `.env` file:

- `DATABASE_URL`: Database connection string (default: `sqlite:///./pyropanel.db`)
- `SECRET_KEY`: Secret key for JWT token generation
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DEBUG`: Enable debug mode (default: `False`)

### Daemon

The daemon is configured through the `config/daemon.json` file:

- `api_url`: URL of the web panel API
- `api_key`: API key for authentication
- `update_interval`: Interval for checking for updates (in seconds)
- `backup_dir`: Directory for storing backups
- `log_level`: Logging level

## Development

### Running in Development Mode

```
python main.py web --reload
```

### Database Migrations

```
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
