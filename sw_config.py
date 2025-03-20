import meraki
import os
import json
from datetime import datetime
import getpass

# Your Meraki organization and network information
ORG_NAME = "CANADA MTN REGION"
NETWORK_NAME = "CA-HA562-HSIA"
OUTPUT_DIR = "switch_configs"  # Directory to save the configurations

# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def main():
    # Prompt for API key securely (input won't be visible when typing)
    API_KEY = getpass.getpass("Enter your Meraki API key: ")
    
    if not API_KEY:
        print("API key is required. Exiting...")
        return
    
    # Initialize the Meraki dashboard
    dashboard = meraki.DashboardAPI(API_KEY, output_log=False, print_console=False)
    
    print(f"Starting configuration backup for organization: {ORG_NAME}")
    print(f"Looking for network: {NETWORK_NAME}")
    
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
        
        print(f"Found organization ID: {org_id}")
        
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
        
        print(f"Found network ID: {network_id}")
        
        # Get all devices in the network
        devices = dashboard.networks.getNetworkDevices(network_id)
        
        # Filter for switches only
        switches = [device for device in devices if device['model'].startswith('MS')]
        
        if not switches:
            print("No switches found in the network.")
            return
        
        print(f"Found {len(switches)} switches in the network.")
        
        # Get and save configuration for each switch
        for switch in switches:
            switch_serial = switch['serial']
            switch_name = switch.get('name', switch_serial)
            
            print(f"Backing up configuration for switch: {switch_name} ({switch_serial})")
            
            try:
                # Get switch configuration
                switch_config = dashboard.switch.getDeviceSwitchRoutingInterfaces(switch_serial)
                port_configs = dashboard.switch.getDeviceSwitchPorts(switch_serial)
                
                # Create a comprehensive configuration object
                full_config = {
                    "deviceInfo": switch,
                    "routingInterfaces": switch_config,
                    "ports": port_configs,
                    "backupDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Try to get additional configuration details if available
                try:
                    vlans = dashboard.switch.getDeviceSwitchRoutingStaticRoutes(switch_serial)
                    full_config["staticRoutes"] = vlans
                except:
                    print(f"  Note: No static routes available for {switch_name}")
                
                try:
                    acls = dashboard.switch.getNetworkSwitchAccessControlLists(network_id)
                    full_config["acls"] = acls
                except:
                    print(f"  Note: No ACLs available for network")
                
                # Save the configuration to a file
                filename = f"{OUTPUT_DIR}/{switch_name}_{switch_serial}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                
                with open(filename, 'w') as f:
                    f.write(f"Configuration for {switch_name} ({switch_serial})\n")
                    f.write(f"Backup Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Network: {NETWORK_NAME}\n")
                    f.write(f"Organization: {ORG_NAME}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    # Write device info
                    f.write("DEVICE INFORMATION:\n")
                    f.write("-" * 80 + "\n")
                    for key, value in switch.items():
                        f.write(f"{key}: {value}\n")
                    f.write("\n")
                    
                    # Write routing interfaces
                    f.write("ROUTING INTERFACES:\n")
                    f.write("-" * 80 + "\n")
                    f.write(json.dumps(switch_config, indent=4))
                    f.write("\n\n")
                    
                    # Write port configurations
                    f.write("PORT CONFIGURATIONS:\n")
                    f.write("-" * 80 + "\n")
                    f.write(json.dumps(port_configs, indent=4))
                    f.write("\n\n")
                    
                    # Write static routes if available
                    if "staticRoutes" in full_config:
                        f.write("STATIC ROUTES:\n")
                        f.write("-" * 80 + "\n")
                        f.write(json.dumps(full_config["staticRoutes"], indent=4))
                        f.write("\n\n")
                    
                    # Write ACLs if available
                    if "acls" in full_config:
                        f.write("ACCESS CONTROL LISTS:\n")
                        f.write("-" * 80 + "\n")
                        f.write(json.dumps(full_config["acls"], indent=4))
                        f.write("\n\n")
                
                print(f"  Configuration saved to {filename}")
                
            except Exception as e:
                print(f"  Error getting configuration for {switch_name}: {str(e)}")
        
        print("Configuration backup complete!")
        
    except meraki.APIError as e:
        print(f"Meraki API Error: {str(e)}")
        print("Please check if your API key is correct and has sufficient permissions.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
    
