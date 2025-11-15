#!/bin/bash
# Software reset of Launchpad USB device (avoids physical power cycle)

# Find the Launchpad USB device
DEVICE=$(lsusb | grep -i "Focusrite-Novation Launchpad" | awk '{print $6}')

if [ -z "$DEVICE" ]; then
    echo "Launchpad not found"
    exit 1
fi

VENDOR=$(echo $DEVICE | cut -d: -f1)
PRODUCT=$(echo $DEVICE | cut -d: -f2)

echo "Found Launchpad: $VENDOR:$PRODUCT"

# Find the USB device path
for dir in /sys/bus/usb/devices/*/; do
    if [ -f "$dir/idVendor" ] && [ -f "$dir/idProduct" ]; then
        v=$(cat "$dir/idVendor" 2>/dev/null)
        p=$(cat "$dir/idProduct" 2>/dev/null)
        if [ "$v" = "$VENDOR" ] && [ "$p" = "$PRODUCT" ]; then
            USB_PATH="$dir"
            break
        fi
    fi
done

if [ -z "$USB_PATH" ]; then
    echo "Could not find USB device path"
    exit 1
fi

echo "USB path: $USB_PATH"
echo "Resetting device..."

# Unbind and rebind the USB device
DEVICE_NAME=$(basename "$USB_PATH")
echo "$DEVICE_NAME" | sudo tee /sys/bus/usb/drivers/usb/unbind > /dev/null
sleep 0.5
echo "$DEVICE_NAME" | sudo tee /sys/bus/usb/drivers/usb/bind > /dev/null

echo "Device reset complete"
sleep 1
echo "Checking if device is back..."
lsusb | grep -i Launchpad
