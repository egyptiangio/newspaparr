# Newspaparr 📰

Automated library card renewal system for digital newspaper access. Keep your New York Times and Wall Street Journal access active through your library's digital passes.

![Version](https://img.shields.io/badge/version-0.5.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

## ✨ Features

- 🔄 **Automated Daily Renewals** - Set it and forget it
- 📚 **Multi-Library Support** - Works with OCLC-affiliated libraries
- 📰 **NYT & WSJ Support** - Access major newspapers through your library
- 🤖 **CAPTCHA Solving** - Handles DataDome challenges automatically
- 🌐 **Web Dashboard** - Modern, responsive interface
- 📊 **Smart Scheduling** - Learns renewal patterns and optimizes timing
- 🔍 **Detailed Logging** - Track all renewal attempts and outcomes
- 🐳 **Docker Deployment** - Simple containerized setup

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Active library card from an OCLC-affiliated library
- Free accounts at NYT and/or WSJ (without paid subscriptions)
- (Optional) CapSolver account for CAPTCHA solving

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/newspaparr.git
   cd newspaparr
   ```

2. **Configure environment**
   ```bash
   cp docker-compose.example.yml docker-compose.yml
   # Edit docker-compose.yml with your settings
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
- Must be an OCLC-affiliated library
- Library must offer digital newspaper passes
- Valid library card number and PIN

### Newspaper Accounts
- Existing email accounts at target newspapers
- Accounts should NOT have active paid subscriptions
- Will be linked to library passes automatically

### CAPTCHA Solving (Optional but Recommended)
- Account at [CapSolver](https://capsolver.com)
- Small credit balance (~$3 per 1000 CAPTCHAs)
- Port 3333 open/forwarded for SOCKS5 proxy
- External IP or dynamic DNS configured

## 🔧 Configuration

### Basic Settings

Edit your `docker-compose.yml`:

```yaml
environment:
  # Timezone for scheduling
  - TZ=America/New_York
  
  # File permissions (use: id $(whoami))
  - PUID=1000
  - PGID=1000
```

### CAPTCHA Setup

If your library uses DataDome protection:

```yaml
environment:
  # CapSolver API key
  - CAPSOLVER_API_KEY=YOUR_API_KEY_HERE
  
  # Your external hostname/IP
  - PROXY_HOST=your-hostname.com
  
  # SOCKS5 proxy port
  - SOCKS5_PROXY_PORT=3333
```

### Advanced Options

See `docker-compose.example.yml` for all available options including:
- Anti-detection settings
- Logging levels
- Retry configuration
- Proxy settings

## 📖 How It Works

1. **Library Authentication**: Logs into your library's digital services
2. **Pass Renewal**: Navigates to newspaper pass section
3. **Account Linking**: Connects your newspaper account to the library pass
4. **Smart Detection**: Verifies successful renewal
5. **Scheduling**: Plans next renewal based on expiration

### Supported Libraries

- Most OCLC/WorldCat libraries
- Libraries using standard OCLC authentication
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

**Note**: This project is not affiliated with The New York Times, Wall Street Journal, OCLC, or any library system. It's an independent tool to help users maintain their legitimate library-provided newspaper access.