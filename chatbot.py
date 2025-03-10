import streamlit as st
import requests
import json
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

class MerakiAPI:
    def __init__(self, api_key=None):
        self.base_url = "https://api.meraki.com/api/v1"
        self.api_key = api_key
        self.headers = {
            "X-Cisco-Meraki-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def set_api_key(self, api_key):
        """Set or update the API key"""
        self.api_key = api_key
        self.headers["X-Cisco-Meraki-API-Key"] = self.api_key
        return True

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
                st.warning(f"Rate limit hit. Waiting for {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(method, endpoint, params, data)
                
            return response
        except requests.exceptions.RequestException as e:
            st.error(f"Request error: {str(e)}")
            return None

    def get_organizations(self):
        """Get all organizations the API key has access to"""
        endpoint = f"{self.base_url}/organizations"
        response = self._make_request("GET", endpoint)
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to retrieve organizations. Status code: {response.status_code if response else 'N/A'}")
            return []

    def get_networks(self, org_id):
        """Get all networks in an organization"""
        endpoint = f"{self.base_url}/organizations/{org_id}/networks"
        response = self._make_request("GET", endpoint)
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to retrieve networks. Status code: {response.status_code if response else 'N/A'}")
            return []

    def get_devices(self, network_id):
        """Get all devices in a network"""
        endpoint = f"{self.base_url}/networks/{network_id}/devices"
        response = self._make_request("GET", endpoint)
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to retrieve devices. Status code: {response.status_code if response else 'N/A'}")
            return []

    def get_ssids(self, network_id):
        """Get all SSIDs in a network"""
        endpoint = f"{self.base_url}/networks/{network_id}/wireless/ssids"
        response = self._make_request("GET", endpoint)
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to retrieve SSIDs. Status code: {response.status_code if response else 'N/A'}")
            return []
    
    def get_clients(self, network_id, timespan=3600):
        """Get clients in a network"""
        endpoint = f"{self.base_url}/networks/{network_id}/clients"
        params = {"timespan": timespan}
        response = self._make_request("GET", endpoint, params=params)
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to retrieve clients. Status code: {response.status_code if response else 'N/A'}")
            return []
    
    def get_vpn_status(self, network_id):
        """Get VPN status for a network"""
        endpoint = f"{self.base_url}/networks/{network_id}/appliance/vpn/status"
        response = self._make_request("GET", endpoint)
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to retrieve VPN status. Status code: {response.status_code if response else 'N/A'}")
            return {}
    
    def get_network_traffic(self, network_id, timespan=86400):
        """Get network traffic data"""
        endpoint = f"{self.base_url}/networks/{network_id}/traffic"
        params = {"timespan": timespan}
        response = self._make_request("GET", endpoint, params=params)
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to retrieve traffic data. Status code: {response.status_code if response else 'N/A'}")
            return []
    
    def get_device_status(self, network_id, serial):
        """Get status information for a specific device"""
        endpoint = f"{self.base_url}/networks/{network_id}/devices/{serial}/statuses"
        response = self._make_request("GET", endpoint)
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to retrieve device status. Status code: {response.status_code if response else 'N/A'}")
            return {}

    def get_organization_summary(self, org_id):
        """Get organization summary information"""
        endpoint = f"{self.base_url}/organizations/{org_id}/summary"
        params = {"total_pages": "all"}
        response = self._make_request("GET", endpoint, params=params)
        
        if response and response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to retrieve organization summary. Status code: {response.status_code if response else 'N/A'}")
            return {}

def initialize_session_state():
    """Initialize session state variables if they don't exist"""
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None
    if 'meraki_api' not in st.session_state:
        st.session_state.meraki_api = MerakiAPI()
    if 'organizations' not in st.session_state:
        st.session_state.organizations = []
    if 'selected_org' not in st.session_state:
        st.session_state.selected_org = None
    if 'networks' not in st.session_state:
        st.session_state.networks = []
    if 'selected_network' not in st.session_state:
        st.session_state.selected_network = None
    if 'devices' not in st.session_state:
        st.session_state.devices = []
    if 'selected_device' not in st.session_state:
        st.session_state.selected_device = None
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "Dashboard"

def sidebar_navigation():
    """Create the sidebar navigation"""
    st.sidebar.title("Meraki Dashboard")
    
    # Only show API key input if not authenticated
    if not st.session_state.authenticated:
        with st.sidebar.form("api_key_form"):
            api_key = st.text_input("Enter Meraki API Key", type="password")
            submit = st.form_submit_button("Connect")
            
            if submit and api_key:
                st.session_state.meraki_api.set_api_key(api_key)
                organizations = st.session_state.meraki_api.get_organizations()
                
                if organizations:
                    st.session_state.authenticated = True
                    st.session_state.api_key = api_key
                    st.session_state.organizations = organizations
                    st.session_state.selected_org = organizations[0]['id'] if organizations else None
                    st.experimental_rerun()
    
    # Navigation for authenticated users
    if st.session_state.authenticated:
        # Organization selector
        org_names = [org['name'] for org in st.session_state.organizations]
        org_ids = [org['id'] for org in st.session_state.organizations]
        
        selected_org_index = 0
        if st.session_state.selected_org:
            try:
                selected_org_index = org_ids.index(st.session_state.selected_org)
            except ValueError:
                selected_org_index = 0
        
        selected_org_name = st.sidebar.selectbox(
            "Select Organization", 
            org_names,
            index=selected_org_index
        )
        
        # Update selected organization
        selected_org_index = org_names.index(selected_org_name)
        st.session_state.selected_org = org_ids[selected_org_index]
        
        # Fetch networks if organization is selected
        if st.session_state.selected_org and (not st.session_state.networks or 
                                              st.session_state.networks[0]['organizationId'] != st.session_state.selected_org):
            with st.sidebar:
                with st.spinner("Loading networks..."):
                    st.session_state.networks = st.session_state.meraki_api.get_networks(st.session_state.selected_org)
        
        # Navigation tabs
        st.sidebar.title("Navigation")
        tabs = ["Dashboard", "Networks", "Devices", "Wireless", "Clients", "Security", "Analytics"]
        
        selected_tab = st.sidebar.radio("Go to", tabs, index=tabs.index(st.session_state.active_tab))
        st.session_state.active_tab = selected_tab

        # Add a button to log out
        if st.sidebar.button("Log Out"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.experimental_rerun()

def display_dashboard():
    """Display the main dashboard"""
    st.title("Meraki Network Dashboard")
    
    if not st.session_state.selected_org:
        st.info("Please select an organization from the sidebar.")
        return
    
    # Get the selected organization
    org_id = st.session_state.selected_org
    org_name = next((org['name'] for org in st.session_state.organizations if org['id'] == org_id), "Unknown")
    
    # Basic organization info
    st.header(f"Organization: {org_name}")
    
    if not st.session_state.networks:
        st.info("No networks found for this organization.")
        return
    
    # Dashboard metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Networks", len(st.session_state.networks))
    
    # Count devices across all networks
    total_devices = 0
    wireless_networks = 0
    
    for network in st.session_state.networks:
        # Check if wireless is in productTypes
        if 'wireless' in [pt.lower() for pt in network.get('productTypes', [])]:
            wireless_networks += 1
    
    with col2:
        st.metric("Wireless Networks", wireless_networks)
    
    # Get device counts (this would be better if cached)
    all_devices = []
    for network in st.session_state.networks[:5]:  # Limit to first 5 to avoid too many API calls
        devices = st.session_state.meraki_api.get_devices(network['id'])
        all_devices.extend(devices)
    
    with col3:
        st.metric("Total Devices", len(all_devices))
    
    # Count device types
    ap_count = sum(1 for device in all_devices if device.get('model', '').startswith(('MR', 'CW')))
    
    with col4:
        st.metric("Access Points", ap_count)
    
    # Create tabs for dashboard sections
    dash_tab1, dash_tab2, dash_tab3 = st.tabs(["Network Overview", "Device Status", "Recent Alerts"])
    
    with dash_tab1:
        # Network overview section
        st.subheader("Network Distribution")
        
        # Create a dataframe with network types
        network_types = {}
        for network in st.session_state.networks:
            for product_type in network.get('productTypes', []):
                if product_type in network_types:
                    network_types[product_type] += 1
                else:
                    network_types[product_type] = 1
        
        if network_types:
            df_network_types = pd.DataFrame({
                'Product Type': list(network_types.keys()),
                'Count': list(network_types.values())
            })
            
            fig = px.pie(df_network_types, values='Count', names='Product Type', 
                        title='Networks by Product Type')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No network type data available.")
    
    with dash_tab2:
        # Device status
        st.subheader("Device Status Overview")
        
        if all_devices:
            # Create a simple device status table
            device_data = []
            for device in all_devices:
                device_data.append({
                    'Name': device.get('name', 'Unnamed'),
                    'Model': device.get('model', 'Unknown'),
                    'Serial': device.get('serial', 'Unknown'),
                    'Status': 'Online' if device.get('status') == 'online' else 'Offline',
                    'Network': next((net['name'] for net in st.session_state.networks 
                                   if net['id'] == device.get('networkId')), 'Unknown')
                })
            
            df_devices = pd.DataFrame(device_data)
            st.dataframe(df_devices, use_container_width=True)
            
            # Device status pie chart
            status_counts = df_devices['Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            
            fig = px.pie(status_counts, values='Count', names='Status', 
                        title='Device Status Distribution', 
                        color='Status', 
                        color_discrete_map={'Online': 'green', 'Offline': 'red'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No device data available.")
    
    with dash_tab3:
        # Placeholder for alerts (would need additional API calls)
        st.subheader("Recent Alerts")
        st.info("Alert data would be displayed here. This would require additional API integration.")
        
        # Mock alerts for visual example
        mock_alerts = [
            {"severity": "High", "type": "Device went down", "device": "AP-Conference-Room", "time": "10 min ago"},
            {"severity": "Medium", "type": "High client count", "device": "AP-Lobby", "time": "32 min ago"},
            {"severity": "Low", "type": "Configuration changed", "device": "SW-Floor1", "time": "1 hour ago"},
        ]
        
        for alert in mock_alerts:
            severity_color = "red" if alert["severity"] == "High" else "orange" if alert["severity"] == "Medium" else "blue"
            st.markdown(f"""
            <div style="padding: 10px; border-left: 5px solid {severity_color}; margin-bottom: 10px;">
                <strong>{alert["severity"]}</strong>: {alert["type"]} - {alert["device"]} ({alert["time"]})
            </div>
            """, unsafe_allow_html=True)

def display_networks():
    """Display networks view"""
    st.title("Networks")
    
    if not st.session_state.selected_org:
        st.info("Please select an organization from the sidebar.")
        return
    
    if not st.session_state.networks:
        st.info("No networks found for this organization.")
        return
    
    # Create a table of networks
    network_data = []
    for network in st.session_state.networks:
        network_data.append({
            'Name': network.get('name', 'Unnamed'),
            'ID': network.get('id', 'Unknown'),
            'Types': ', '.join(network.get('productTypes', [])),
            'Tags': ', '.join(network.get('tags', [])),
            'Time Zone': network.get('timeZone', 'Unknown')
        })
    
    df_networks = pd.DataFrame(network_data)
    
    # Filter options
    with st.expander("Filter Networks"):
        network_types = set()
        for network in st.session_state.networks:
            for product_type in network.get('productTypes', []):
                network_types.add(product_type)
        
        selected_types = st.multiselect("Filter by Network Type", list(network_types))
        search_term = st.text_input("Search by Name")
        
        if selected_types:
            df_networks = df_networks[df_networks['Types'].apply(lambda x: any(net_type in x for net_type in selected_types))]
        
        if search_term:
            df_networks = df_networks[df_networks['Name'].str.contains(search_term, case=False)]
    
    # Display the filtered networks
    st.dataframe(df_networks, use_container_width=True)
    
    # Select a network for detailed view
    selected_network_name = st.selectbox(
        "Select a network for details", 
        [network['name'] for network in st.session_state.networks]
    )
    
    selected_network = next((network for network in st.session_state.networks 
                           if network['name'] == selected_network_name), None)
    
    if selected_network:
        st.session_state.selected_network = selected_network['id']
        
        st.subheader(f"Network Details: {selected_network['name']}")
        
        # Create tabs for network details
        net_tab1, net_tab2 = st.tabs(["Network Information", "Network Status"])
        
        with net_tab1:
            # Display network information
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Network ID:** " + selected_network['id'])
                st.markdown("**Product Types:** " + ", ".join(selected_network.get('productTypes', [])))
                st.markdown("**Time Zone:** " + selected_network.get('timeZone', 'Not set'))
            
            with col2:
                st.markdown("**Tags:** " + (", ".join(selected_network.get('tags', [])) if selected_network.get('tags') else 'None'))
                st.markdown("**Notes:** " + (selected_network.get('notes', 'None')))
        
        with net_tab2:
            # Network status info would go here (requires additional API calls)
            st.info("Loading network status...")
            
            # Get network devices
            devices = st.session_state.meraki_api.get_devices(selected_network['id'])
            
            if devices:
                st.success(f"Network has {len(devices)} devices")
                
                # Device table
                device_data = []
                for device in devices:
                    device_data.append({
                        'Name': device.get('name', 'Unnamed'),
                        'Model': device.get('model', 'Unknown'),
                        'Serial': device.get('serial', 'Unknown'),
                        'MAC': device.get('mac', 'Unknown'),
                        'Status': device.get('status', 'Unknown')
                    })
                
                df_devices = pd.DataFrame(device_data)
                st.dataframe(df_devices, use_container_width=True)
            else:
                st.warning("No devices found for this network")

def display_devices():
    """Display devices view"""
    st.title("Devices")
    
    if not st.session_state.selected_org:
        st.info("Please select an organization from the sidebar.")
        return
    
    if not st.session_state.networks:
        st.info("No networks found for this organization.")
        return
    
    # Select a network
    selected_network_name = st.selectbox(
        "Select a network", 
        [network['name'] for network in st.session_state.networks]
    )
    
    selected_network = next((network for network in st.session_state.networks 
                           if network['name'] == selected_network_name), None)
    
    if not selected_network:
        st.info("Please select a network.")
        return
    
    st.session_state.selected_network = selected_network['id']
    
    # Get devices for the selected network
    with st.spinner("Loading devices..."):
        devices = st.session_state.meraki_api.get_devices(selected_network['id'])
    
    if not devices:
        st.info("No devices found in this network.")
        return
    
    # Create device overview
    st.subheader("Device Overview")
    
    # Device type distribution
    device_types = {}
    for device in devices:
        model = device.get('model', 'Unknown')
        device_type = 'Unknown'
        
        if model.startswith('MR'):
            device_type = 'Wireless AP'
        elif model.startswith('MS'):
            device_type = 'Switch'
        elif model.startswith('MX'):
            device_type = 'Security Appliance'
        elif model.startswith('MV'):
            device_type = 'Camera'
        elif model.startswith('MT'):
            device_type = 'Sensor'
        
        if device_type in device_types:
            device_types[device_type] += 1
        else:
            device_types[device_type] = 1
    
    # Display as a horizontal bar chart
    if device_types:
        df_device_types = pd.DataFrame({
            'Device Type': list(device_types.keys()),
            'Count': list(device_types.values())
        })
        
        fig = px.bar(df_device_types, x='Count', y='Device Type', 
                    title='Device Types in Network',
                    orientation='h')
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed device list
    st.subheader("Device List")
    
    # Filter options
    with st.expander("Filter Devices"):
        device_models = set(device.get('model', 'Unknown') for device in devices)
        selected_models = st.multiselect("Filter by Model", list(device_models))
        device_search = st.text_input("Search by Name or Serial")
    
    # Prepare device data
    device_data = []
    for device in devices:
        device_data.append({
            'Name': device.get('name', 'Unnamed'),
            'Model': device.get('model', 'Unknown'),
            'Serial': device.get('serial', 'Unknown'),
            'MAC': device.get('mac', 'Unknown'),
            'Status': device.get('status', 'Unknown'),
            'IP': device.get('lanIp', 'Unknown')
        })
    
    df_devices = pd.DataFrame(device_data)
    
    # Apply filters
    if selected_models:
        df_devices = df_devices[df_devices['Model'].isin(selected_models)]
    
    if device_search:
        name_mask = df_devices['Name'].str.contains(device_search, case=False, na=False)
        serial_mask = df_devices['Serial'].str.contains(device_search, case=False, na=False)
        df_devices = df_devices[name_mask | serial_mask]
    
    # Display the filtered device table
    st.dataframe(df_devices, use_container_width=True)
    
    # Select a device for detailed view
    if not df_devices.empty:
        selected_device_name = st.selectbox(
            "Select a device for details", 
            df_devices['Name'].tolist()
        )
        
        selected_device = df_devices[df_devices['Name'] == selected_device_name].iloc[0]
        
        # Display device details
        st.subheader(f"Device Details: {selected_device['Name']}")
        
        device_tabs = st.tabs(["Device Information", "Status", "Performance"])
        
        with device_tabs[0]:
            # Basic device info
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Model:** {selected_device['Model']}")
                st.markdown(f"**Serial:** {selected_device['Serial']}")
                st.markdown(f"**MAC Address:** {selected_device['MAC']}")
            
            with col2:
                st.markdown(f"**IP Address:** {selected_device['IP']}")
                st.markdown(f"**Status:** {selected_device['Status']}")
                st.markdown(f"**Network:** {selected_network_name}")

def display_wireless():
    """Display wireless view"""
    st.title("Wireless")
    
    if not st.session_state.selected_org:
        st.info("Please select an organization from the sidebar.")
        return
    
    if not st.session_state.networks:
        st.info("No networks found for this organization.")
        return
    
    # Filter for wireless networks
    wireless_networks = [network for network in st.session_state.networks 
                        if 'wireless' in [pt.lower() for pt in network.get('productTypes', [])]]
    
    if not wireless_networks:
        st.info("No wireless networks found in this organization.")
        return
    
    # Select a wireless network
    selected_wireless_name = st.selectbox(
        "Select a wireless network", 
        [network['name'] for network in wireless_networks]
    )
    
    selected_wireless = next((network for network in wireless_networks 
                            if network['name'] == selected_wireless_name), None)
    
    if not selected_wireless:
        return
    
    st.session_state.selected_network = selected_wireless['id']
    
    # Get SSIDs for the selected network
    with st.spinner("Loading wireless data..."):
        ssids = st.session_state.meraki_api.get_ssids(selected_wireless['id'])
    
    if not ssids:
        st.info("No SSIDs found for this network.")
        return
    
    # Display SSID information
    st.subheader("Wireless SSIDs")
    
    # Create SSID cards
    ssid_cols = st.columns(3)
    
    for i, ssid in enumerate(ssids):
        col_index = i % 3
        with ssid_cols[col_index]:
            enabled_status = "✅ Enabled" if ssid.get('enabled', False) else "❌ Disabled"
            status_color = "green" if ssid.get('enabled', False) else "red"
            
            st.markdown(f"""
            <div style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                <h3 style="margin-top: 0;">{ssid.get('name', 'Unnamed SSID')}</h3>
                <p style="color: {status_color};">{enabled_status}</p>
                <p><strong>Authentication:</strong> {ssid.get('authMode', 'Unknown')}</p>
                <p><strong>Encryption:</strong> {ssid.get('encryptionMode', 'None')}</p>
                <p><strong>Visibility:</strong> {"Hidden" if ssid.get('hidden', False) else "Visible"}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Wireless stats and clients
    wireless_tabs = st.tabs(["Wireless Status", "Client Distribution", "Signal Quality"])
    
    with wireless_tabs[0]:
        st.subheader("Wireless Health")
        # This would need additional API calls for actual data
        
        # Mock data for visualization
        health_data = {
            'SSID': [ssid.get('name', f"SSID {i}") for i, ssid in enumerate(ssids) if ssid.get('enabled', False)],
            'Client Count': [85, 42, 13],  # Mock data
            'Channel Utilization': [65, 42, 28],  # Mock data
            'Interference': [12, 8, 22]  # Mock data
        }
        
        if health_data['SSID']:
            df_health = pd.DataFrame(health_data)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_health['SSID'],
                y=df_health['Client Count'],
                name='Client Count'
            ))
            
            fig.add_trace(go.Bar(
                x=df_health['SSID'],
                y=df_health['Channel Utilization'],
                name='Channel Utilization (%)'
            ))
            
            fig.add_trace(go.Bar(
                x=df_health['SSID'],
                y=df_health['Interference'],
                name='Interference (%)'
            ))
            
            fig.update_layout(
                title='Wireless Health Metrics by SSID',
                xaxis_title='SSID',
                yaxis_title='Value',
                barmode='group'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No enabled SSIDs found for wireless health data.")

def display_clients():
    """Display clients view"""
    st.title("Clients")
    
    if not st.session_state.selected_org:
        st.info("Please select an organization from the sidebar.")
        return
    
    if not st.session_state.networks:
        st.info("No networks found for this organization.")
        return
    
    # Select a network
    selected_network_name = st.selectbox(
        "Select a network", 
        [network['name'] for network in st.session_state.networks]
    )
    
    selected_network = next((network for network in st.session_state.networks 
                           if network['name'] == selected_network_name), None)
    
    if not selected_network:
        return
    
    st.session_state.selected_network = selected_network['id']
    
    # Time range for client data
    time_options = {
        "Last Hour": 3600,
        "Last 3 Hours": 10800,
        "Last 12 Hours": 43200,
        "Last Day": 86400,
        "Last Week": 604800
    }
    
    selected_time = st.select_slider(
        "Select time range",
        options=list(time_options.keys()),
        value="Last Day"
    )
    
    timespan = time_options[selected_time]
    
    with st.spinner("Loading network traffic data..."):
        traffic_data = st.session_state.meraki_api.get_network_traffic(selected_security['id'], timespan=timespan)
    
    if traffic_data:
        df_traffic = pd.DataFrame(traffic_data)
        
        # Convert times to datetime objects
        df_traffic['startTs'] = pd.to_datetime(df_traffic['startTs'])
        
        # Plot traffic data
        fig = px.line(df_traffic, x='startTs', y='bytes', title='Network Traffic Over Time')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Failed to retrieve network traffic data.")
        
def display_analytics():
    """Display analytics view"""
    st.title("Analytics")
    
    if not st.session_state.selected_org:
        st.info("Please select an organization from the sidebar.")
        return
    
    if not st.session_state.networks:
        st.info("No networks found for this organization.")
        return
    
    # Select a network
    selected_network_name = st.selectbox(
        "Select a network",
        [network['name'] for network in st.session_state.networks]
    )
    
    selected_network = next((network for network in st.session_state.networks
                              if network['name'] == selected_network_name), None)
    
    if not selected_network:
        return
    
    st.session_state.selected_network = selected_network['id']
    
    # Organization Summary
    st.subheader("Organization Summary")
    
    with st.spinner("Loading organization summary..."):
        org_summary = st.session_state.meraki_api.get_organization_summary(st.session_state.selected_org)
    
    if org_summary:
        st.json(org_summary)
    else:
        st.info("Failed to retrieve organization summary.")
    
    # Device Status
    st.subheader("Device Status")
    
