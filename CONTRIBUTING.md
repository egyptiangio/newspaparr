# Contributing to Newspaparr

Thank you for your interest in contributing to Newspaparr! We welcome contributions of all kinds - bug fixes, new features, documentation improvements, and more.

## Code of Conduct

By participating in this project, you agree to be respectful and constructive in all interactions. We want to maintain a welcoming environment for everyone.

## How to Contribute

### Reporting Issues

Before creating an issue, please:
- Check existing issues to avoid duplicates
- Use the issue templates when available
- Include as much detail as possible:
  - Steps to reproduce
  - Expected vs actual behavior
  - Error messages and logs
  - Your environment (OS, Docker version, browser)
  - Screenshots if applicable

### Suggesting Features

- Open a discussion first for major features
- Explain the use case and benefits
- Consider implementation complexity
- Be open to feedback and alternatives

### Submitting Code

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/newspaparr.git
   cd newspaparr
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   # or
   git checkout -b fix/bug-description
   ```

3. **Make your changes**
   - Follow existing code style and patterns
   - Add comments for complex logic
   - Update documentation if needed
   - Keep changes focused and atomic

4. **Test thoroughly**
   ```bash
   # Build and run with Docker
   docker-compose build
   docker-compose up
   
   # Test your changes:
   # - Web interface at http://localhost:1851
   # - Library connections
   # - Renewal functionality
   # - Error handling
   ```

5. **Commit your changes**
   ```bash
   git commit -m "feat: add amazing feature"
   # or
   git commit -m "fix: resolve specific issue"
   ```
   
   Follow conventional commits:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `style:` for formatting changes
   - `refactor:` for code restructuring
   - `test:` for test additions
   - `chore:` for maintenance tasks

6. **Push and create PR**
   ```bash
   git push origin feature/amazing-feature
   ```
   Then open a Pull Request with:
   - Clear description of changes
   - Link to related issues
   - Screenshots if UI changes
   - Testing notes

## Development Environment

### Prerequisites
- Docker and Docker Compose
- Git
- Text editor or IDE
- Web browser for testing

### Local Development Setup

1. **Clone and configure**
   ```bash
   git clone https://github.com/YOUR_USERNAME/newspaparr.git
   cd newspaparr
   
   # Copy example configuration
   cp docker-compose.example.yml docker-compose.yml
   # Edit docker-compose.yml with your settings
   ```

2. **Build and run**
   ```bash
   docker-compose build --no-cache
   docker-compose up
   ```

3. **Access the application**
   - Web UI: http://localhost:1851
   - Logs: `docker-compose logs -f`

### Project Structure
```
newspaparr/
├── app.py                 # Main Flask application
├── renewal_engine.py      # Core renewal logic
├── library_adapters.py    # Library-specific implementations
├── state_detector.py      # Success/failure detection
├── captcha_solver.py      # CAPTCHA solving integration
├── templates/            # HTML templates
├── static/              # CSS, JS, images
├── data/               # Runtime data (gitignored)
├── logs/               # Application logs (gitignored)
└── docker/             # Docker configuration
```

### Key Technologies
- **Backend**: Python, Flask, SQLAlchemy
- **Frontend**: HTML, Tailwind CSS, Alpine.js
- **Automation**: Selenium, undetected-chromedriver
- **Scheduling**: APScheduler
- **Database**: SQLite
- **Deployment**: Docker, Docker Compose

## Testing Guidelines

### Manual Testing Checklist
- [ ] Web interface loads correctly
- [ ] Can add/edit/delete accounts
- [ ] Manual renewal works
- [ ] Scheduled renewals trigger
- [ ] Error handling works
- [ ] Logs are generated
- [ ] Screenshots captured (debug mode)

### Testing Different Scenarios
- Test with valid credentials
- Test with invalid credentials
- Test CAPTCHA handling
- Test network failures
- Test library variations

## Code Style Guidelines

### Python
- Follow PEP 8 conventions
- Use meaningful variable names
- Add docstrings for functions
- Handle exceptions properly
- Use type hints where helpful

### HTML/JavaScript
- Use semantic HTML
- Follow existing Tailwind patterns
- Keep JavaScript minimal
- Ensure accessibility

### Commits
- One logical change per commit
- Clear, descriptive messages
- Reference issues when applicable
- Keep commit history clean

## Documentation

When adding features or making changes:
- Update README.md if needed
- Add inline code comments
- Update CHANGELOG.md
- Document new environment variables
- Include examples where helpful

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Create an Issue
- **Security**: Email security concerns privately
- **Chat**: Join community discussions

## Recognition

Contributors will be:
- Listed in CHANGELOG.md
- Mentioned in release notes
- Added to contributors list

Thank you for helping make Newspaparr better!