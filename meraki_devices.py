import requests
import time

# Define base API URL
BASE_URL = "https://api.meraki.com/api/v1"

def get_organizations(api_key):
    """Retrieve all organizations associated with the API key."""
    headers = {
        "X-Cisco-Meraki-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/organizations", headers=headers)
        response.raise_for_status()
        return response.json()  # Returns a list of organizations

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving organizations: {e}")
        return []

def get_network_devices(api_key, org_id, org_name):
    """Fetch all devices from all networks in a given organization."""
    headers = {
        "X-Cisco-Meraki-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        # Get all networks in the organization
        networks_response = requests.get(f"{BASE_URL}/organizations/{org_id}/networks", headers=headers)
        networks_response.raise_for_status()
        
        networks = networks_response.json()
        all_devices = []

        print(f"\nFetching devices for organization: {org_name} (ID: {org_id})")

        # Get devices for each network
        for network in networks:
            print(f"\nDevices in network: {network['name']} (ID: {network['id']})")
            devices_response = requests.get(f"{BASE_URL}/networks/{network['id']}/devices", headers=headers)
            devices_response.raise_for_status()
            
            devices = devices_response.json()
            for device in devices:
                print(f"- {device.get('name', 'Unnamed')} ({device.get('model', 'Unknown')})")
                print(f"  Serial: {device.get('serial', 'N/A')}")
                print(f"  MAC: {device.get('mac', 'N/A')}")
                print(f"  Firmware: {device.get('firmware', 'Unknown')}")
                print(f"  Status: {'Online' if device.get('status') == 'online' else 'Offline'}")

                all_devices.append(device)

            # Rate-limit to prevent API throttling
            time.sleep(0.2)

        return all_devices

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving devices: {e}")
        return []

def main():
    # Get user input for API key
    api_key = input("Enter your Meraki API key: ").strip()
    
    # Fetch all organizations
    organizations = get_organizations(api_key)
    if not organizations:
        print("No organizations found or invalid API key.")
        return
    
    # Iterate through all organizations
    for org in organizations:
        org_id = org["id"]
        org_name = org["name"]
        
        # Fetch and display devices for the organization
        devices = get_network_devices(api_key, org_id, org_name)
        
        if devices:
            print(f"\nTotal devices found in '{org_name}': {len(devices)}")
        else:
            print(f"\nNo devices found in '{org_name}'.")

if __name__ == "__main__":
    main()

