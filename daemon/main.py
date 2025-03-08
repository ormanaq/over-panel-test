import asyncio
import docker
import sqlite3
from datetime import datetime
import logging
import os
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('GameServerDaemon')

class GameServerDaemon:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.db_path = "../backend/game_panel.db"
        
        # Ensure the database exists
        if not os.path.exists(self.db_path):
            logger.error(f"Database not found at {self.db_path}")
            raise FileNotFoundError(f"Database not found at {self.db_path}")

    async def monitor_server(self, server_id: int, container_id: str):
        try:
            container = self.docker_client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Calculate resource usage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_usage = (cpu_delta / system_delta) * 100.0
            memory_usage = stats['memory_stats']['usage']
            
            # Update server status in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE servers 
                SET status = ?, 
                    last_checked = ?
                WHERE id = ?
            """, (container.status, datetime.utcnow(), server_id))
            
            # Log server metrics
            logger.info(f"Server {server_id} stats - CPU: {cpu_usage:.2f}%, Memory: {memory_usage / 1024 / 1024:.2f}MB")
            
            conn.commit()
            conn.close()
            
        except docker.errors.NotFound:
            logger.warning(f"Container {container_id} for server {server_id} not found")
            # Update server status to error
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE servers 
                SET status = 'error',
                    container_id = NULL
                WHERE id = ?
            """, (server_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error monitoring server {server_id}: {str(e)}")

    async def monitor_all_servers(self):
        while True:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get all running servers
                cursor.execute("""
                    SELECT id, container_id 
                    FROM servers 
                    WHERE container_id IS NOT NULL
                """)
                servers = cursor.fetchall()
                conn.close()
                
                # Monitor each server
                for server_id, container_id in servers:
                    await self.monitor_server(server_id, container_id)
                
                # Wait before next monitoring cycle
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {str(e)}")
                await asyncio.sleep(5)  # Wait before retry on error

    async def cleanup_orphaned_containers(self):
        """Cleanup any containers that are running but not in our database"""
        while True:
            try:
                # Get all game server containers
                containers = self.docker_client.containers.list(
                    filters={"label": "game_server=true"}
                )
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get all known container IDs
                cursor.execute("SELECT container_id FROM servers WHERE container_id IS NOT NULL")
                known_containers = {row[0] for row in cursor.fetchall()}
                
                # Stop and remove orphaned containers
                for container in containers:
                    if container.id not in known_containers:
                        logger.warning(f"Found orphaned container {container.id}, cleaning up")
                        try:
                            container.stop()
                            container.remove()
                        except Exception as e:
                            logger.error(f"Error cleaning up container {container.id}: {str(e)}")
                
                conn.close()
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in cleanup cycle: {str(e)}")
                await asyncio.sleep(30)  # Wait before retry on error

    async def run(self):
        """Run the daemon"""
        logger.info("Starting Game Server Daemon")
        try:
            # Run monitoring and cleanup tasks
            await asyncio.gather(
                self.monitor_all_servers(),
                self.cleanup_orphaned_containers()
            )
        except Exception as e:
            logger.error(f"Daemon error: {str(e)}")
            raise

if __name__ == "__main__":
    daemon = GameServerDaemon()
    asyncio.run(daemon.run())
