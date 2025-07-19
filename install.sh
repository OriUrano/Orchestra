#!/bin/bash
# Orchestra Installation Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORCHESTRA_PATH="$SCRIPT_DIR/orchestra.py"
CRON_JOB="0 * * * * /usr/bin/python3 $ORCHESTRA_PATH >/dev/null 2>&1"

echo "🎼 Installing Orchestra..."

# Check dependencies
echo "Checking dependencies..."

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if gh is authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Error: GitHub CLI is not authenticated"
    echo "Please run: gh auth login"
    exit 1
fi

echo "✅ Dependencies check passed"

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r "$SCRIPT_DIR/requirements.txt"

# Make orchestra.py executable
chmod +x "$ORCHESTRA_PATH"

# Create config directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/config"

# Check if configuration files exist
if [ ! -f "$SCRIPT_DIR/config/repos.yaml" ]; then
    echo "⚠️  Warning: config/repos.yaml not found. Please configure your repositories."
fi

if [ ! -f "$SCRIPT_DIR/config/settings.yaml" ]; then
    echo "⚠️  Warning: config/settings.yaml not found. Using default settings."
fi

# Test the installation
echo "Testing Orchestra installation..."
if python3 "$ORCHESTRA_PATH" --test-mode --run-once > /dev/null 2>&1; then
    echo "✅ Orchestra test run successful"
else
    echo "❌ Orchestra test run failed. Please check the configuration."
    exit 1
fi

# Setup cron job
echo "Setting up cron job..."

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$ORCHESTRA_PATH"; then
    echo "⚠️  Cron job already exists. Removing old entry..."
    (crontab -l 2>/dev/null | grep -v "$ORCHESTRA_PATH") | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Cron job installed: $CRON_JOB"

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

echo ""
echo "🎉 Orchestra installation completed!"
echo ""
echo "Next steps:"
echo "1. Configure your repositories in config/repos.yaml"
echo "2. Adjust settings in config/settings.yaml if needed"
echo "3. Test manually: python3 orchestra.py --run-once"
echo "4. Orchestra will now run automatically every hour"
echo ""
echo "To uninstall:"
echo "- Remove cron job: crontab -e (delete the Orchestra line)"
echo "- Remove this directory: rm -rf $SCRIPT_DIR"
echo ""
echo "Logs will be available in: $SCRIPT_DIR/logs/"