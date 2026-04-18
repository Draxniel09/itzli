import usb.core
import usb.util
dev = usb.core.find(idVendor=0x04e8)
if dev is None:
    print("Device not found")
else:
    for cfg in dev:
        print(f"Configuration: {cfg.bConfigurationValue}")
        for intf in cfg:
            print(f"  Interface: {intf.bInterfaceNumber}, Class: {intf.bInterfaceClass}, SubClass: {intf.bInterfaceSubClass}")
