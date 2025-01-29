import IOT_cert as IOT
import hardwares.hub as hub
import scanner as scanner
import os
import json
import sys
import argparse
import serial
import configparser

# include the below lines in each module to implement logging ---------
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) #inherits from the root logger

PRIVATE_KEY_FILE = "private.pem.key"
CERTIFICATE_FILE = "cert.pem.crt"

# ---------------------------------------------------------------------

def provision(sn):
    """ Get certificate information from AWS and flash into Sentry Interface
    1) Create AWS thing
    2) Generate certificate and keys
    3) Provisioning thing with the generated certificate 
    4) Attach policy
    Args:
        sn (str): target serial number

    Returns:
        bool: True - Provioning infomation written into files in preparation to be programmed to target. 
              False - Provisioning failed
    """
    print("Start provisioning Process")
    serial_number = sn   
    try: 
        responseDev = IOT.provisionHub(serial_number, "dev")
        if responseDev: 
            print("Success to generate credential")
            with open(PRIVATE_KEY_FILE, 'w') as f:
                f.write(responseDev["PrivateKey"].replace('\x00',''))
                print("Private key file is created")
            with open(CERTIFICATE_FILE , 'w') as f:
                f.write(responseDev["certificatePem"].replace('\x00',''))
                print("Certificate file is created")
            return True
        else: 
            logger.warning("AWS IOT CORE provisioning calls failed")
            return False

    except Exception as e: 
        # BotoCoreError as e: 
        logger.critical(f"an exception occured : todo handle this correctly: {e}")
        """2021-01-26 22:53:52,160 MainProcess provisioning CRITICAL an exception occured : 
        todo handle this correctly: An error occurred (ResourceAlreadyExistsException) when 
        calling the CreateThing operation: Thing 00100235 already exists in account with different attributes"""
        print("Unexpected error:", sys.exc_info()[0])
        return False



if __name__ == '__main__':    
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', required=False, help='port number e.x. COM6, tty3')
    parser.add_argument('-sn', '--serial_no', required=False, nargs = '?', default = 'scan', help='Serial Number of the device. If no this argument, serial no. is read from barcode scanner')
    parser.add_argument('-cert_start','--nvs_cert_start', required=False, help='NVS AWS certificate partition start address (hex form in 0xaaaaa)')
    parser.add_argument('-cert_size','--nvs_cert_size', required=False, help='NVS AWS certificate partition size in bytes (decimal)')
    parser.add_argument('-key_start','--nvs_aws_key_start', required=False, help='NVS cert encryption key partition start address (hex form in 0xaaaaa)')
    args = parser.parse_args()  

    config = configparser.ConfigParser ()

    """Load parameters from config.ini if exists"""
    if os.path.isfile ('config.ini'):
        config.read ('config.ini')

    try:
        for arg in vars (args):
            if getattr (args, arg) is None:
                if config.has_option ("DEFAULT", arg):
                    setattr (args, arg, config['DEFAULT'][arg])

        if not args.nvs_cert_start:
            args.nvs_cert_start = '0x7ed000'
        if not args.nvs_cert_size:
            args.nvs_cert_size = '40960'
        if not args.nvs_aws_key_start:
            args.nvs_aws_key_start = '0x7f8000'


        for arg in vars (args):
            if not getattr (args, arg):
                raise Exception (f"Missing parameter: " + arg)

        config['DEFAULT']['nvs_cert_start'] = args.nvs_cert_start
        config['DEFAULT']['nvs_cert_size'] = args.nvs_cert_size
        config['DEFAULT']['nvs_aws_key_start'] = args.nvs_aws_key_start

    except KeyError as ex:
        logging.error ("Missing parameter. Neither argument nor .ini found. See help with --help")
        logging.error (ex)
        sys.exit (-1)

    with open ('config.ini', 'w') as configfile:
        config.write (configfile)




    # Add internal arguments used for generating an encrypted partition by genEncryptPartition()
    args.input = 'flash_nvs.csv'
    args.output = 'en_certKeyDnload.bin'
    args.size = args.nvs_cert_size
    args.version = 2
    args.keygen = True
    args.keyfile = 'certs_en_key.bin'
    args.inputkey = None
    args.outdir = os.getcwd()

    serialNo = args.serial_no.lower()

    if serialNo == 'scan':
        scan = scanner.Scanner()
        ret = scan.getBarCode()
        if ret == False:
            sys.exit("Incorrect scanned serial no.")
        else:    
            serialNo = ret.lower()

    #Check if serial port is available
    try:
        ser = serial.Serial(args.port)
    except Exception as e:
        sys.exit(f"Serial port error: {e}")    
    ser.close()
    
    if provision(serialNo):        
        hubCert = hub.Hub(serialNo)
        hubCert.genCsv(CERTIFICATE_FILE, PRIVATE_KEY_FILE)            
        hubCert.genEncryptPartition(args)
        hubCert.downEnCertImage(args)
        hubCert.downEnKeyImage(args)
        os.remove(CERTIFICATE_FILE)  
        os.remove(PRIVATE_KEY_FILE)  
    sys.exit()

