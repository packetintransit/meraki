import requests
import json
import os
from datetime import datetime

def get_client_usage_history(api_key, org_name="DevNet Sandbox", 
                            network_name="DNSMB4-s.jayaraj007007@gmail.com", 
                            client_id="k0191cb"):
    """
    Get usage history for a specific client from Meraki Dashboard API
    
    Args:
        api_key (str): Meraki API key
        org_name (str): Organization name to search for
        network_name (str): Network name to search within
        client_id (str): Specific client ID to get usage history for (defaults to k0191cb)
        
    Returns:
        dict: Usage history data for the specified client
    """
    # Base API URL
    base_url = "https://api.meraki.com/api/v1"
    
    # Common headers
    headers = {
        'X-Cisco-Meraki-API-Key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        # Step 1: Get organization ID
        orgs_url = f"{base_url}/organizations"
        response = requests.get(orgs_url, headers=headers)
        response.raise_for_status()
        organizations = response.json()
        
        org_id = None
        for org in organizations:
            if org['name'] == org_name:
                org_id = org['id']
                break
        
        if not org_id:
            raise ValueError(f"Organization '{org_name}' not found")
            
        # Step 2: Get network ID
        networks_url = f"{base_url}/organizations/{org_id}/networks"
        response = requests.get(networks_url, headers=headers)
        response.raise_for_status()
        networks = response.json()
        
        network_id = None
        for network in networks:
            if network['name'] == network_name:
                network_id = network['id']
                break
        
        if not network_id:
            raise ValueError(f"Network '{network_name}' not found")
        
        # Step 3: Find client if client_id not provided or verify client exists
        if not client_id:
            clients_url = f"{base_url}/networks/{network_id}/clients"
            response = requests.get(clients_url, headers=headers)
            response.raise_for_status()
            clients = response.json()
            
            if not clients:
                raise ValueError("No clients found in the network")
            
            # Use the first client if none specified
            client_id = clients[0]['id']
        
        # Step 4: Get client usage history
        history_url = f"{base_url}/networks/{network_id}/clients/{client_id}/usageHistory"
        response = requests.get(history_url, headers=headers)
        response.raise_for_status()
        usage_history = response.json()
        
        return usage_history
        
    except requests.exceptions.RequestException as e:
        print(f"API request error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Status code: {e.response.status_code}")
            print(f"Response: {e.response.text}")
        return None

if __name__ == "__main__":
    # Get API key from environment variable for security
    api_key = os.environ.get("MERAKI_API_KEY")
    
    if not api_key:
        print("Error: MERAKI_API_KEY environment variable not set")
        print("Set it with: export MERAKI_API_KEY='your-api-key'")
        exit(1)
    
    # Get client usage history
    usage_history = get_client_usage_history(api_key)
    
    if usage_history:
        print(json.dumps(usage_history, indent=2, sort_keys=True))
