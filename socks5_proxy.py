#!/usr/bin/env python3
"""
SOCKS5 Proxy for CapSolver DataDome CAPTCHA solving
- Handles all traffic types properly at protocol level
- Authentication support with temporary credentials  
- External accessibility on port 3333
"""

import asyncio
import logging
import struct
import socket
import json
import os
import time
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store active credentials
ACTIVE_CREDENTIALS = {}
CREDENTIALS_FILE = "/tmp/newspaparr_socks5_proxy_creds.json"

class SOCKS5Server:
    def __init__(self, host='0.0.0.0', port=3333):
        self.host = host
        self.port = port
        
    async def handle_client(self, reader, writer):
        """Handle SOCKS5 client connection"""
        client_addr = writer.get_extra_info('peername')
        logger.info(f"🔗 New SOCKS5 connection from {client_addr[0]}:{client_addr[1]}")
        
        try:
            # SOCKS5 handshake
            if not await self.socks5_handshake(reader, writer, client_addr):
                return
                
            # Handle CONNECT request
            await self.handle_connect(reader, writer, client_addr)
            
        except Exception as e:
            logger.error(f"❌ Error handling client {client_addr}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            
    async def socks5_handshake(self, reader, writer, client_addr):
        """Perform SOCKS5 authentication handshake"""
        try:
            # Read greeting with timeout
            data = await asyncio.wait_for(reader.read(2), timeout=30.0)
            if len(data) < 2:
                return False
                
            version, nmethods = struct.unpack('!BB', data)
            if version != 5:
                logger.error(f"❌ Unsupported SOCKS version: {version} from {client_addr[0]}")
                return False
                
            # Read methods
            methods = await asyncio.wait_for(reader.read(nmethods), timeout=30.0)
            if len(methods) != nmethods:
                return False
                
            # Check if client supports username/password auth (method 2)
            if 2 in methods:
                # Require username/password authentication
                writer.write(struct.pack('!BB', 5, 2))
                await writer.drain()
                logger.info(f"🔐 Requesting authentication from {client_addr[0]}")
                return await self.handle_auth(reader, writer, client_addr)
            elif 0 in methods:
                # Allow no authentication for internal connections
                if client_addr[0] in ['127.0.0.1', '::1']:
                    writer.write(struct.pack('!BB', 5, 0))
                    await writer.drain()
                    logger.info(f"🏠 No auth required for internal client {client_addr[0]}")
                    return True
                else:
                    # External connection without auth support
                    writer.write(struct.pack('!BB', 5, 255))
                    await writer.drain()
                    logger.warning(f"❌ External client {client_addr[0]} doesn't support auth")
                    return False
            else:
                # No acceptable methods
                writer.write(struct.pack('!BB', 5, 255))
                await writer.drain()
                logger.warning(f"❌ No acceptable auth methods from {client_addr[0]}")
                return False
                
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Handshake timeout with {client_addr[0]}")
            return False
        except Exception as e:
            logger.error(f"❌ Handshake error with {client_addr}: {e}")
            return False
            
    async def handle_auth(self, reader, writer, client_addr):
        """Handle username/password authentication"""
        try:
            # Read auth request with timeout
            data = await asyncio.wait_for(reader.read(1), timeout=30.0)
            if len(data) < 1:
                return False
                
            version = struct.unpack('!B', data)[0]
            if version != 1:
                return False
                
            # Read username
            data = await asyncio.wait_for(reader.read(1), timeout=30.0)
            if len(data) < 1:
                return False
            ulen = struct.unpack('!B', data)[0]
            
            username = await asyncio.wait_for(reader.read(ulen), timeout=30.0)
            if len(username) != ulen:
                return False
            username = username.decode('utf-8')
            
            # Read password
            data = await asyncio.wait_for(reader.read(1), timeout=30.0)
            if len(data) < 1:
                return False
            plen = struct.unpack('!B', data)[0]
            
            password = await asyncio.wait_for(reader.read(plen), timeout=30.0)
            if len(password) != plen:
                return False
            password = password.decode('utf-8')
            
            # Verify credentials
            if self.verify_credentials(username, password):
                writer.write(struct.pack('!BB', 1, 0))  # Success
                await writer.drain()
                logger.info(f"✅ Authentication successful for {username} from {client_addr[0]}")
                return True
            else:
                writer.write(struct.pack('!BB', 1, 1))  # Failure
                await writer.drain()
                logger.warning(f"❌ Authentication failed for {username} from {client_addr[0]}")
                return False
                
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Auth timeout with {client_addr[0]}")
            return False
        except Exception as e:
            logger.error(f"❌ Auth error with {client_addr}: {e}")
            return False
            
    def verify_credentials(self, username, password):
        """Verify SOCKS5 credentials"""
        load_credentials()
        user_key = f"{username}:{password}"
        
        logger.info(f"🔐 Checking SOCKS5 credentials for user: {username} (have {len(ACTIVE_CREDENTIALS)} active creds)")
        
        if user_key in ACTIVE_CREDENTIALS:
            logger.info(f"✅ Valid SOCKS5 credentials for user: {username}")
            return True
        
        logger.warning(f"❌ Invalid SOCKS5 credentials for user: {username}")
        return False
        
    async def handle_connect(self, reader, writer, client_addr):
        """Handle SOCKS5 CONNECT request"""
        try:
            # Read CONNECT request with timeout
            data = await asyncio.wait_for(reader.read(4), timeout=30.0)
            if len(data) < 4:
                return
                
            version, cmd, rsv, atyp = struct.unpack('!BBBB', data)
            if version != 5 or cmd != 1:  # Only support CONNECT
                await self.send_reply(writer, 7)  # Command not supported
                return
                
            # Read address
            if atyp == 1:  # IPv4
                addr_data = await asyncio.wait_for(reader.read(4), timeout=30.0)
                if len(addr_data) < 4:
                    return
                addr = socket.inet_ntoa(addr_data)
            elif atyp == 3:  # Domain name
                addr_len_data = await asyncio.wait_for(reader.read(1), timeout=30.0)
                if len(addr_len_data) < 1:
                    return
                addr_len = struct.unpack('!B', addr_len_data)[0]
                addr_data = await asyncio.wait_for(reader.read(addr_len), timeout=30.0)
                if len(addr_data) < addr_len:
                    return
                addr = addr_data.decode('utf-8')
            else:
                await self.send_reply(writer, 8)  # Address type not supported
                return
                
            # Read port
            port_data = await asyncio.wait_for(reader.read(2), timeout=30.0)
            if len(port_data) < 2:
                return
            port = struct.unpack('!H', port_data)[0]
            
            logger.info(f"🎯 SOCKS5 CONNECT: {client_addr[0]} → {addr}:{port}")
            
            # Connect to target with longer timeout for CAPTCHA solving
            try:
                target_reader, target_writer = await asyncio.wait_for(
                    asyncio.open_connection(addr, port), 
                    timeout=60.0  # 60 second connection timeout
                )
                logger.info(f"✅ Connected to {addr}:{port}")
                
                # Send success reply (always use 0.0.0.0:0 for successful connections)
                await self.send_reply(writer, 0)
                
                # Start relaying data optimized for CapSolver
                await self.relay_data_capsolver(reader, writer, target_reader, target_writer, client_addr, f"{addr}:{port}")
                
            except asyncio.TimeoutError:
                logger.error(f"⏰ Connection timeout to {addr}:{port}")
                await self.send_reply(writer, 1)  # General SOCKS server failure
            except Exception as e:
                logger.error(f"❌ Failed to connect to {addr}:{port}: {e}")
                await self.send_reply(writer, 1)  # General SOCKS server failure
                
        except asyncio.TimeoutError:
            logger.warning(f"⏰ CONNECT request timeout from {client_addr[0]}")
        except Exception as e:
            logger.error(f"❌ CONNECT error: {e}")
            
    async def send_reply(self, writer, status, bind_addr='0.0.0.0', bind_port=0):
        """Send SOCKS5 reply"""
        try:
            # Handle bind address properly - always use 0.0.0.0 for successful connections
            if status == 0:  # Success
                bind_addr = '0.0.0.0'
                bind_port = 0
            
            # Convert bind address to bytes
            addr_bytes = socket.inet_aton(bind_addr)
            reply = struct.pack('!BBBB', 5, status, 0, 1) + addr_bytes + struct.pack('!H', bind_port)
            writer.write(reply)
            await writer.drain()
        except Exception as e:
            logger.error(f"❌ Error sending reply: {e}")
            # Fallback with 0.0.0.0 if address conversion fails
            try:
                addr_bytes = socket.inet_aton('0.0.0.0')
                reply = struct.pack('!BBBB', 5, status, 0, 1) + addr_bytes + struct.pack('!H', 0)
                writer.write(reply)
                await writer.drain()
            except:
                pass
            
    async def relay_data_capsolver(self, client_reader, client_writer, target_reader, target_writer, client_addr, target_info):
        """Optimized bidirectional data relay for CapSolver"""
        bytes_client_to_target = 0
        bytes_target_to_client = 0
        last_log_time = time.time()
        
        async def forward(reader, writer, direction):
            nonlocal bytes_client_to_target, bytes_target_to_client, last_log_time
            try:
                logger.debug(f"🔄 Starting {direction} relay for {client_addr[0]} ↔ {target_info}")
                while True:
                    try:
                        # Use appropriate buffer and timeout for CapSolver
                        data = await asyncio.wait_for(reader.read(32768), timeout=120.0)  
                        if not data:
                            break
                        
                        writer.write(data)
                        await writer.drain()
                        
                        # Track bytes
                        if direction == "client→target":
                            bytes_client_to_target += len(data)
                        else:
                            bytes_target_to_client += len(data)
                            
                        # Consolidated logging - only log summary every 5 seconds or on large transfers
                        current_time = time.time()
                        if len(data) > 10000 or (current_time - last_log_time) > 5:
                            total_bytes = bytes_client_to_target + bytes_target_to_client
                            logger.info(f"📊 Data relay active: {client_addr[0]} ↔ {target_info} (↑{bytes_client_to_target:,} ↓{bytes_target_to_client:,} = {total_bytes:,} bytes)")
                            last_log_time = current_time
                        
                    except asyncio.TimeoutError:
                        logger.debug(f"⏰ {direction} timeout for {client_addr[0]} (120s)")
                        break
                        
            except Exception as e:
                logger.debug(f"🔌 {direction} relay ended for {client_addr[0]}: {e}")
            finally:
                pass  # No need for closing log, covered in summary
                try:
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass
                
        # Start forwarding in both directions
        try:
            await asyncio.gather(
                forward(client_reader, target_writer, "client→target"),
                forward(target_reader, client_writer, "target→client"),
                return_exceptions=True
            )
        finally:
            total_bytes = bytes_client_to_target + bytes_target_to_client
            if total_bytes > 0:
                logger.info(f"✅ Relay complete: {client_addr[0]} ↔ {target_info} (↑{bytes_client_to_target:,} ↓{bytes_target_to_client:,} = {total_bytes:,} bytes)")
            else:
                logger.debug(f"✅ Relay complete: {client_addr[0]} ↔ {target_info} (no data transferred)")
        
    async def start_server(self):
        """Start the SOCKS5 server"""
        server = await asyncio.start_server(
            self.handle_client, 
            self.host, 
            self.port
        )
        
        logger.info(f"🚀 CapSolver SOCKS5 proxy server running on {self.host}:{self.port}")
        
        async with server:
            await server.serve_forever()

def load_credentials():
    """Load credentials from file"""
    global ACTIVE_CREDENTIALS
    try:
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, 'r') as f:
                ACTIVE_CREDENTIALS = json.load(f)
    except Exception as e:
        logger.warning(f"⚠️ Could not load credentials: {e}")
        ACTIVE_CREDENTIALS = {}

def save_credentials():
    """Save credentials to file"""
    try:
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(ACTIVE_CREDENTIALS, f)
    except Exception as e:
        logger.warning(f"⚠️ Could not save credentials: {e}")

def add_credential(username, password):
    """Add a temporary credential"""
    user_key = f"{username}:{password}"
    ACTIVE_CREDENTIALS[user_key] = {
        'created': time.time(),
        'used': False
    }
    save_credentials()
    logger.info(f"🔑 Added SOCKS5 credential for user: {username}")

def remove_credential(username, password):
    """Remove a specific credential (single-use cleanup)"""
    user_key = f"{username}:{password}"
    if user_key in ACTIVE_CREDENTIALS:
        del ACTIVE_CREDENTIALS[user_key]
        save_credentials()
        logger.info(f"🗑️ Removed single-use SOCKS5 credential for user: {username}")
        return True
    else:
        logger.debug(f"Credential not found for removal: {username}")
        return False

def cleanup_expired_credentials():
    """Clean up expired credentials (safety cleanup for any orphaned credentials)"""
    current_time = time.time()
    expired_keys = []
    
    for key, data in ACTIVE_CREDENTIALS.items():
        # Reduce to 10 minutes since we now remove credentials immediately after use
        if current_time - data['created'] > 600:  # 10 minutes (safety buffer)
            expired_keys.append(key)
    
    for key in expired_keys:
        del ACTIVE_CREDENTIALS[key]
        logger.info(f"🧹 Removed orphaned SOCKS5 credential: {key.split(':')[0]}")
    
    if expired_keys:
        save_credentials()

def start_cleanup_thread():
    """Start background thread to clean up expired credentials"""
    def cleanup_loop():
        while True:
            time.sleep(300)  # Check every 5 minutes
            cleanup_expired_credentials()
    
    cleanup_thread = threading.Thread(target=cleanup_loop)
    cleanup_thread.daemon = True
    cleanup_thread.start()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'add':
        # Add credential mode: python3 socks5_proxy.py add username:password
        if len(sys.argv) > 2:
            try:
                username, password = sys.argv[2].split(':', 1)
                load_credentials()
                add_credential(username, password)
                print(f"Added SOCKS5 credential for user: {username}")
            except ValueError:
                print("Error: Format should be username:password")
                sys.exit(1)
        else:
            print("Error: Missing username:password")
            sys.exit(1)
    elif len(sys.argv) > 1 and sys.argv[1] == 'remove':
        # Remove credential mode: python3 socks5_proxy.py remove username:password
        if len(sys.argv) > 2:
            try:
                username, password = sys.argv[2].split(':', 1)
                load_credentials()
                if remove_credential(username, password):
                    print(f"Removed SOCKS5 credential for user: {username}")
                else:
                    print(f"Credential not found for user: {username}")
            except ValueError:
                print("Error: Format should be username:password")
                sys.exit(1)
        else:
            print("Error: Missing username:password")
            sys.exit(1)
    else:
        # Start proxy server
        load_credentials()
        start_cleanup_thread()
        
        logger.info("🚀 Starting CapSolver SOCKS5 proxy server on port 3333")
        
        server = SOCKS5Server(host='0.0.0.0', port=3333)
        try:
            asyncio.run(server.start_server())
        except KeyboardInterrupt:
            logger.info("🛑 SOCKS5 proxy server stopped")