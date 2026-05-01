import socket
import psutil
import os

print("--- ALADDIN NETWORK DEBUG ---")
print(f"Current User: {os.getlogin()}")

interfaces = psutil.net_if_addrs()
for iface, addrs in interfaces.items():
    print(f"\nInterface: {iface}")
    for addr in addrs:
        if addr.family == socket.AF_INET:
            print(f"  IP Address: {addr.address}")
            print(f"  Netmask: {addr.netmask}")

target_ip = "192.168.101.75"
target_port = 8022

print(f"\n--- Testing Connection to {target_ip}:{target_port} ---")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    result = s.connect_ex((target_ip, target_port))
    if result == 0:
        print("SUCCESS: Port is OPEN and reachable!")
    else:
        print(f"FAILED: Connection error code {result}")
    s.close()
except Exception as e:
    print(f"ERROR: {e}")
