# Troubleshooting Guide

This guide covers common issues and solutions for Newspaparr.

## Table of Contents
- [Installation Issues](#installation-issues)
- [Authentication Problems](#authentication-problems)
- [CAPTCHA Issues](#captcha-issues)
- [Renewal Failures](#renewal-failures)
- [Scheduling Problems](#scheduling-problems)
- [Performance Issues](#performance-issues)
- [Docker Issues](#docker-issues)
- [Debug Tools](#debug-tools)

## Installation Issues

### Port Already in Use

**Error**: `bind: address already in use`

**Solution**:
```bash
# Check what's using port 1851
sudo lsof -i :1851

# Either stop the conflicting service or change Newspaparr's port:
# Edit docker-compose.yml
ports:
  - "8080:1851"  # Change 8080 to your preferred port
```

### Permission Denied Errors

**Error**: `Permission denied` when accessing data files

**Solution**:
```bash
# Fix ownership
sudo chown -R $(id -u):$(id -g) ./data

# Fix permissions
chmod -R 755 ./data

# Update docker-compose.yml with your user ID
environment:
  - PUID=$(id -u)
  - PGID=$(id -g)
```

### Docker Build Fails

**Error**: Build errors during `docker-compose build`

**Solution**:
```bash
# Clean rebuild
docker-compose down
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
```

## Authentication Problems

### Library Login Failed

**Common Causes & Solutions**:

1. **Incorrect Credentials**
   - Double-check library card number
   - Verify PIN/password
   - Some libraries use birthdate as PIN (MMDDYYYY format)

2. **Library Not Supported**
   - Verify library is OCLC-affiliated
   - Check if library offers digital newspaper passes
   - Try manual login on library website first

3. **Session Expired**
   - Clear browser cookies
   - Restart Newspaparr container
   ```bash
   docker-compose restart
   ```

4. **Library Website Changed**
   - Check if library website layout changed
   - Report issue on GitHub for adapter update

### NYT/WSJ Login Failed

**Common Causes & Solutions**:

1. **Account Already Has Subscription**
   - Check account status on newspaper website
   - Cancel any active subscriptions
   - Wait 24 hours and retry

2. **Too Many Devices**
   - Log out of newspaper on other devices
   - Check device limit (usually 4-5 devices)
   - Remove unused devices from account settings

3. **Wrong Password Format**
   - Some special characters may cause issues
   - Try simpler password temporarily
   - Ensure no leading/trailing spaces

4. **Account Locked**
   - Too many failed attempts
   - Reset password on newspaper website
   - Wait 30 minutes before retrying

## CAPTCHA Issues

### CAPTCHA Not Solving

**Check CapSolver Setup**:

1. **API Key Invalid**
   ```bash
   # Verify API key in docker-compose.yml
   grep CAPSOLVER_API_KEY docker-compose.yml
   ```

2. **No Credit Balance**
   - Log into capsolver.com
   - Check balance (need ~$0.003 per CAPTCHA)
   - Add credit if needed

3. **Proxy Not Accessible**
   ```bash
   # Test external connectivity
   telnet YOUR_EXTERNAL_IP 3333
   
   # Check port forwarding on router
   # Port 3333 must be forwarded to Docker host
   ```

4. **Wrong Proxy Configuration**
   ```yaml
   # Correct format in docker-compose.yml
   environment:
     - PROXY_HOST=your-external-ip-or-domain
     - SOCKS5_PROXY_PORT=3333
   ```

### CAPTCHA Loop

**Issue**: Keeps getting CAPTCHA after solving

**Solutions**:
1. **IP Banned**
   - Wait 24 hours
   - Use different IP (VPN/proxy)
   - Reduce renewal frequency

2. **User-Agent Mismatch**
   - Ensure browser and CapSolver use same UA
   - Don't change CAPSOLVER_USER_AGENT unless necessary

## Renewal Failures

### Success Not Detected

**Issue**: Renewal works but shows as failed

**Solutions**:
1. Enable debug mode to capture success page
2. Check logs for actual outcome
3. Report unrecognized success message

### Timeout Errors

**Issue**: "Renewal timed out after 300 seconds"

**Solutions**:
```yaml
# Increase timeout in environment
environment:
  - RENEWAL_TIMEOUT=600  # 10 minutes
```

### Element Not Found

**Issue**: "Could not find login button/field"

**Solutions**:
1. Website layout may have changed
2. Enable screenshots to see current page
3. Report issue with screenshot

## Scheduling Problems

### Renewals Not Running

**Check Scheduler Status**:
```bash
# View scheduled jobs
docker-compose exec newspaparr python -c "
from app import scheduler
for job in scheduler.get_jobs():
    print(f'{job.id}: {job.next_run_time}')
"
```

**Common Fixes**:
1. Restart container
2. Check timezone setting
3. Verify account is enabled
4. Check logs for errors

### Wrong Schedule Time

**Issue**: Renewals run at unexpected times

**Solution**:
```yaml
# Set correct timezone
environment:
  - TZ=America/New_York  # Your timezone
```

Find your timezone: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

## Performance Issues

### High Memory Usage

**Solutions**:
1. **Limit Chrome memory**:
   ```bash
   # Add to docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 2G
   ```

### Slow Renewals

**Solutions**:
1. **Adjust interaction speed**:
   ```yaml
   environment:
     - RENEWAL_SPEED=fast  # Options: fast, normal, slow
   ```

2. **Disable screenshots** (if enabled):
   ```yaml
   environment:
     - DEBUG_SCREENSHOTS=false
   ```

## Docker Issues

### Container Keeps Restarting

**Check Logs**:
```bash
docker-compose logs --tail=50 newspaparr
```

**Common Causes**:
1. Port conflict
2. Invalid environment variables
3. Corrupted database

**Fix**:
```bash
# Full reset
docker-compose down
rm -rf data/newspaparr.db
docker-compose up -d
```

### Can't Access Web Interface

**Troubleshooting Steps**:
```bash
# Check if container is running
docker ps | grep newspaparr

# Check container logs
docker-compose logs newspaparr

# Test connectivity
curl http://localhost:1851/health

# Check firewall
sudo ufw status
```

## Debug Tools

### Enable Debug Mode

```yaml
# Add to docker-compose.yml
environment:
  - LOG_LEVEL=DEBUG
  - DEBUG_SCREENSHOTS=true
```

### View Screenshots

Screenshots saved to `./data/screenshots/` when debug enabled.

### Export Logs

```bash
# Save logs to file
docker-compose logs > newspaparr-logs.txt

# Follow logs in real-time
docker-compose logs -f --tail=100
```

### Database Inspection

```bash
# Backup database
cp data/newspaparr.db data/newspaparr-backup.db

# View accounts
docker-compose exec newspaparr python -c "
from app import db, Account
for acc in Account.query.all():
    print(f'{acc.name}: {acc.status}')
"
```

### Test Individual Components

```bash
# Test library adapter
docker-compose exec newspaparr python -c "
from library_adapters import LibraryAdapterFactory
adapter = LibraryAdapterFactory.create('oclc')
print(adapter.get_library_name())
"

# Test CAPTCHA solver
docker-compose exec newspaparr python -c "
from captcha_solver import CaptchaSolver
solver = CaptchaSolver()
print(f'CapSolver configured: {solver.api_key is not None}')
"
```

## Getting Help

If these solutions don't resolve your issue:

1. **Check existing issues**: [GitHub Issues](https://github.com/yourusername/newspaparr/issues)
2. **Enable debug mode** and collect logs
3. **Create detailed issue** with:
   - Error messages
   - Docker logs
   - Configuration (without secrets)
   - Steps to reproduce
   - Screenshots if relevant

## Common Error Messages

### "DataDome Protected"
- **Meaning**: Site detected automation
- **Solution**: Ensure CapSolver is configured

### "Invalid credentials"
- **Meaning**: Wrong username/password
- **Solution**: Verify credentials on website

### "No library adapter found"
- **Meaning**: Library type not supported
- **Solution**: Check supported libraries list

### "Chrome version mismatch"
- **Meaning**: ChromeDriver incompatible
- **Solution**: Rebuild container with `--no-cache`

### "Connection refused"
- **Meaning**: Service not accessible
- **Solution**: Check network and firewall settings

---

For additional help, visit our [GitHub Discussions](https://github.com/yourusername/newspaparr/discussions).