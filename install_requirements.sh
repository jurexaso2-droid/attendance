#!/bin/bash
echo "Installing required packages for Attendance System..."

pkg update && pkg upgrade -y
pkg install python -y
pkg install python-pip -y

pip install qrcode[pil]
pip install pillow

echo "Installation complete!"
echo "Run: python attendance_system.py"
