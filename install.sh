#!/bin/bash

echo "Installing BME280 monitoring system..."

# Create necessary directories
mkdir -p data logs

# Install Python dependencies system-wide (you may need sudo for this)
echo "Installing Python dependencies..."
echo "Note: You may need to install these packages manually with apt or pip3 --user"
echo "Required packages: fastapi uvicorn schedule smbus2 bme280"

# Check if packages are available
python3 -c "import fastapi, uvicorn, schedule, smbus2, bme280" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ All Python dependencies are available"
else
    echo "⚠ Some dependencies missing. Install with:"
    echo "  pip3 install --user fastapi uvicorn[standard] schedule smbus2 bme280"
    echo "  OR try: sudo apt install python3-fastapi python3-uvicorn python3-schedule"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Copy systemd service files
echo "Installing systemd services..."
sudo cp systemd/bme280-logger.service /etc/systemd/system/
sudo cp systemd/bme280-web.service /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable bme280-logger.service
sudo systemctl enable bme280-web.service

# Start services
echo "Starting services..."
sudo systemctl start bme280-logger.service
sudo systemctl start bme280-web.service

# Wait a moment and check status
sleep 3

echo "Checking service status..."
sudo systemctl status bme280-logger.service --no-pager -l
sudo systemctl status bme280-web.service --no-pager -l

echo ""
echo "Installation complete!"
echo "Dashboard available at: http://$(hostname -I | cut -d' ' -f1):8000"
echo "Or try: http://raspberrypi.local:8000"
echo ""
echo "To check logs:"
echo "  sudo journalctl -u bme280-logger.service -f"
echo "  sudo journalctl -u bme280-web.service -f"
