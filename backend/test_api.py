import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    # 1. Register a new user
    register_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass123"
    }
    
    print("\n1. Registering new user...")
    register_response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    print(f"Register Response: {register_response.status_code}")
    print(json.dumps(register_response.json(), indent=2))

    # 2. Login to get access token
    print("\n2. Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": "testuser", "password": "testpass123"}
    )
    print(f"Login Response: {login_response.status_code}")
    print(json.dumps(login_response.json(), indent=2))
    
    if login_response.status_code == 200:
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 3. Create a new game server
        server_data = {
            "name": "Test Minecraft Server",
            "game_type": "minecraft",
            "port": 25565,
            "memory_limit": 2048,  # 2GB RAM
            "cpu_limit": 1.0  # 100% of one CPU core
        }
        
        print("\n3. Creating new game server...")
        create_server_response = requests.post(
            f"{BASE_URL}/servers/",
            headers=headers,
            json=server_data
        )
        print(f"Create Server Response: {create_server_response.status_code}")
        print(json.dumps(create_server_response.json(), indent=2))
        
        if create_server_response.status_code == 200:
            server_id = create_server_response.json()["id"]
            
            # 4. List all servers
            print("\n4. Listing all servers...")
            list_servers_response = requests.get(
                f"{BASE_URL}/servers/",
                headers=headers
            )
            print(f"List Servers Response: {list_servers_response.status_code}")
            print(json.dumps(list_servers_response.json(), indent=2))
            
            # 5. Start the server
            print("\n5. Starting the server...")
            start_command = {"command": "start"}
            start_response = requests.post(
                f"{BASE_URL}/servers/{server_id}/command",
                headers=headers,
                json=start_command
            )
            print(f"Start Server Response: {start_response.status_code}")
            print(json.dumps(start_response.json(), indent=2))

if __name__ == "__main__":
    test_api()
