import requests
import json
import datetime
import sys
import getpass
import time
import csv
from collections import defaultdict

def get_meraki_ap_data(api_key, org_name, network_name, days=7):
    """
    Fetch access point status, inventory, and traffic data from a Meraki network.
    
    Args:
        api_key (str): Meraki API key
        org_name (str): Name of the Meraki organization
        network_name (str): Name of the network within the organization
        days (int): Number of days of traffic data to retrieve
        
    Returns:
        dict: Access point data or error message
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
    
    # Step 3: Get devices in the network
    print("Getting devices in the network...")
    try:
        devices_response = requests.get(f"{base_url}/networks/{network_id}/devices", headers=headers)
        devices_response.raise_for_status()
        
        all_devices = devices_response.json()
        
        # Filter for access points only (model name usually starts with MR)
        access_points = [device for device in all_devices if device.get('model', '').startswith('CW')]
        
        if not access_points:
            return {"error": "No access points found in the network"}
            
        print(f"Found {len(access_points)} access points")
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Error retrieving devices: {str(e)}"}
    
    # Step 4: Get detailed information for each AP
    ap_details = []
    
    for ap in access_points:
        ap_serial = ap.get('serial')
        if not ap_serial:
            continue
            
        print(f"Getting details for AP: {ap.get('name', ap_serial)}")
        
        try:
            # Get device status
            status_response = requests.get(f"{base_url}/devices/{ap_serial}/wireless/status", headers=headers)
            status_response.raise_for_status()
            status_data = status_response.json()
            
            # Get device clients (currently connected)
            clients_response = requests.get(
                f"{base_url}/devices/{ap_serial}/clients", 
                headers=headers,
                params={"timespan": 300}  # Last 5 minutes
            )
            clients_response.raise_for_status()
            clients_data = clients_response.json()
            
            # Get device connection stats
            timespan = days * 86400  # Convert days to seconds
            connection_stats_response = requests.get(
                f"{base_url}/devices/{ap_serial}/wireless/connectionStats", 
                headers=headers,
                params={"timespan": timespan}
            )
            connection_stats_response.raise_for_status()
            connection_stats = connection_stats_response.json()
            
            # Get device latency stats
            latency_stats_response = requests.get(
                f"{base_url}/devices/{ap_serial}/wireless/latencyStats", 
                headers=headers,
                params={"timespan": timespan}
            )
            latency_stats_response.raise_for_status()
            latency_stats = latency_stats_response.json()
            
            # Calculate current traffic
            current_traffic_sent = sum(client.get('usage', {}).get('sent', 0) for client in clients_data)
            current_traffic_recv = sum(client.get('usage', {}).get('recv', 0) for client in clients_data)
            
            # Combine all the data
            ap_info = {
                "name": ap.get('name', 'Unnamed'),
                "serial": ap_serial,
                "model": ap.get('model', 'Unknown'),
                "mac": ap.get('mac', 'Unknown'),
                "tags": ap.get('tags', []),
                "lanIp": ap.get('lanIp', 'Unknown'),
                "firmware": ap.get('firmware', 'Unknown'),
                "networkId": ap.get('networkId', 'Unknown'),
                "status": ap.get('status', 'Unknown'),
                "lastReportedAt": ap.get('lastReportedAt', 'Unknown'),
                "wireless_status": {
                    "status": status_data.get('status', 'Unknown'),
                    "connectionStats": connection_stats,
                    "latencyStats": latency_stats
                },
                "currentClients": len(clients_data),
                "currentClientsDetails": clients_data,
                "currentTraffic": {
                    "sent": current_traffic_sent,
                    "received": current_traffic_recv,
                    "total": current_traffic_sent + current_traffic_recv,
                    "sent_human": bytes_to_human_readable(current_traffic_sent),
                    "received_human": bytes_to_human_readable(current_traffic_recv),
                    "total_human": bytes_to_human_readable(current_traffic_sent + current_traffic_recv)
                }
            }
            
            ap_details.append(ap_info)
            
            # Rate limiting - Meraki API has a limit of 5 calls per second
            time.sleep(0.2)
            
        except requests.exceptions.RequestException as e:
            print(f"Warning: Error retrieving details for AP {ap_serial}: {str(e)}")
            continue
    
    # Step 5: Calculate aggregated statistics
    total_clients = sum(ap['currentClients'] for ap in ap_details)
    total_traffic_sent = sum(ap['currentTraffic']['sent'] for ap in ap_details)
    total_traffic_recv = sum(ap['currentTraffic']['received'] for ap in ap_details)
    total_traffic = total_traffic_sent + total_traffic_recv
    
    # Count APs by status
    ap_status_counts = defaultdict(int)
    for ap in ap_details:
        ap_status_counts[ap['status']] += 1
    
    # Count APs by model
    ap_model_counts = defaultdict(int)
    for ap in ap_details:
        ap_model_counts[ap['model']] += 1
    
    return {
        "organization": org_name,
        "network": network_name,
        "timespan_days": days,
        "timestamp": datetime.datetime.now().isoformat(),
        "total_access_points": len(ap_details),
        "total_clients": total_clients,
        "total_traffic": {
            "sent": total_traffic_sent,
            "received": total_traffic_recv,
            "total": total_traffic,
            "sent_human": bytes_to_human_readable(total_traffic_sent),
            "received_human": bytes_to_human_readable(total_traffic_recv),
            "total_human": bytes_to_human_readable(total_traffic)
        },
        "ap_status_summary": dict(ap_status_counts),
        "ap_model_summary": dict(ap_model_counts),
        "access_points": ap_details
    }

def bytes_to_human_readable(bytes_value):
    """Convert bytes to human-readable format (KB, MB, GB, etc.)"""
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024**2:
        return f"{bytes_value/1024:.2f} KB"
    elif bytes_value < 1024**3:
        return f"{bytes_value/1024**2:.2f} MB"
    elif bytes_value < 1024**4:
        return f"{bytes_value/1024**3:.2f} GB"
    else:
        return f"{bytes_value/1024**4:.2f} TB"

def export_ap_summary_to_csv(data, filename):
    """Export access point summary data to CSV file"""
    try:
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['Name', 'Serial', 'Model', 'MAC Address', 'LAN IP', 
                          'Status', 'Firmware', 'Current Clients', 
                          'Current Traffic (Sent)', 'Current Traffic (Received)', 
                          'Current Traffic (Total)', 'Last Reported']
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for ap in data["access_points"]:
                writer.writerow({
                    'Name': ap['name'],
                    'Serial': ap['serial'],
                    'Model': ap['model'],
                    'MAC Address': ap['mac'],
                    'LAN IP': ap['lanIp'],
                    'Status': ap['status'],
                    'Firmware': ap['firmware'],
                    'Current Clients': ap['currentClients'],
                    'Current Traffic (Sent)': ap['currentTraffic']['sent_human'],
                    'Current Traffic (Received)': ap['currentTraffic']['received_human'],
                    'Current Traffic (Total)': ap['currentTraffic']['total_human'],
                    'Last Reported': ap['lastReportedAt']
                })
        
        return True
    except Exception as e:
        print(f"Error exporting to CSV: {str(e)}")
        return False

def main():
    """Main function to run the script."""
    print("=" * 60)
    print("Meraki Access Points Status & Traffic Analyzer")
    print("=" * 60)
    
    # Get API key securely
    api_key = getpass.getpass("Enter your Meraki API key: ")
    
    # Organization and network details
    org_name = "CANADA MTN REGION"
    network_name = "CA-HA562-HSIA"
    
    # Get number of days for data retrieval
    try:
        days_input = input("Enter number of days for historical data (default: 7): ")
        days = int(days_input) if days_input.strip() else 7
    except ValueError:
        print("Invalid input. Using default of 7 days.")
        days = 7
    
    print(f"\nFetching access point data for network '{network_name}' in organization '{org_name}'...")
    print(f"Including historical data from the past {days} days...")
    
    # Get AP data
    result = get_meraki_ap_data(api_key, org_name, network_name, days)
    
    # Save results to files
    if "error" not in result:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"meraki_ap_status_{timestamp}.json"
        csv_filename = f"meraki_ap_status_{timestamp}.csv"
        
        # Save raw data to JSON
        with open(json_filename, "w") as f:
            json.dump(result, f, indent=2)
            
        # Export to CSV for easier viewing
        csv_export = export_ap_summary_to_csv(result, csv_filename)
        
        print(f"\nSuccess! Found {result['total_access_points']} access points.")
        
        # Print AP status summary
        print("\nAccess Point Status Summary:")
        for status, count in result['ap_status_summary'].items():
            print(f"  {status}: {count} APs")
        
        # Print AP model summary
        print("\nAccess Point Model Summary:")
        for model, count in result['ap_model_summary'].items():
            print(f"  {model}: {count} APs")
        
        # Print total client count
        print(f"\nTotal Connected Clients: {result['total_clients']}")
        
        # Print total traffic
        print("\nCurrent Traffic:")
        print(f"  Sent:     {result['total_traffic']['sent_human']}")
        print(f"  Received: {result['total_traffic']['received_human']}")
        print(f"  Total:    {result['total_traffic']['total_human']}")
        
        # Print AP details
        print("\nAccess Point Details:")
        print("-" * 60)
        print(f"{'Name':<20} {'Model':<10} {'Status':<10} {'Clients':<8} {'Traffic':<12}")
        print("-" * 60)
        
        for ap in sorted(result['access_points'], key=lambda x: x['currentClients'], reverse=True):
            print(f"{ap['name'][:20]:<20} {ap['model']:<10} {ap['status']:<10} {ap['currentClients']:<8} {ap['currentTraffic']['total_human']:<12}")
        
        print(f"\nDetailed results saved to {json_filename}")
        if csv_export:
            print(f"CSV report saved to {csv_filename}")
    else:
        print(f"\nError: {result['error']}")

if __name__ == "__main__":
    main()
