#!/usr/bin/env python3
import asyncio
import docker
import json
import logging
import os
import signal
import sys
import time
from typing import Dict, List, Optional
import requests
from datetime import datetime, timedelta
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("daemon.log")
    ]
)
logger = logging.getLogger("PyroPanel-Daemon")

class PyroServerDaemon:
    """
    PyroPanel Server Daemon
    
    Manages game servers running in Docker containers:
    - Monitors server resources
    - Starts/stops/restarts servers
    - Collects logs
    - Manages backups
    """
    
    def __init__(self, config_path: str = "config/daemon.json"):
        """Initialize the daemon"""
        self.config = self._load_config(config_path)
        self.docker_client = docker.from_env()
        self.servers: Dict[int, Dict] = {}  # Server ID -> Server info
        self.running = True
        self.api_base_url = self.config.get("api_url", "http://localhost:8000")
        self.api_key = self.config.get("api_key", "")
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)
        
        logger.info("PyroPanel Daemon initialized")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load daemon configuration from file"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file {config_path} not found, using defaults")
                return {
                    "api_url": "http://localhost:8000",
                    "api_key": "",
                    "update_interval": 10,
                    "backup_dir": "backups",
                    "log_level": "INFO"
                }
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def _handle_exit(self, signum, frame):
        """Handle exit signals"""
        logger.info("Shutdown signal received, stopping daemon...")
        self.running = False
    
    async def _fetch_servers(self) -> List[Dict]:
        """Fetch server list from API"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.api_base_url}/api/servers", headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch servers: {response.status_code} {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error fetching servers: {e}")
            return []
    
    async def _update_server_status(self, server_id: int, status: str, container_id: Optional[str] = None):
        """Update server status in API"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"status": status}
            
            if container_id is not None:
                data["container_id"] = container_id
            
            response = requests.put(
                f"{self.api_base_url}/api/servers/{server_id}/status", 
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to update server status: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"Error updating server status: {e}")
    
    async def _collect_server_stats(self, server_id: int, container_id: str):
        """Collect server resource usage stats"""
        try:
            container = self.docker_client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Calculate CPU usage
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                        stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            cpu_usage = (cpu_delta / system_delta) * 100.0
            
            # Calculate memory usage
            memory_usage = stats["memory_stats"]["usage"]
            
            # Get uptime
            container_info = container.attrs
            started_at = datetime.fromisoformat(container_info["State"]["StartedAt"].replace("Z", "+00:00"))
            uptime = (datetime.now() - started_at).total_seconds()
            
            # Send stats to API
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "uptime": uptime
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/servers/{server_id}/stats", 
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to send server stats: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"Error collecting server stats: {e}")
    
    async def start_server(self, server_id: int, server_info: Dict):
        """Start a game server container"""
        try:
            # Check if container already exists
            container_id = server_info.get("container_id")
            if container_id:
                try:
                    container = self.docker_client.containers.get(container_id)
                    if container.status != "running":
                        logger.info(f"Starting existing container for server {server_id}")
                        container.start()
                    else:
                        logger.info(f"Container for server {server_id} is already running")
                    
                    await self._update_server_status(server_id, "running", container_id)
                    return
                except docker.errors.NotFound:
                    logger.info(f"Container {container_id} not found, creating new container")
            
            # Create and start new container
            logger.info(f"Creating new container for server {server_id}")
            
            # Prepare environment variables
            env_vars = {}
            for var in server_info.get("variables", []):
                env_vars[var["key"]] = var["value"]
            
            # Prepare port mapping
            ports = {f"{server_info['port']}/tcp": server_info['port']}
            
            # Create container
            container = self.docker_client.containers.run(
                server_info["image"],
                detach=True,
                environment=env_vars,
                ports=ports,
                name=f"pyropanel-server-{server_id}",
                mem_limit=f"{server_info['memory_limit']}m",
                cpu_quota=int(server_info['cpu_limit'] * 100000),
                restart_policy={"Name": "unless-stopped"}
            )
            
            # Update server status
            await self._update_server_status(server_id, "running", container.id)
            logger.info(f"Server {server_id} started with container {container.id}")
        except Exception as e:
            logger.error(f"Error starting server {server_id}: {e}")
            await self._update_server_status(server_id, "error")
    
    async def stop_server(self, server_id: int, server_info: Dict):
        """Stop a game server container"""
        try:
            container_id = server_info.get("container_id")
            if not container_id:
                logger.warning(f"No container ID for server {server_id}")
                return
            
            try:
                container = self.docker_client.containers.get(container_id)
                if container.status == "running":
                    logger.info(f"Stopping container for server {server_id}")
                    container.stop(timeout=30)  # Give 30 seconds for graceful shutdown
                else:
                    logger.info(f"Container for server {server_id} is already stopped")
                
                await self._update_server_status(server_id, "stopped", container_id)
            except docker.errors.NotFound:
                logger.warning(f"Container {container_id} not found")
                await self._update_server_status(server_id, "stopped", None)
        except Exception as e:
            logger.error(f"Error stopping server {server_id}: {e}")
    
    async def restart_server(self, server_id: int, server_info: Dict):
        """Restart a game server container"""
        try:
            container_id = server_info.get("container_id")
            if not container_id:
                logger.warning(f"No container ID for server {server_id}, starting new container")
                await self.start_server(server_id, server_info)
                return
            
            try:
                container = self.docker_client.containers.get(container_id)
                logger.info(f"Restarting container for server {server_id}")
                container.restart(timeout=30)  # Give 30 seconds for graceful shutdown
                await self._update_server_status(server_id, "running", container_id)
            except docker.errors.NotFound:
                logger.warning(f"Container {container_id} not found, starting new container")
                await self.start_server(server_id, server_info)
        except Exception as e:
            logger.error(f"Error restarting server {server_id}: {e}")
            await self._update_server_status(server_id, "error")
    
    async def create_backup(self, server_id: int, server_info: Dict):
        """Create a backup of the game server data"""
        try:
            container_id = server_info.get("container_id")
            if not container_id:
                logger.warning(f"No container ID for server {server_id}")
                return None
            
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(self.config.get("backup_dir", "backups"), str(server_id))
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{server_info['name']}_{timestamp}.tar.gz"
            backup_path = os.path.join(backup_dir, backup_name)
            
            # Create backup
            logger.info(f"Creating backup for server {server_id}")
            container = self.docker_client.containers.get(container_id)
            
            # Get container info to find volumes
            container_info = container.attrs
            mounts = container_info.get("Mounts", [])
            
            if not mounts:
                logger.warning(f"No volumes found for server {server_id}")
                return None
            
            # Create tar archive of volume data
            import tarfile
            with tarfile.open(backup_path, "w:gz") as tar:
                for mount in mounts:
                    if mount["Type"] == "volume":
                        volume_name = mount["Name"]
                        dest_path = mount["Destination"]
                        
                        # Add volume data to tar archive
                        tar.add(f"/var/lib/docker/volumes/{volume_name}/_data", arcname=dest_path)
            
            # Get backup size
            backup_size = os.path.getsize(backup_path)
            
            # Register backup in API
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {
                "name": backup_name,
                "path": backup_path,
                "size": backup_size
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/servers/{server_id}/backups", 
                headers=headers,
                json=data
            )
            
            if response.status_code != 201:
                logger.error(f"Failed to register backup: {response.status_code} {response.text}")
            
            logger.info(f"Backup created for server {server_id}: {backup_path} ({backup_size} bytes)")
            return backup_path
        except Exception as e:
            logger.error(f"Error creating backup for server {server_id}: {e}")
            return None
    
    async def check_pending_actions(self):
        """Check for pending server actions"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.api_base_url}/api/actions/pending", headers=headers)
            
            if response.status_code == 200:
                actions = response.json()
                
                for action in actions:
                    server_id = action["server_id"]
                    action_type = action["action"]
                    
                    if server_id in self.servers:
                        server_info = self.servers[server_id]
                        
                        if action_type == "start":
                            await self.start_server(server_id, server_info)
                        elif action_type == "stop":
                            await self.stop_server(server_id, server_info)
                        elif action_type == "restart":
                            await self.restart_server(server_id, server_info)
                        elif action_type == "backup":
                            await self.create_backup(server_id, server_info)
                        else:
                            logger.warning(f"Unknown action type: {action_type}")
                        
                        # Mark action as completed
                        requests.put(
                            f"{self.api_base_url}/api/actions/{action['id']}/complete", 
                            headers=headers
                        )
        except Exception as e:
            logger.error(f"Error checking pending actions: {e}")
    
    async def monitor_servers(self):
        """Monitor running servers and collect stats"""
        for server_id, server_info in self.servers.items():
            if server_info.get("status") == "running" and server_info.get("container_id"):
                try:
                    container = self.docker_client.containers.get(server_info["container_id"])
                    if container.status == "running":
                        await self._collect_server_stats(server_id, server_info["container_id"])
                    else:
                        logger.warning(f"Container for server {server_id} is not running: {container.status}")
                        await self._update_server_status(server_id, container.status, server_info["container_id"])
                except docker.errors.NotFound:
                    logger.warning(f"Container {server_info['container_id']} for server {server_id} not found")
                    await self._update_server_status(server_id, "error", None)
                except Exception as e:
                    logger.error(f"Error monitoring server {server_id}: {e}")
    
    async def collect_system_stats(self):
        """Collect system-wide resource usage stats"""
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_used = memory.used
            memory_total = memory.total
            memory_percent = memory.percent
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_used = disk.used
            disk_total = disk.total
            disk_percent = disk.percent
            
            # Send stats to API
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {
                "cpu_percent": cpu_percent,
                "memory_used": memory_used,
                "memory_total": memory_total,
                "memory_percent": memory_percent,
                "disk_used": disk_used,
                "disk_total": disk_total,
                "disk_percent": disk_percent
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/system/stats", 
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to send system stats: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"Error collecting system stats: {e}")
    
    async def run(self):
        """Main daemon loop"""
        update_interval = self.config.get("update_interval", 10)
        stats_interval = self.config.get("stats_interval", 60)
        backup_interval = self.config.get("backup_interval", 86400)  # Default: daily
        
        last_stats_time = 0
        last_backup_time = 0
        
        logger.info("Starting PyroPanel Daemon main loop")
        
        while self.running:
            try:
                # Fetch servers from API
                servers = await self._fetch_servers()
                
                # Update local server cache
                for server in servers:
                    self.servers[server["id"]] = server
                
                # Check for pending actions
                await self.check_pending_actions()
                
                # Monitor running servers
                await self.monitor_servers()
                
                # Collect system stats periodically
                current_time = time.time()
                if current_time - last_stats_time >= stats_interval:
                    await self.collect_system_stats()
                    last_stats_time = current_time
                
                # Create scheduled backups
                if current_time - last_backup_time >= backup_interval:
                    for server_id, server_info in self.servers.items():
                        if server_info.get("status") == "running" and server_info.get("container_id"):
                            await self.create_backup(server_id, server_info)
                    last_backup_time = current_time
                
                # Sleep until next update
                await asyncio.sleep(update_interval)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(update_interval)
    
    def start(self):
        """Start the daemon"""
        logger.info("Starting PyroPanel Daemon")
        asyncio.run(self.run())

if __name__ == "__main__":
    daemon = PyroServerDaemon()
    daemon.start()
