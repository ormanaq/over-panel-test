# PyroPanel

A Python-based game server management panel inspired by Pterodactyl.

## Features

- Web-based control panel for game server management
- Server daemon for monitoring and controlling game servers
- Docker integration for game server isolation
- User authentication and permission system
- File management with SFTP support
- Automated tasks and scheduling

## Components

1. **Web Panel**
   - FastAPI backend
   - Jinja2 templates for frontend
   - SQLAlchemy ORM for database operations

2. **Server Daemon**
   - Python-based daemon for server management
   - Docker integration for container management
   - Resource monitoring (CPU, RAM, disk usage)

3. **Authentication System**
   - JWT-based authentication
   - Role-based access control

4. **File Management**
   - SFTP support via Paramiko
   - Web-based file editor

5. **Task Scheduling**
   - Celery for task queue management
   - Redis as message broker

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/PyroPanel.git
cd PyroPanel

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up the database
alembic upgrade head

# Start the web panel
uvicorn app.main:app --reload

# Start the daemon (in a separate terminal)
python daemon/daemon.py
```

## Configuration

Edit the `config/config.py` file to configure your installation.

## License

MIT
