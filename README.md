# Newspaparr 📰

Automated library card renewal system for digital newspaper access. Keep your New York Times and Wall Street Journal access active through your library's digital passes.

![Version](https://img.shields.io/badge/version-0.5.3-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

## ✨ Features

- 🔄 **Automated Daily Renewals** - Set it and forget it
- 📚 **Multi-Library Support** - Use your library-provided URLs
- 📰 **NYT & WSJ Support** - Access major newspapers through your library
- 🤖 **CAPTCHA Solving** - Handles DataDome challenges automatically
- 🌐 **Web Dashboard** - Modern, responsive interface
- 📊 **Smart Scheduling** - Learns renewal patterns and optimizes timing
- 🔍 **Detailed Logging** - Track all renewal attempts and outcomes
- 🐳 **Docker Deployment** - Simple containerized setup

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Active library card with digital newspaper access
- Free accounts at NYT and/or WSJ (without paid subscriptions)
- (Optional) CapSolver account for CAPTCHA solving

### Installation

1. **Create a docker-compose.yml file**
   ```bash
   # Download the example configuration
   wget https://raw.githubusercontent.com/egyptiangio/newspaparr/main/docker-compose.example.yml -O docker-compose.yml
   
   # Or create it manually from the example below
   ```

2. **Configure your settings**
   ```bash
   # Edit docker-compose.yml with your library and newspaper settings
   nano docker-compose.yml
   ```

3. **Start the container**
   ```bash
   docker-compose up -d
   ```

4. **Access the web interface**
   - Open http://localhost:1851
   - Add your library configuration
   - Add newspaper accounts
   - Enable automated renewals

## 📋 Requirements

### Library Requirements
- Must provide digital newspaper passes
- Library must offer digital newspaper passes
- Valid library card number and PIN

### Newspaper Accounts
- Existing email accounts at target newspapers
- Accounts should NOT have active paid subscriptions
- Will be linked to library passes automatically

### CAPTCHA Solving (Optional but Recommended)
- Account at [CapSolver](https://capsolver.com) for when NYT/WSJ show CAPTCHAs
- Small credit balance (~$3 per 1000 CAPTCHAs)
- **Port 3333 must be forwarded** on your router for external access
- External IP or dynamic DNS configured (e.g., your-home.duckdns.org)

## 🔧 Configuration

### Minimal docker-compose.yml

```yaml
services:
  newspaparr:
    image: ghcr.io/egyptiangio/newspaparr:latest
    container_name: newspaparr
    ports:
      - "1851:1851"           # Web interface
      - "3333:3333"           # SOCKS5 proxy for CAPTCHA solving
    volumes:
      - ./data:/app/data      # Persistent data storage
    restart: unless-stopped
    environment:
      # Basic Configuration
      - TZ=America/New_York
      - PUID=1000
      - PGID=1000
      
      # Anti-Detection Settings
      - RENEWAL_HEADLESS=false     # Use GUI mode for better success
      - RENEWAL_SPEED=normal        # Interaction speed: fast, normal, slow
      - RENEWAL_RANDOM_UA=false     # Keep false for CAPTCHA compatibility
      
      # CAPTCHA Solving (For NYT/WSJ bot detection)
      - CAPSOLVER_API_KEY=YOUR_API_KEY_HERE
      - PROXY_HOST=your-hostname.com    # Your external IP/hostname
      - SOCKS5_PROXY_PORT=3333
      
      # Optional: Debug Mode
      - RENEWAL_DEBUG=false         # Set to true for verbose logging
```

### CAPTCHA Setup

When NYT or WSJ detect bot activity and show CAPTCHAs, Newspaparr automatically handles them:

1. **Port Forwarding Required**: Forward port 3333 on your router to your Docker host
   - External port: 3333 → Internal port: 3333
   - This allows the CAPTCHA service to connect through your home IP

2. **On-Demand SOCKS5 Proxy**:
   - Proxy starts automatically only when CAPTCHA solving is needed
   - Shuts down immediately after solving (not always running)
   - Uses randomized credentials for each renewal session
   - Credentials expire and rotate automatically for security

3. **Configuration**:
```yaml
environment:
  # CapSolver API key from capsolver.com
  - CAPSOLVER_API_KEY=YOUR_API_KEY_HERE
  
  # Your external hostname/IP (must be accessible from internet)
  - PROXY_HOST=your-hostname.com
  
  # SOCKS5 proxy port (must match port forwarding)
  - SOCKS5_PROXY_PORT=3333
```

**Security Note**: The proxy only runs during CAPTCHA solving (typically 30-60 seconds) with temporary credentials that are invalidated immediately after use.

## 📖 How It Works

1. **Library Authentication**: Logs into your library's digital services
2. **Pass Renewal**: Navigates to newspaper pass section
3. **Account Linking**: Connects your newspaper account to the library pass
4. **Smart Detection**: Verifies successful renewal
5. **Scheduling**: Plans next renewal based on expiration

### Supported Libraries

- Libraries with newspaper pass programs
- Any library-provided newspaper access URL
- Custom adapters can be added for special cases

### Renewal States

- ✅ **Success**: Access renewed and verified
- ⚠️ **Success with Warning**: Account has direct subscription
- ❌ **Failure**: Unable to renew (check logs for details)

## 🛠️ Management

### View Logs
```bash
docker-compose logs -f newspaparr
```

### Manual Renewal
Access http://localhost:1851 and click "Renew Now" for any account

### Backup Data
```bash
cp -r ./data ./data-backup-$(date +%Y%m%d)
```

### Update to Latest
```bash
docker-compose pull
docker-compose up -d
```

## 🐛 Troubleshooting

### Common Issues

**"Library login failed"**
- Verify library card number and PIN
- Check if library requires special authentication
- Try logging in manually on library website

**"CAPTCHA detected but not solved"**
- Ensure CapSolver API key is valid
- Check credit balance at capsolver.com
- Verify port 3333 is accessible externally
- Confirm PROXY_HOST is correct

**"NYT/WSJ activation failed"**
- Account may already have active subscription
- Check device limit on newspaper account
- Try clearing browser data and retrying

**"Permission denied" errors**
```bash
# Fix permissions
sudo chown -R $(id -u):$(id -g) ./data
chmod -R 755 ./data
```

### Debug Mode

Enable detailed logging and screenshots:

```yaml
environment:
  - LOG_LEVEL=DEBUG
  - DEBUG_SCREENSHOTS=true
```

Screenshots will be saved to `./data/screenshots/`

## 📊 API Endpoints

The web interface exposes several API endpoints:

- `GET /api/accounts` - List all accounts
- `POST /api/accounts` - Add new account
- `PUT /api/accounts/{id}` - Update account
- `DELETE /api/accounts/{id}` - Delete account
- `POST /api/accounts/{id}/renew` - Trigger manual renewal
- `GET /api/logs` - Retrieve renewal logs
- `GET /health` - Health check endpoint

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/newspaparr.git
cd newspaparr

# Build and run
docker-compose build
docker-compose up
```

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool automates the library card renewal process. Users are responsible for:
- Complying with their library's terms of service
- Respecting newspaper subscription terms
- Using the tool responsibly and ethically

## 🆘 Support

- 🐛 [Report Issues](https://github.com/yourusername/newspaparr/issues)
- 💡 [Request Features](https://github.com/yourusername/newspaparr/discussions)
- 📖 [Documentation](https://github.com/yourusername/newspaparr/wiki)

## 🙏 Acknowledgments

- Built with Flask, Selenium, and undetected-chromedriver
- CAPTCHA solving powered by CapSolver
- UI components from Tailwind CSS

---

**Note**: This project is not affiliated with The New York Times, Wall Street Journal, or any library system. It's an independent tool to help users maintain their legitimate library-provided newspaper access.