import requests
import json
import os
from datetime import datetime

def get_switch_settings(api_key, org_name="Knoxs Data", network_name="SoHo"):
    """
    Get switch settings from Meraki Dashboard API
    
    Args:
        api_key (str): Meraki API key
        org_name (str): Organization name to search for
        network_name (str): Network name to get switch settings for
        
    Returns:
        dict: Switch settings for the specified network
    """
    # Base API URL
    base_url = "https://api.meraki.com/api/v1"
    
    # Common headers
    headers = {
        'X-Cisco-Meraki-API-Key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Step 1: Get organization ID
    try:
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
        
        # Step 3: Get switch settings
        switch_settings_url = f"{base_url}/networks/{network_id}/switch/settings"
        response = requests.get(switch_settings_url, headers=headers)
        response.raise_for_status()
        switch_settings = response.json()
        
        return switch_settings
        
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
    
    # Get switch settings
    switch_settings = get_switch_settings(api_key)
    
    if switch_settings:
        print(json.dumps(switch_settings, indent=2))
