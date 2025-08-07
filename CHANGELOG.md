# Changelog

All notable changes to Newspaparr will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2025-08-07

### 🎉 Initial Public Release

First public release of Newspaparr - an automated library card renewal system for digital newspaper access.

### ✨ Features

#### Core Functionality
- **Automated Daily Renewals** - Keep newspaper access active without manual intervention
- **Multi-Account Support** - Manage multiple library cards and newspaper accounts
- **Multiple Newspapers** - Support for The New York Times (NYT) and Wall Street Journal (WSJ)
- **OCLC Library Integration** - Works with OCLC-affiliated libraries offering digital passes

#### Advanced Automation
- **Priority-Based Login System** - Adaptive authentication handling for different newspaper flows
- **Smart State Detection** - Intelligent detection of success, warning, and failure states
- **CAPTCHA Solving** - Integrated CapSolver support with on-demand SOCKS5 proxy
- **Anti-Detection Measures** - Built with undetected-chromedriver and stealth techniques

#### User Interface
- **Modern Web Dashboard** - Clean, responsive interface built with Tailwind CSS
- **Real-Time Monitoring** - Live status updates and renewal tracking
- **Activity Logs** - Detailed history with filtering and search
- **Dark Mode Support** - Automatic theme switching

#### Technical Features
- **Docker Deployment** - Simple containerized setup
- **Persistent Storage** - SQLite database with automatic backups
- **Comprehensive Logging** - Rotating log files with configurable levels
- **Screenshot Debugging** - Automatic screenshots for troubleshooting
- **Health Monitoring** - Built-in health check endpoints

### 📋 Requirements
- Docker and Docker Compose
- Active library card from OCLC-affiliated library
- CapSolver account for CAPTCHA solving
- Port 1851 for web interface
- Port 3333 for SOCKS5 proxy

### 🏗️ Architecture
- Flask-based web application
- Selenium automation with undetected-chromedriver
- SQLite database for configuration and history
- APScheduler for automated renewals
- CapSolver integration for CAPTCHA challenges

### 📝 Notes
- Initial release focused on stability and core functionality
- Extensively tested with NYT and WSJ
- Production-ready with comprehensive error handling
- Full documentation included

---

## Pre-Release Development

### [0.4.0] - Internal Testing
- Implemented state detection system
- Added warning states for accounts with direct subscriptions
- Improved UI with color-coded status badges

### [0.3.0] - Beta Testing
- Added CAPTCHA solving via CapSolver
- Implemented SOCKS5 proxy for IP consistency
- Enhanced anti-detection measures

### [0.2.0] - Alpha Testing
- Basic renewal functionality
- Web interface implementation
- Database schema design

### [0.1.0] - Initial Development
- Project structure setup
- Core automation logic
- Library adapter framework

---

[0.5.0]: https://github.com/yourusername/newspaparr/releases/tag/v0.5.0