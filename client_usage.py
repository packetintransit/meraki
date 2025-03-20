import requests
import json
import datetime
import sys
import getpass
import time
import csv
from collections import defaultdict

def get_meraki_client_usage(api_key, org_name, network_name, days=7):
    """
    Fetch client usage data from a specific Meraki network in an organization.
    
    Args:
        api_key (str): Meraki API key
        org_name (str): Name of the Meraki organization
        network_name (str): Name of the network within the organization
        days (int): Number of days of data to retrieve
        
    Returns:
        dict: Client usage data or error message
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
    
    # Step 3: Get clients with usage data
    print(f"Getting client usage data for the past {days} days...")
    try:
        # Calculate timespan in seconds
        timespan = days * 86400  # days * 24 hours * 60 minutes * 60 seconds
        
        clients_response = requests.get(
            f"{base_url}/networks/{network_id}/clients", 
            headers=headers,
            params={"timespan": timespan}
        )
        clients_response.raise_for_status()
        clients = clients_response.json()
        
        if not clients:
            return {"message": "No clients found in the network for the specified time period"}
            
        print(f"Found {len(clients)} clients")
        
        # Step 4: Get client usage data
        client_usage = []
        
        for client in clients:
            usage_data = {
                "id": client.get("id", "Unknown"),
                "description": client.get("description", "Unknown"),
                "mac": client.get("mac", "Unknown"),
                "ip": client.get("ip", "Unknown"),
                "user": client.get("user", "Unknown"),
                "firstSeen": client.get("firstSeen", "Unknown"),
                "lastSeen": client.get("lastSeen", "Unknown"),
                "manufacturer": client.get("manufacturer", "Unknown"),
                "os": client.get("os", "Unknown"),
                "usage": {
                    "sent": client.get("usage", {}).get("sent", 0),
                    "recv": client.get("usage", {}).get("recv", 0),
                    "total": client.get("usage", {}).get("total", 0)
                },
                "status": client.get("status", "Unknown"),
                "ssid": client.get("ssid", "Unknown") if "ssid" in client else "Not Wireless"
            }
            
            client_usage.append(usage_data)
        
        # Sort clients by total usage (descending)
        client_usage.sort(key=lambda x: x["usage"]["total"], reverse=True)
        
        # Calculate total network usage
        total_sent = sum(client["usage"]["sent"] for client in client_usage)
        total_recv = sum(client["usage"]["recv"] for client in client_usage)
        total_usage = sum(client["usage"]["total"] for client in client_usage)
        
        # Calculate usage by OS
        usage_by_os = defaultdict(int)
        for client in client_usage:
            os_name = client["os"] if client["os"] != "Unknown" else "Other"
            usage_by_os[os_name] += client["usage"]["total"]
        
        # Calculate usage by SSID/connection method
        usage_by_ssid = defaultdict(int)
        for client in client_usage:
            ssid = client["ssid"] if client["ssid"] != "Unknown" else "Other"
            usage_by_ssid[ssid] += client["usage"]["total"]
        
        return {
            "organization": org_name,
            "network": network_name,
            "timespan_days": days,
            "total_clients": len(clients),
            "total_usage": {
                "sent_bytes": total_sent,
                "received_bytes": total_recv,
                "total_bytes": total_usage,
                "sent_human": bytes_to_human_readable(total_sent),
                "received_human": bytes_to_human_readable(total_recv),
                "total_human": bytes_to_human_readable(total_usage)
            },
            "usage_by_os": dict(usage_by_os),
            "usage_by_ssid": dict(usage_by_ssid),
            "clients": client_usage
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Error retrieving client usage data: {str(e)}"}

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
        
def export_to_csv(data, filename):
    """Export client usage data to CSV file"""
    try:
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['Client ID', 'Description', 'MAC Address', 'IP Address', 
                          'User', 'OS', 'Manufacturer', 'SSID', 'First Seen', 
                          'Last Seen', 'Status', 'Sent (B)', 'Received (B)', 
                          'Total (B)', 'Sent', 'Received', 'Total']
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for client in data["clients"]:
                writer.writerow({
                    'Client ID': client['id'],
                    'Description': client['description'],
                    'MAC Address': client['mac'],
                    'IP Address': client['ip'],
                    'User': client['user'],
                    'OS': client['os'],
                    'Manufacturer': client['manufacturer'],
                    'SSID': client['ssid'],
                    'First Seen': client['firstSeen'],
                    'Last Seen': client['lastSeen'],
                    'Status': client['status'],
                    'Sent (B)': client['usage']['sent'],
                    'Received (B)': client['usage']['recv'],
                    'Total (B)': client['usage']['total'],
                    'Sent': bytes_to_human_readable(client['usage']['sent']),
                    'Received': bytes_to_human_readable(client['usage']['recv']),
                    'Total': bytes_to_human_readable(client['usage']['total'])
                })
        
        return True
    except Exception as e:
        print(f"Error exporting to CSV: {str(e)}")
        return False

def main():
    """Main function to run the script."""
    print("=" * 60)
    print("Meraki Client Usage Analyzer")
    print("=" * 60)
    
    # Get API key securely
    api_key = getpass.getpass("Enter your Meraki API key: ")
    
    # Organization and network details
    org_name = "CANADA MTN REGION"
    network_name = "CA-HA562-HSIA"
    
    # Get number of days for data retrieval
    try:
        days_input = input("Enter number of days to analyze (default: 7): ")
        days = int(days_input) if days_input.strip() else 7
    except ValueError:
        print("Invalid input. Using default of 7 days.")
        days = 7
    
    print(f"\nFetching client usage data for network '{network_name}' in organization '{org_name}'...")
    print(f"Analyzing data from the past {days} days...")
    
    # Get client usage data
    result = get_meraki_client_usage(api_key, org_name, network_name, days)
    
    # Save results to files
    if "error" not in result:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"meraki_client_usage_{timestamp}.json"
        csv_filename = f"meraki_client_usage_{timestamp}.csv"
        
        # Save raw data to JSON
        with open(json_filename, "w") as f:
            json.dump(result, f, indent=2)
            
        # Export to CSV for easier viewing
        csv_export = export_to_csv(result, csv_filename)
        
        print(f"\nSuccess! Found {result['total_clients']} clients.")
        print("\nTotal Network Usage:")
        print(f"  Sent:     {result['total_usage']['sent_human']}")
        print(f"  Received: {result['total_usage']['received_human']}")
        print(f"  Total:    {result['total_usage']['total_human']}")
        
        # Print usage by OS
        print("\nUsage by Operating System:")
        for os, usage in sorted(result['usage_by_os'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {os}: {bytes_to_human_readable(usage)}")
        
        # Print usage by SSID
        print("\nUsage by SSID/Connection:")
        for ssid, usage in sorted(result['usage_by_ssid'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {ssid}: {bytes_to_human_readable(usage)}")
        
        # Print top 5 clients by usage
        print("\nTop 5 Clients by Usage:")
        for i, client in enumerate(result['clients'][:5], 1):
            description = client['description'] if client['description'] != "Unknown" else client['mac']
            print(f"  {i}. {description}: {bytes_to_human_readable(client['usage']['total'])}")
        
        print(f"\nDetailed results saved to {json_filename}")
        if csv_export:
            print(f"CSV report saved to {csv_filename}")
    else:
        print(f"\nError: {result['error']}")

if __name__ == "__main__":
    main()
