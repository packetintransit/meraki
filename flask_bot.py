from flask import Flask, render_template, request, jsonify, session
import requests
import json
import os
from datetime import datetime
import time
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a random secret key for session

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

# Initialize the chatbot
chatbot = MerakiChatbot()

# Routes
@app.route('/')
def index():
    if 'api_key' in session:
        api_key_set = True
    else:
        api_key_set = False
    return render_template('index.html', api_key_set=api_key_set)

@app.route('/process_command', methods=['POST'])
def process_command():
    command = request.form.get('command', '')
    
    # Initialize chatbot with session API key if it exists
    if 'api_key' in session:
        chatbot.set_api_key(session['api_key'])
    
    # Process the command
    response = chatbot.process_command(command)
    
    # If setting API key, store it in session
    if command.startswith('set_api_key') and 'API key has been set successfully' in response:
        api_key = command.split()[1]
        session['api_key'] = api_key
    
    return jsonify({'response': response})

@app.route('/clear_api_key', methods=['POST'])
def clear_api_key():
    if 'api_key' in session:
        session.pop('api_key')
    return jsonify({'success': True})

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create the HTML template file
    with open('templates/index.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meraki Dashboard API Chatbot</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }
        
        .chat-container {
            max-width: 900px;
            margin: 30px auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .chat-header {
            background-color: #0078CE;
            color: white;
            padding: 15px;
            font-size: 1.2em;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .chat-header img {
            height: 30px;
            margin-right: 10px;
        }
        
        .chat-history {
            height: 400px;
            overflow-y: auto;
            padding: 15px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        
        .chat-input {
            padding: 15px;
            display: flex;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 10px 15px;
            border-radius: 8px;
            max-width: 80%;
            word-wrap: break-word;
        }
        
        .user-message {
            background-color: #DCF8C6;
            margin-left: auto;
            border-top-right-radius: 0;
        }
        
        .bot-message {
            background-color: #E1E8ED;
            margin-right: auto;
            border-top-left-radius: 0;
            white-space: pre-line;
        }
        
        .helper-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
            padding: 0 15px 15px;
        }
        
        .api-key-status {
            font-size: 0.8em;
            margin-left: auto;
        }
        
        .buttons-container {
            margin-top: 15px;
            padding: 0 15px 15px;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <div>
                <span>Meraki Dashboard API Chatbot</span>
            </div>
            <div class="api-key-status">
                {% if api_key_set %}
                <span class="badge bg-success">API Key: Set</span>
                <button id="clearApiKey" class="btn btn-sm btn-danger">Clear</button>
                {% else %}
                <span class="badge bg-warning text-dark">API Key: Not Set</span>
                {% endif %}
            </div>
        </div>
        
        <div class="chat-history" id="chatHistory">
            <div class="message bot-message">
                Welcome to Meraki Dashboard API Chatbot! Type 'help' to see available commands.
            </div>
        </div>
        
        <div class="chat-input">
            <input type="text" id="commandInput" class="form-control" placeholder="Type a command..." autocomplete="off">
            <button id="sendButton" class="btn btn-primary ms-2">Send</button>
        </div>
        
        <div class="helper-buttons">
            <button class="btn btn-sm btn-outline-secondary" onclick="insertCommand('help')">Help</button>
            <button class="btn btn-sm btn-outline-secondary" onclick="insertCommand('set_api_key ')">Set API Key</button>
            <button class="btn btn-sm btn-outline-secondary" onclick="insertCommand('get_organizations')">Get Organizations</button>
            <button class="btn btn-sm btn-outline-secondary" onclick="insertCommand('get_networks ')">Get Networks</button>
            <button class="btn btn-sm btn-outline-secondary" onclick="insertCommand('get_devices ')">Get Devices</button>
            <button class="btn btn-sm btn-outline-secondary" onclick="insertCommand('get_ssids ')">Get SSIDs</button>
            <button class="btn btn-sm btn-outline-secondary" onclick="insertCommand('get_clients ')">Get Clients</button>
            <button class="btn btn-sm btn-outline-secondary" onclick="insertCommand('get_vpn ')">Get VPN Status</button>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script>
        function addMessage(message, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = isUser ? 'message user-message' : 'message bot-message';
            messageDiv.textContent = message;
            
            const chatHistory = document.getElementById('chatHistory');
            chatHistory.appendChild(messageDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }
        
        function sendCommand() {
            const commandInput = document.getElementById('commandInput');
            const command = commandInput.value.trim();
            
            if (command === '') return;
            
            addMessage(command, true);
            commandInput.value = '';
            
            // Display typing indicator
            const typingIndicator = document.createElement('div');
            typingIndicator.className = 'message bot-message typing-indicator';
            typingIndicator.textContent = 'Processing...';
            
            const chatHistory = document.getElementById('chatHistory');
            chatHistory.appendChild(typingIndicator);
            chatHistory.scrollTop = chatHistory.scrollHeight;
            
            // Send command to server
            $.ajax({
                url: '/process_command',
                method: 'POST',
                data: { command: command },
                success: function(data) {
                    // Remove typing indicator
                    chatHistory.removeChild(typingIndicator);
                    
                    // Add response
                    addMessage(data.response, false);
                    
                    // Update API key status if needed
                    if (command.startsWith('set_api_key') && data.response.includes('successfully')) {
                        location.reload();  // Refresh to update API key status
                    }
                },
                error: function() {
                    // Remove typing indicator
                    chatHistory.removeChild(typingIndicator);
                    
                    // Add error message
                    addMessage('Error processing command. Please try again.', false);
                }
            });
        }
        
        function insertCommand(cmd) {
            const commandInput = document.getElementById('commandInput');
            commandInput.value = cmd;
            commandInput.focus();
        }
        
        // Event listeners
        document.getElementById('sendButton').addEventListener('click', sendCommand);
        
        document.getElementById('commandInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendCommand();
            }
        });
        
        if (document.getElementById('clearApiKey')) {
            document.getElementById('clearApiKey').addEventListener('click', function() {
                $.ajax({
                    url: '/clear_api_key',
                    method: 'POST',
                    success: function() {
                        location.reload();  // Refresh to update API key status
                    }
                });
            });
        }
    </script>
</body>
</html>
        ''')
    
    # Run the Flask app
    app.run(debug=True)