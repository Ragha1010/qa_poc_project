import hardwares.hub as hub
import scanner as scanner
import argparse
import sys

ESP32_CHECKLIST = ["Chip is ESP32-D0WD","Crystal is 40MHz","flash size: 8MB"]
ESP32_PROD_CHECKLIST = ["ESP32-D0WD-V3"]        #Exact keyword match production checklist, which is used in production mode only
MODE_DEV = "dev"
MODE_PROD = "prod"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Flash custom MAC address to efuse of ESP32")    
    parser.add_argument('-p', '--port', required=True, help='port number e.g. COM6, tty3')
    parser.add_argument('-m', '--mode', required=True, choices=[MODE_DEV,MODE_PROD], help=f"mode: {MODE_DEV} or {MODE_PROD}  (development/production mode)")
    parser.add_argument('-sn', '--serial', required=False, nargs = '?', default = 'scan', help='Serial number e.g. e0e2e65b5ddc. If no this argument, serial no. is read from barcode scanner')    
    parser.add_argument('-f', '--flash_efuse', required=False, action = "store_true", help='flash custom mac into eFuse of ESP32')

    args = parser.parse_args()

    serialNo = args.serial.lower()

    if serialNo == 'scan':
        scan = scanner.Scanner()
        ret = scan.getBarCode()
        if ret == False:
            sys.exit("Incorrect scanned serial no.")
        else:    
            serialNo = ret.lower()

    hubMac = hub.Hub(serialNo)      

    ret = hubMac.chkSerialPortAvailable(args.port)
    if ret != True:
        sys.exit(f"Serial port connection error: {ret}")
    
    isProd = False
    if args.mode == MODE_PROD:
        isProd = True
    ret = hubMac.chkESP32Response(args.port, isProd, ESP32_CHECKLIST, ESP32_PROD_CHECKLIST)
    if ret != True:
        sys.exit(ret)
    else:    
        print("ESP32 response OK")

    macAdr = hubMac.createDnMac()
   
    ret = hubMac.burnCustomMac(args.port, args.flash_efuse, macAdr)
    if ret != True:
        sys.exit(f"\nFlash custom Mac address error:{ret}")

    sys.exit()


   