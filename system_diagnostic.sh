#!/bin/bash
# System diagnostic script for baseball CLI execution issues

echo "=== SYSTEM DIAGNOSTIC REPORT ==="
echo "Timestamp: $(date)"
echo "Hostname: $(hostname)"
echo "User: $(whoami)"
echo "Current directory: $(pwd)"
echo ""

echo "=== SYSTEM RESOURCES ==="
echo "Memory usage:"
free -h
echo ""
echo "Disk usage:"
df -h
echo ""
echo "CPU load:"
uptime
echo ""

echo "=== PROCESS INFORMATION ==="
echo "Running processes (top 10 by CPU):"
ps aux --sort=-%cpu | head -11
echo ""
echo "Running processes (top 10 by memory):"
ps aux --sort=-%mem | head -11
echo ""
echo "Python processes:"
ps aux | grep python | grep -v grep
echo ""

echo "=== ENVIRONMENT ==="
echo "Shell: $SHELL"
echo "Path: $PATH"
echo "Python version:"
python3 --version 2>&1 || echo "python3 not found"
echo ""
echo "Virtual environment:"
if [ -n "$VIRTUAL_ENV" ]; then
    echo "Virtual env: $VIRTUAL_ENV"
    echo "Python in venv: $VIRTUAL_ENV/bin/python --version"
    $VIRTUAL_ENV/bin/python --version 2>&1
else
    echo "No virtual environment active"
fi
echo ""

echo "=== FILE SYSTEM TESTS ==="
echo "Current directory contents:"
ls -la | head -10
echo ""
echo "Write test:"
echo "test" > /tmp/test_write_$$.txt
if [ -f "/tmp/test_write_$$.txt" ]; then
    echo "✓ File write successful"
    rm /tmp/test_write_$$.txt
else
    echo "✗ File write failed"
fi
echo ""

echo "=== NETWORK TESTS ==="
echo "Localhost connectivity:"
ping -c 1 localhost 2>&1 | head -2
echo ""
echo "DNS resolution:"
nslookup google.com 2>&1 | head -5
echo ""

echo "=== SYSTEM LOGS (last 10 lines) ==="
if [ -f /var/log/syslog ]; then
    tail -10 /var/log/syslog
elif [ -f /var/log/messages ]; then
    tail -10 /var/log/messages
else
    echo "System log file not found"
fi
echo ""

echo "=== END DIAGNOSTIC REPORT ==="
