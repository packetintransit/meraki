import requests
import json
import os
from datetime import datetime
import time

class MerakiChatbot:
    def __init__(self, api_key=None):
        self.base_url = "https://api.meraki.com/api/v1"
        self.api_key = api_key
        self.headers = {
            "X-Cisco-Meraki-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.organizations = None
        self.networks = {}
        self.devices = {}
        self.ssids = {}

    def set_api_key(self, api_key):
        """Set or update the API key"""
        self.api_key = api_key
        self.headers["X-Cisco-Meraki-API-Key"] = self.api_key
        return "API key has been set successfully."

    def get_organizations(self):
        """Get all organizations the API key has access to"""
        endpoint = f"{self.base_url}/organizations"
        response = self._make_request("GET", endpoint)
        
        if response.status_code == 200:
            self.organizations = response.json()
            org_list = [f"ID: {org['id']} - Name: {org['name']}" for org in self.organizations]
            return f"Found {len(org_list)} organizations:\n" + "\n".join(org_list)
        else:
            return f"Failed to retrieve organizations. Status code: {response.status_code} - {response.text}"

    def get_networks(self, org_id):
        """Get all networks in an organization"""
        endpoint = f"{self.base_url}/organizations/{org_id}/networks"
        response = self._make_request("GET", endpoint)
        
        if response.status_code == 200:
            self.networks[org_id] = response.json()
            network_list = [f"ID: {net['id']} - Name: {net['name']} - Type: {','.join(net['productTypes'])}" 
                           for net in self.networks[org_id]]
            return f"Found {len(network_list)} networks in organization {org_id}:\n" + "\n".join(network_list)
        else:
            return f"Failed to retrieve networks. Status code: {response.status_code} - {response.text}"

    def get_devices(self, network_id):
        """Get all devices in a network"""
        endpoint = f"{self.base_url}/networks/{network_id}/devices"
        response = self._make_request("GET", endpoint)
        
        if response.status_code == 200:
            self.devices[network_id] = response.json()
            device_list = []
            for device in self.devices[network_id]:
                device_info = f"Name: {device.get('name', 'Unnamed')} - Model: {device.get('model', 'N/A')}"
                device_info += f" - Serial: {device.get('serial', 'N/A')}"
                device_list.append(device_info)
            
            return f"Found {len(device_list)} devices in network {network_id}:\n" + "\n".join(device_list)
        else:
            return f"Failed to retrieve devices. Status code: {response.status_code} - {response.text}"

    def get_ssids(self, network_id):
        """Get all SSIDs in a network"""
        endpoint = f"{self.base_url}/networks/{network_id}/wireless/ssids"
        response = self._make_request("GET", endpoint)
        
        if response.status_code == 200:
            self.ssids[network_id] = response.json()
            ssid_list = []
            for ssid in self.ssids[network_id]:
                status = "Enabled" if ssid.get('enabled', False) else "Disabled"
                ssid_info = f"Number: {ssid.get('number', 'N/A')} - Name: {ssid.get('name', 'Unnamed')} - Status: {status}"
                auth_mode = ssid.get('authMode', 'N/A')
                ssid_info += f" - Auth Mode: {auth_mode}"
                ssid_list.append(ssid_info)
            
            return f"Found {len(ssid_list)} SSIDs in network {network_id}:\n" + "\n".join(ssid_list)
        else:
            return f"Failed to retrieve SSIDs. Status code: {response.status_code} - {response.text}"
    
    def get_clients(self, network_id, timespan=3600):
        """Get clients in a network for the last hour (default) or specified timespan in seconds"""
        endpoint = f"{self.base_url}/networks/{network_id}/clients"
        params = {"timespan": timespan}
        response = self._make_request("GET", endpoint, params=params)
        
        if response.status_code == 200:
            clients = response.json()
            client_list = []
            for client in clients:
                client_info = f"Description: {client.get('description', 'N/A')} - MAC: {client.get('mac', 'N/A')}"
                client_info += f" - IP: {client.get('ip', 'N/A')} - VLAN: {client.get('vlan', 'N/A')}"
                client_list.append(client_info)
            
            return f"Found {len(client_list)} clients in network {network_id}:\n" + "\n".join(client_list)
        else:
            return f"Failed to retrieve clients. Status code: {response.status_code} - {response.text}"
    
    def get_vpn_status(self, network_id):
        """Get VPN status for a network"""
        endpoint = f"{self.base_url}/networks/{network_id}/appliance/vpn/status"
        response = self._make_request("GET", endpoint)
        
        if response.status_code == 200:
            vpn_status = response.json()
            return json.dumps(vpn_status, indent=2)
        else:
            return f"Failed to retrieve VPN status. Status code: {response.status_code} - {response.text}"

    def _make_request(self, method, endpoint, params=None, data=None):
        """Helper method to make API requests with rate limiting consideration"""
        try:
            if method == "GET":
                response = requests.get(endpoint, headers=self.headers, params=params)
            elif method == "POST":
                response = requests.post(endpoint, headers=self.headers, json=data)
            elif method == "PUT":
                response = requests.put(endpoint, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(endpoint, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                print(f"Rate limit hit. Waiting for {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(method, endpoint, params, data)
                
            return response
        except requests.exceptions.RequestException as e:
            # Create a mock response object to maintain consistency
            class MockResponse:
                def __init__(self, status_code, text):
                    self.status_code = status_code
                    self.text = text
            
            return MockResponse(500, str(e))

    def process_command(self, command):
        """Process user commands and return responses"""
        if not command:
            return "Please enter a command."
        
        cmd_parts = command.strip().split()
        cmd = cmd_parts[0].lower()
        
        # Check if API key is set for commands that need it
        if cmd not in ["help", "set_api_key"] and not self.api_key:
            return "Please set your API key first using: set_api_key YOUR_API_KEY"
        
        if cmd == "help":
            return self._get_help()
        elif cmd == "set_api_key":
            if len(cmd_parts) < 2:
                return "Please provide an API key. Usage: set_api_key YOUR_API_KEY"
            return self.set_api_key(cmd_parts[1])
        elif cmd == "get_organizations" or cmd == "orgs":
            return self.get_organizations()
        elif cmd == "get_networks" or cmd == "networks":
            if len(cmd_parts) < 2:
                return "Please provide an organization ID. Usage: get_networks ORG_ID"
            return self.get_networks(cmd_parts[1])
        elif cmd == "get_devices" or cmd == "devices":
            if len(cmd_parts) < 2:
                return "Please provide a network ID. Usage: get_devices NETWORK_ID"
            return self.get_devices(cmd_parts[1])
        elif cmd == "get_ssids" or cmd == "ssids":
            if len(cmd_parts) < 2:
                return "Please provide a network ID. Usage: get_ssids NETWORK_ID"
            return self.get_ssids(cmd_parts[1])
        elif cmd == "get_clients" or cmd == "clients":
            if len(cmd_parts) < 2:
                return "Please provide a network ID. Usage: get_clients NETWORK_ID [TIMESPAN_SECONDS]"
            timespan = int(cmd_parts[2]) if len(cmd_parts) > 2 else 3600
            return self.get_clients(cmd_parts[1], timespan)
        elif cmd == "get_vpn" or cmd == "vpn":
            if len(cmd_parts) < 2:
                return "Please provide a network ID. Usage: get_vpn NETWORK_ID"
            return self.get_vpn_status(cmd_parts[1])
        else:
            return f"Unknown command: {cmd}. Type 'help' to see available commands."
    
    def _get_help(self):
        """Return help information"""
        help_text = """
Available Commands:
------------------
help                            - Show this help message
set_api_key YOUR_API_KEY        - Set your Meraki API key
get_organizations (orgs)        - List all organizations you have access to
get_networks ORG_ID (networks)  - List all networks in an organization
get_devices NETWORK_ID (devices)- List all devices in a network
get_ssids NETWORK_ID (ssids)    - List all SSIDs in a network
get_clients NETWORK_ID [TIMESPAN]- List clients in a network (default timespan: 1 hour)
get_vpn NETWORK_ID (vpn)        - Get VPN status for a network

Short command aliases are shown in parentheses.
"""
        return help_text


# Simple CLI interface for the chatbot
def main():
    print("Welcome to Meraki Dashboard API Chatbot!")
    print("Type 'help' to see available commands or 'exit' to quit.")
    
    chatbot = MerakiChatbot()
    
    while True:
        command = input("\nMeraki> ").strip()
        
        if command.lower() in ["exit", "quit", "bye"]:
            print("Goodbye!")
            break
        
        response = chatbot.process_command(command)
        print(response)


if __name__ == "__main__":
    main()