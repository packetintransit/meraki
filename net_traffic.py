import meraki
import getpass
import json
import time
import datetime
import os
import csv
import matplotlib.pyplot as plt
from collections import defaultdict

# Your Meraki organization and network information
ORG_NAME = "CANADA MTN REGION"
NETWORK_NAME = "CA-HA562-HSIA"
OUTPUT_DIR = "traffic_data"  # Directory to save the output files

# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def get_client_traffic(dashboard, network_id, timespan=3600):
    """Get client traffic data for the network"""
    try:
        # Get all clients
        clients = dashboard.networks.getNetworkClients(
            network_id,
            timespan=timespan
        )
        
        print(f"Found {len(clients)} clients in the network")
        
        # Create a list to store all client traffic data
        client_traffic = []
        
        # For each client, get detailed information
        for client in clients:
            client_traffic.append({
                'description': client.get('description', 'Unknown'),
                'dhcpHostname': client.get('dhcpHostname', 'Unknown'),
                'id': client.get('id', 'Unknown'),
                'ip': client.get('ip', 'Unknown'),
                'mac': client.get('mac', 'Unknown'),
                'manufacturer': client.get('manufacturer', 'Unknown'),
                'os': client.get('os', 'Unknown'),
                'user': client.get('user', 'Unknown'),
                'usage': {
                    'sent': client.get('usage', {}).get('sent', 0),
                    'recv': client.get('usage', {}).get('recv', 0),
                    'total': client.get('usage', {}).get('total', 0)
                }
            })
            
        return client_traffic
    except Exception as e:
        print(f"Error getting client traffic: {str(e)}")
        return []

def get_application_traffic(dashboard, network_id, timespan=3600):
    """Get application traffic data for the network"""
    try:
        # Get all application usage
        app_usage = dashboard.networks.getNetworkTrafficAnalysis(network_id)
        
        # Check if application data is available
        if not app_usage or 'applicationUsage' not in app_usage:
            print("Application traffic data not available for this network")
            return []
            
        return app_usage.get('applicationUsage', [])
    except Exception as e:
        print(f"Error getting application traffic: {str(e)}")
        return []

def get_device_traffic(dashboard, network_id):
    """Get traffic data for each device in the network"""
    try:
        # Get all devices
        devices = dashboard.networks.getNetworkDevices(network_id)
        
        device_traffic = []
        
        for device in devices:
            # Try to get usage information
            try:
                if device['model'].startswith('MX'):
                    # For security appliances, get detailed traffic
                    usage = dashboard.appliance.getDeviceApplianceUplinksUsage(
                        device['serial'],
                        timespan=3600
                    )
                    device_traffic.append({
                        'name': device.get('name', device['serial']),
                        'model': device['model'],
                        'serial': device['serial'],
                        'usage': usage
                    })
                elif device['model'].startswith('MS'):
                    # For switches, get port usage
                    ports = dashboard.switch.getDeviceSwitchPorts(device['serial'])
                    device_traffic.append({
                        'name': device.get('name', device['serial']),
                        'model': device['model'],
                        'serial': device['serial'],
                        'ports': ports
                    })
            except Exception as e:
                print(f"Could not get traffic data for device {device.get('name', device['serial'])}: {str(e)}")
                
        return device_traffic
    except Exception as e:
        print(f"Error getting device traffic: {str(e)}")
        return []

def analyze_client_traffic(client_traffic):
    """Analyze client traffic data and generate reports"""
    if not client_traffic:
        print("No client traffic data to analyze")
        return
    
    # Sort clients by total usage
    sorted_clients = sorted(client_traffic, key=lambda x: x['usage']['total'], reverse=True)
    
    # Calculate total usage
    total_sent = sum(client['usage']['sent'] for client in client_traffic)
    total_recv = sum(client['usage']['recv'] for client in client_traffic)
    total_usage = total_sent + total_recv
    
    # Group clients by manufacturer
    manufacturers = defaultdict(int)
    for client in client_traffic:
        manufacturers[client['manufacturer']] += client['usage']['total']
    
    # Create a timestamp for file naming
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save the client traffic data to a CSV file
    csv_filename = f"{OUTPUT_DIR}/client_traffic_{timestamp}.csv"
    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = ['Description', 'Hostname', 'IP', 'MAC', 'Manufacturer', 'OS', 'User', 'Sent (MB)', 'Received (MB)', 'Total (MB)']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for client in sorted_clients:
            writer.writerow({
                'Description': client['description'],
                'Hostname': client['dhcpHostname'],
                'IP': client['ip'],
                'MAC': client['mac'],
                'Manufacturer': client['manufacturer'],
                'OS': client['os'],
                'User': client['user'],
                'Sent (MB)': round(client['usage']['sent'] / (1024 * 1024), 2),
                'Received (MB)': round(client['usage']['recv'] / (1024 * 1024), 2),
                'Total (MB)': round(client['usage']['total'] / (1024 * 1024), 2)
            })
    
    print(f"Client traffic data saved to {csv_filename}")
    
    # Generate a summary report
    report_filename = f"{OUTPUT_DIR}/client_traffic_summary_{timestamp}.txt"
    with open(report_filename, 'w') as f:
        f.write(f"Network Traffic Summary - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("Total Traffic:\n")
        f.write(f"  Sent: {round(total_sent / (1024 * 1024), 2)} MB\n")
        f.write(f"  Received: {round(total_recv / (1024 * 1024), 2)} MB\n")
        f.write(f"  Total: {round(total_usage / (1024 * 1024), 2)} MB\n\n")
        
        f.write("Top 10 Clients by Traffic:\n")
        for i, client in enumerate(sorted_clients[:10], 1):
            f.write(f"  {i}. {client['description']} ({client['ip']}): {round(client['usage']['total'] / (1024 * 1024), 2)} MB\n")
        
        f.write("\nTraffic by Manufacturer:\n")
        for manufacturer, usage in sorted(manufacturers.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {manufacturer}: {round(usage / (1024 * 1024), 2)} MB\n")
    
    print(f"Client traffic summary saved to {report_filename}")
    
    # Generate a traffic chart
    try:
        # Create a pie chart of top 5 clients
        plt.figure(figsize=(10, 7))
        
        # Get top 5 clients and 'Others'
        top_clients = sorted_clients[:5]
        other_traffic = sum(client['usage']['total'] for client in sorted_clients[5:])
        
        labels = [f"{client['description']} ({client['ip']})" for client in top_clients]
        if other_traffic > 0:
            labels.append('Others')
        
        sizes = [client['usage']['total'] for client in top_clients]
        if other_traffic > 0:
            sizes.append(other_traffic)
        
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.axis('equal')
        plt.title('Network Traffic by Client')
        
        chart_filename = f"{OUTPUT_DIR}/client_traffic_chart_{timestamp}.png"
        plt.savefig(chart_filename)
        plt.close()
        
        print(f"Client traffic chart saved to {chart_filename}")
    except Exception as e:
        print(f"Error generating traffic chart: {str(e)}")

def analyze_application_traffic(app_traffic):
    """Analyze application traffic data and generate reports"""
    if not app_traffic:
        print("No application traffic data to analyze")
        return
    
    # Create a timestamp for file naming
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save the application traffic data to a CSV file
    csv_filename = f"{OUTPUT_DIR}/app_traffic_{timestamp}.csv"
    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = ['Application', 'Category', 'Received (MB)', 'Sent (MB)', 'Total (MB)']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for app in app_traffic:
            if 'application' in app and 'received' in app and 'sent' in app:
                writer.writerow({
                    'Application': app['application'],
                    'Category': app.get('category', 'Unknown'),
                    'Received (MB)': round(app['received'] / (1024 * 1024), 2),
                    'Sent (MB)': round(app['sent'] / (1024 * 1024), 2),
                    'Total (MB)': round((app['received'] + app['sent']) / (1024 * 1024), 2)
                })
    
    print(f"Application traffic data saved to {csv_filename}")
    
    # Generate a chart of top 10 applications
    try:
        # Sort applications by total traffic
        sorted_apps = sorted(app_traffic, key=lambda x: x.get('received', 0) + x.get('sent', 0), reverse=True)[:10]
        
        plt.figure(figsize=(12, 8))
        
        apps = [app['application'] for app in sorted_apps if 'application' in app]
        traffic = [(app.get('received', 0) + app.get('sent', 0)) / (1024 * 1024) for app in sorted_apps]
        
        plt.bar(apps, traffic)
        plt.xlabel('Application')
        plt.ylabel('Traffic (MB)')
        plt.title('Top 10 Applications by Traffic')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        chart_filename = f"{OUTPUT_DIR}/app_traffic_chart_{timestamp}.png"
        plt.savefig(chart_filename)
        plt.close()
        
        print(f"Application traffic chart saved to {chart_filename}")
    except Exception as e:
        print(f"Error generating application chart: {str(e)}")

def monitor_network_traffic():
    """Main function to monitor network traffic"""
    # Prompt for API key securely
    API_KEY = getpass.getpass("Enter your Meraki API key: ")
    
    if not API_KEY:
        print("API key is required. Exiting...")
        return
    
    # Initialize the Meraki dashboard
    dashboard = meraki.DashboardAPI(API_KEY, output_log=False, print_console=False)
    
    print(f"Starting Meraki Network Traffic Monitor")
    print(f"Organization: {ORG_NAME}")
    print(f"Network: {NETWORK_NAME}")
    
    try:
        # Get organization ID
        organizations = dashboard.organizations.getOrganizations()
        org_id = None
        
        for org in organizations:
            if org['name'] == ORG_NAME:
                org_id = org['id']
                break
        
        if not org_id:
            print(f"Organization '{ORG_NAME}' not found.")
            return
        
        # Get network ID
        networks = dashboard.organizations.getOrganizationNetworks(org_id)
        network_id = None
        
        for network in networks:
            if network['name'] == NETWORK_NAME:
                network_id = network['id']
                break
        
        if not network_id:
            print(f"Network '{NETWORK_NAME}' not found in organization.")
            return
        
        print(f"Found network: {NETWORK_NAME} (ID: {network_id})")
        
        # Ask for the time period to analyze
        print("\nSelect time period for traffic analysis:")
        print("1. Last hour")
        print("2. Last 3 hours")
        print("3. Last 12 hours")
        print("4. Last 24 hours")
        
        choice = input("Enter your choice (1-4): ")
        
        timespan = 3600  # Default to 1 hour
        if choice == "2":
            timespan = 10800  # 3 hours
        elif choice == "3":
            timespan = 43200  # 12 hours
        elif choice == "4":
            timespan = 86400  # 24 hours
            
        print(f"\nGathering traffic data for the past {timespan // 3600} hour(s)...")
        
        # Get client traffic
        print("\nFetching client traffic data...")
        client_traffic = get_client_traffic(dashboard, network_id, timespan)
        
        # Get application traffic
        print("\nFetching application traffic data...")
        app_traffic = get_application_traffic(dashboard, network_id, timespan)
        
        # Get device traffic
        print("\nFetching device traffic data...")
        device_traffic = get_device_traffic(dashboard, network_id)
        
        # Analyze and report on traffic
        print("\nAnalyzing client traffic...")
        analyze_client_traffic(client_traffic)
        
        print("\nAnalyzing application traffic...")
        analyze_application_traffic(app_traffic)
        
        # Export raw data as JSON
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"{OUTPUT_DIR}/raw_traffic_data_{timestamp}.json", 'w') as f:
            json.dump({
                'clientTraffic': client_traffic,
                'applicationTraffic': app_traffic,
                'deviceTraffic': device_traffic
            }, f, indent=2)
            
        print(f"\nRaw traffic data exported to {OUTPUT_DIR}/raw_traffic_data_{timestamp}.json")
        print("\nTraffic analysis complete!")
        
    except meraki.APIError as e:
        print(f"Meraki API Error: {str(e)}")
        print("Please check if your API key is correct and has sufficient permissions.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    monitor_network_traffic()
