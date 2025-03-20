import requests
import json
import datetime
import sys
import getpass
import time

def get_meraki_client_events(api_key, org_name, network_name):
    """
    Fetch client events from a specific Meraki network in an organization.
    
    Args:
        api_key (str): Meraki API key
        org_name (str): Name of the Meraki organization
        network_name (str): Name of the network within the organization
        
    Returns:
        dict: Client events data or error message
    """
    base_url = "https://api.meraki.com/api/v1"
    headers = {
        "X-Cisco-Meraki-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Step 1: Get organization ID
    print("Getting organization ID for:", org_name)
    try:
        orgs_response = requests.get(f"{base_url}/organizations", headers=headers)
        orgs_response.raise_for_status()
        
        organizations = orgs_response.json()
        org_id = None
        
        for org in organizations:
            if org["name"] == org_name:
                org_id = org["id"]
                break
                
        if not org_id:
            return {"error": f"Organization '{org_name}' not found"}
        
        print(f"Organization ID found: {org_id}")
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Error retrieving organizations: {str(e)}"}
    
    # Step 2: Get network ID
    print("Getting network ID for:", network_name)
    try:
        networks_response = requests.get(f"{base_url}/organizations/{org_id}/networks", headers=headers)
        networks_response.raise_for_status()
        
        networks = networks_response.json()
        network_id = None
        
        for network in networks:
            if network["name"] == network_name:
                network_id = network["id"]
                break
                
        if not network_id:
            return {"error": f"Network '{network_name}' not found in organization '{org_name}'"}
        
        print(f"Network ID found: {network_id}")
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Error retrieving networks: {str(e)}"}
    
    # Step 3: Get clients
    print("Getting clients for network...")
    try:
        # Get list of clients from the past 24 hours
        timespan = 86400  # 24 hours in seconds
        clients_response = requests.get(
            f"{base_url}/networks/{network_id}/clients", 
            headers=headers,
            params={"timespan": timespan}
        )
        clients_response.raise_for_status()
        clients = clients_response.json()
        
        if not clients:
            return {"message": "No clients found in the network"}
            
        print(f"Found {len(clients)} clients")
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Error retrieving clients: {str(e)}"}
    
    # Step 4: Get client events for each client
    all_events = []
    
    print("Getting client events...")
    for client in clients:
        client_id = client["id"]
        try:
            print(f"Getting events for client: {client['description'] if 'description' in client else client_id}")
            
            # Get events from the past 24 hours
            events_response = requests.get(
                f"{base_url}/networks/{network_id}/clients/{client_id}/events",
                headers=headers,
                params={"timespan": timespan}
            )
            events_response.raise_for_status()
            
            client_events = events_response.json()
            
            if client_events and "events" in client_events:
                for event in client_events["events"]:
                    event["clientId"] = client_id
                    event["clientMac"] = client.get("mac", "Unknown")
                    event["clientDescription"] = client.get("description", "Unknown")
                    all_events.append(event)
            
            # Rate limiting - Meraki API has a limit of 5 calls per second
            time.sleep(0.2)
            
        except requests.exceptions.RequestException as e:
            print(f"Warning: Error retrieving events for client {client_id}: {str(e)}")
            continue
    
    return {
        "organization": org_name,
        "network": network_name,
        "clientCount": len(clients),
        "eventCount": len(all_events),
        "events": all_events
    }

def main():
    """Main function to run the script."""
    print("=" * 60)
    print("Meraki Client Events Fetcher")
    print("=" * 60)
    
    # Get API key securely
    api_key = getpass.getpass("Enter your Meraki API key: ")
    
    # Organization and network details
    org_name = "CANADA MTN REGION"
    network_name = "CA-HA562-HSIA"
    
    print(f"\nFetching client events for network '{network_name}' in organization '{org_name}'...")
    
    # Get client events
    result = get_meraki_client_events(api_key, org_name, network_name)
    
    # Save results to a file
    if "error" not in result:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"meraki_client_events_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(result, f, indent=2)
            
        print(f"\nSuccess! Found {result['eventCount']} events from {result['clientCount']} clients.")
        print(f"Results saved to {filename}")
        
        # Print event summary
        if result["events"]:
            print("\nEvent Summary:")
            print("-" * 60)
            event_types = {}
            for event in result["events"]:
                event_type = event.get("type", "Unknown")
                event_types[event_type] = event_types.get(event_type, 0) + 1
                
            for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
                print(f"{event_type}: {count} events")
    else:
        print(f"\nError: {result['error']}")

if __name__ == "__main__":
    main()
