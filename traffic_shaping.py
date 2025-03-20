import meraki
import getpass
import json
import sys

# Your Meraki organization and network information
ORG_NAME = "CANADA MTN REGION"
NETWORK_NAME = "CA-HA562-HSIA"

def configure_traffic_shaping(dashboard, network_id):
    """
    Configure traffic shaping for a specific network
    """
    print("\n=== Traffic Shaping Configuration ===")
    print("1. Configure global bandwidth limits")
    print("2. Configure per-client bandwidth limits")
    print("3. Configure traffic shaping rules")
    print("4. View current traffic shaping configuration")
    print("5. Return to main menu")
    
    choice = input("\nEnter your choice (1-5): ")
    
    if choice == "1":
        configure_global_bandwidth(dashboard, network_id)
    elif choice == "2":
        configure_client_bandwidth(dashboard, network_id)
    elif choice == "3":
        configure_shaping_rules(dashboard, network_id)
    elif choice == "4":
        view_current_config(dashboard, network_id)
    elif choice == "5":
        return
    else:
        print("Invalid choice. Please try again.")
    
    # Return to traffic shaping menu
    configure_traffic_shaping(dashboard, network_id)

def configure_global_bandwidth(dashboard, network_id):
    """Configure global bandwidth limits for the network"""
    try:
        # Get current settings first
        current_settings = dashboard.networks.getNetworkTrafficShaping(network_id)
        print("\nCurrent Global Bandwidth Settings:")
        print(json.dumps(current_settings, indent=2))
        
        print("\nConfigure new global bandwidth limits:")
        
        # Ask for new settings
        apply_global = input("Apply global bandwidth limits? (yes/no): ").lower() == "yes"
        
        if not apply_global:
            dashboard.networks.updateNetworkTrafficShaping(
                network_id,
                globalBandwidthLimits={
                    "limitUp": None,
                    "limitDown": None
                }
            )
            print("Global bandwidth limits disabled.")
            return
        
        # Get bandwidth limits
        limit_up = input("Enter upload limit in Kbps (or press Enter to leave unchanged): ")
        limit_down = input("Enter download limit in Kbps (or press Enter to leave unchanged): ")
        
        # Prepare update data
        update_data = {"globalBandwidthLimits": {}}
        
        if limit_up:
            update_data["globalBandwidthLimits"]["limitUp"] = int(limit_up)
        else:
            update_data["globalBandwidthLimits"]["limitUp"] = current_settings.get("globalBandwidthLimits", {}).get("limitUp")
            
        if limit_down:
            update_data["globalBandwidthLimits"]["limitDown"] = int(limit_down)
        else:
            update_data["globalBandwidthLimits"]["limitDown"] = current_settings.get("globalBandwidthLimits", {}).get("limitDown")
        
        # Update network
        dashboard.networks.updateNetworkTrafficShaping(network_id, **update_data)
        print("Global bandwidth limits updated successfully.")
        
    except Exception as e:
        print(f"Error configuring global bandwidth: {str(e)}")

def configure_client_bandwidth(dashboard, network_id):
    """Configure per-client bandwidth limits for the network"""
    try:
        # Get current settings first
        current_settings = dashboard.networks.getNetworkTrafficShaping(network_id)
        print("\nCurrent Per-Client Bandwidth Settings:")
        print(json.dumps(current_settings.get("perClientBandwidthLimits", {}), indent=2))
        
        print("\nConfigure new per-client bandwidth limits:")
        
        # Ask for new settings
        apply_client = input("Apply per-client bandwidth limits? (yes/no): ").lower() == "yes"
        
        if not apply_client:
            dashboard.networks.updateNetworkTrafficShaping(
                network_id,
                perClientBandwidthLimits={
                    "settings": "disabled"
                }
            )
            print("Per-client bandwidth limits disabled.")
            return
        
        # Get bandwidth limits
        limit_up = input("Enter client upload limit in Kbps (or press Enter to leave unchanged): ")
        limit_down = input("Enter client download limit in Kbps (or press Enter to leave unchanged): ")
        
        # Prepare update data
        update_data = {
            "perClientBandwidthLimits": {
                "settings": "custom"
            }
        }
        
        if limit_up:
            update_data["perClientBandwidthLimits"]["bandwidthLimits"] = {
                "limitUp": int(limit_up)
            }
        else:
            current_limit = current_settings.get("perClientBandwidthLimits", {}).get("bandwidthLimits", {}).get("limitUp")
            if current_limit:
                update_data["perClientBandwidthLimits"]["bandwidthLimits"] = {
                    "limitUp": current_limit
                }
            
        if limit_down:
            if "bandwidthLimits" not in update_data["perClientBandwidthLimits"]:
                update_data["perClientBandwidthLimits"]["bandwidthLimits"] = {}
            update_data["perClientBandwidthLimits"]["bandwidthLimits"]["limitDown"] = int(limit_down)
        else:
            current_limit = current_settings.get("perClientBandwidthLimits", {}).get("bandwidthLimits", {}).get("limitDown")
            if current_limit:
                if "bandwidthLimits" not in update_data["perClientBandwidthLimits"]:
                    update_data["perClientBandwidthLimits"]["bandwidthLimits"] = {}
                update_data["perClientBandwidthLimits"]["bandwidthLimits"]["limitDown"] = current_limit
        
        # Update network
        dashboard.networks.updateNetworkTrafficShaping(network_id, **update_data)
        print("Per-client bandwidth limits updated successfully.")
        
    except Exception as e:
        print(f"Error configuring per-client bandwidth: {str(e)}")

def configure_shaping_rules(dashboard, network_id):
    """Configure traffic shaping rules for the network"""
    try:
        # Get current rules
        current_rules = dashboard.networks.getNetworkTrafficShaping(network_id)
        print("\nCurrent Traffic Shaping Rules:")
        if "rules" in current_rules:
            for i, rule in enumerate(current_rules["rules"], 1):
                print(f"\nRule {i}:")
                print(json.dumps(rule, indent=2))
        else:
            print("No traffic shaping rules configured.")
        
        print("\nTraffic Shaping Rules Options:")
        print("1. Add a new rule")
        print("2. Delete a rule")
        print("3. Return to traffic shaping menu")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            add_traffic_rule(dashboard, network_id, current_rules)
        elif choice == "2":
            delete_traffic_rule(dashboard, network_id, current_rules)
        elif choice == "3":
            return
        else:
            print("Invalid choice. Please try again.")
            configure_shaping_rules(dashboard, network_id)
            
    except Exception as e:
        print(f"Error configuring traffic shaping rules: {str(e)}")

def add_traffic_rule(dashboard, network_id, current_rules):
    """Add a new traffic shaping rule"""
    try:
        print("\n=== Add Traffic Shaping Rule ===")
        
        # Create a new rule
        new_rule = {}
        
        # Define the rule
        print("\nRule definition:")
        
        # Define rule type
        print("Rule types:")
        print("1. Application")
        print("2. Application Category")
        print("3. Host")
        print("4. Port")
        print("5. IP Range")
        
        rule_type_choice = input("Enter rule type (1-5): ")
        
        if rule_type_choice == "1":
            new_rule["type"] = "application"
            new_rule["value"] = input("Enter application name (e.g., 'Netflix'): ")
        elif rule_type_choice == "2":
            new_rule["type"] = "applicationCategory"
            new_rule["value"] = input("Enter application category (e.g., 'Video & Music'): ")
        elif rule_type_choice == "3":
            new_rule["type"] = "host"
            new_rule["value"] = input("Enter hostname (e.g., 'google.com'): ")
        elif rule_type_choice == "4":
            new_rule["type"] = "port"
            new_rule["value"] = input("Enter port (e.g., '80'): ")
        elif rule_type_choice == "5":
            new_rule["type"] = "ipRange"
            new_rule["value"] = input("Enter IP range (e.g., '192.168.1.0/24'): ")
        else:
            print("Invalid choice. Rule will not be added.")
            return
        
        # Define traffic definition
        print("\nTraffic direction:")
        print("1. Source")
        print("2. Destination")
        print("3. Any")
        
        direction_choice = input("Enter traffic direction (1-3): ")
        
        if direction_choice == "1":
            new_rule["definition"] = {"type": "src"}
        elif direction_choice == "2":
            new_rule["definition"] = {"type": "dst"}
        else:
            new_rule["definition"] = {"type": "any"}
        
        # Define rule action
        print("\nRule action:")
        
        # DSCP tagging
        dscp_tag = input("Set DSCP tag (0-63, or press Enter to skip): ")
        if dscp_tag:
            if "perClientBandwidthLimits" not in new_rule:
                new_rule["perClientBandwidthLimits"] = {}
            new_rule["dscpTagValue"] = int(dscp_tag)
        
        # Bandwidth limits
        apply_bw_limits = input("Apply bandwidth limits? (yes/no): ").lower() == "yes"
        if apply_bw_limits:
            limit_up = input("Enter upload limit in Kbps: ")
            limit_down = input("Enter download limit in Kbps: ")
            
            new_rule["perClientBandwidthLimits"] = {
                "settings": "custom",
                "bandwidthLimits": {}
            }
            
            if limit_up:
                new_rule["perClientBandwidthLimits"]["bandwidthLimits"]["limitUp"] = int(limit_up)
            if limit_down:
                new_rule["perClientBandwidthLimits"]["bandwidthLimits"]["limitDown"] = int(limit_down)
        
        # Add the rule to existing rules
        rules = current_rules.get("rules", [])
        rules.append(new_rule)
        
        # Update the network with new rules
        dashboard.networks.updateNetworkTrafficShaping(network_id, rules=rules)
        print("Traffic shaping rule added successfully.")
        
    except Exception as e:
        print(f"Error adding traffic rule: {str(e)}")

def delete_traffic_rule(dashboard, network_id, current_rules):
    """Delete a traffic shaping rule"""
    try:
        if "rules" not in current_rules or not current_rules["rules"]:
            print("No rules to delete.")
            return
        
        print("\n=== Delete Traffic Shaping Rule ===")
        
        # Display existing rules
        for i, rule in enumerate(current_rules["rules"], 1):
            rule_type = rule.get("type", "unknown")
            rule_value = rule.get("value", "unknown")
            print(f"{i}. {rule_type}: {rule_value}")
        
        # Get rule to delete
        rule_index = int(input("\nEnter rule number to delete (or 0 to cancel): "))
        
        if rule_index == 0:
            return
        
        if rule_index < 1 or rule_index > len(current_rules["rules"]):
            print("Invalid rule number.")
            return
        
        # Remove the rule
        rules = current_rules["rules"]
        del rules[rule_index - 1]
        
        # Update the network with new rules
        dashboard.networks.updateNetworkTrafficShaping(network_id, rules=rules)
        print("Traffic shaping rule deleted successfully.")
        
    except Exception as e:
        print(f"Error deleting traffic rule: {str(e)}")

def view_current_config(dashboard, network_id):
    """View current traffic shaping configuration"""
    try:
        current_settings = dashboard.networks.getNetworkTrafficShaping(network_id)
        print("\n=== Current Traffic Shaping Configuration ===")
        print(json.dumps(current_settings, indent=2))
        
        input("\nPress Enter to continue...")
        
    except Exception as e:
        print(f"Error viewing configuration: {str(e)}")

def main():
    # Prompt for API key securely
    API_KEY = getpass.getpass("Enter your Meraki API key: ")
    
    if not API_KEY:
        print("API key is required. Exiting...")
        return
    
    # Initialize the Meraki dashboard
    dashboard = meraki.DashboardAPI(API_KEY, output_log=False, print_console=False)
    
    print(f"Starting Meraki Traffic Shaping Configuration Tool")
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
        
        # Main menu
        while True:
            print("\n=== Meraki Traffic Shaping Configuration Tool ===")
            print("1. Configure traffic shaping")
            print("2. Exit")
            
            choice = input("\nEnter your choice (1-2): ")
            
            if choice == "1":
                configure_traffic_shaping(dashboard, network_id)
            elif choice == "2":
                print("Exiting...")
                sys.exit(0)
            else:
                print("Invalid choice. Please try again.")
        
    except meraki.APIError as e:
        print(f"Meraki API Error: {str(e)}")
        print("Please check if your API key is correct and has sufficient permissions.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
