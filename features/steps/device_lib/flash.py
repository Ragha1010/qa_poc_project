import hardwares.hub as hub
import argparse
import platform
import boto3
import configparser
import os
import sys
import logging


def get_s3_latest_release(binary_name):
    """Some values defaulted to S3 if they are empty"""
    try:
        S3_BUCKET_NAME = "afr-ota-sentry-firmware-qa"

        client = boto3.client (
            's3'
        )

        object_name = binary_name + ".bin"

        logging.info ("download from S3: " + object_name)
        client.download_file (S3_BUCKET_NAME, object_name, object_name)
        print (object_name)
    except Exception as ex:
        logging.error ("Could not find binary in S3 bucket")
        logging.error (ex)
        sys.exit (-1)
    return object_name


if __name__ == '__main__':
    """One stop programmer"""
    """Argument priority: 1. console argument 2. config.ini file 3. default to S3 bucket"""

    HALO_START_MAC = 0x6CA4017A1200

    parser = argparse.ArgumentParser()
    parser.add_argument('-table', '--partition_table_bin', required=False, help='Partition table')
    parser.add_argument('-part_start','--partition_table_start', required=False, help='Partition table start address (hex form in 0xaaaaa)')
    parser.add_argument('-app', '--application_bin', required=False, help='Application binary to flash')
    parser.add_argument('-app_start','--app_bin_start', required=False, help='Application binary start address (hex form in 0xaaaaa)')
    parser.add_argument('-boot', '--bootloader_bin', required=False, help='Bootloader binary to flash')
    parser.add_argument('-ota_data', '--ota_data_init_bin', required=False, help='OTA data binary to flash')
    parser.add_argument('-ota_data_start','--ota_data_start', required=False, help='OTA data binary start address (hex form in 0xaaaaa)')
    parser.add_argument('-e', '--encrypt', required=False, action = 'store_true', help='include this option if flash is already encrypted')
    parser.add_argument('-sn', '--serial', required=False, help='Serial number e.x. e0e2e65b5ddc')
    parser.add_argument('-v', '--version', required=False, help='firmware version number to be flashed e.x. 0.2.1')
    parser.add_argument('-p', '--port', required=True, help='port number e.x. COM6, tty3')
    parser.add_argument('-div', '--device', required=False, help='When it is not possible to tell device type from Serial Number, you can determine here e.x. hub, halo')
    parser.add_argument('-cert','--cert_file', required=False, help = "certificate file to flash")
    parser.add_argument('-prvkey','--prvkey_file', required=False, help = "private key file to flash")
    args = parser.parse_args()    
    config = configparser.ConfigParser ()

    """Load parameters from config.ini if exists"""
    if os.path.isfile ('config.ini'):
        config.read ('config.ini')

    """Evaluate existing arguments to see if it's to write certificate and private key """
    if bool(args.cert_file) != bool(args.prvkey_file):
        misCredPara = 'private key file' if bool(args.cert_file) else 'certificate file'
        logging.error("Flashing AWS provision credentials. Missing " + misCredPara +". See help with --help")
        sys.exit(-1)
    if  args.cert_file and args.prvkey_file:   
        logging.info("Flashing AWS provision credentials")
        if not args.port:
            logging.error("Miss port parameter")
            sys.exit(-1)
        if not os.path.exists(args.cert_file):
            logging.error("Certificate file doesn't exist. Please check if file name is correct")
            sys.exit(-1)
        if not os.path.exists(args.prvkey_file):
            logging.error("Private key file doesn't exist. Please check if file name is correct")
            sys.exit(-1)
        hubCert = hub.Hub("1234")
        hubCert.genCsv(args.cert_file, args.prvkey_file)
        
        hubCert.genEncryptPartition()
        hubCert.downEnCertImage(args.port)
        hubCert.downEnKeyImage(args.port)

        sys.exit(0)



    """Ty to conclude empty mondantory parameters from the given ones"""
    # TODO: make port not mandantory and scan USB ports
    try:
        if not args.serial:
            args.serial = config['DEFAULT']['Serial']
        else:
            config['DEFAULT']['Serial'] = args.serial

        if not args.device:
            device = 'sr' if (int (args.serial, 16) >= HALO_START_MAC) else 'si'
            args.device = device
        else:
            device = 'sr' if (args.device == 'sr') else 'si'
    except KeyError as ex:
        logging.error ("Missing parameter. Neither argument nor .ini found. See help with --help")
        logging.error (ex)
        sys.exit (-1)

    """Evaluate existing arguments and save to config.ini"""
    try:
        for arg in vars (args):
            if getattr (args, arg) is None:
                if config.has_option ("DEFAULT", arg):
                    setattr (args, arg, config['DEFAULT'][arg])

        if not args.partition_table_bin:
            args.partition_table_bin = get_s3_latest_release ("partition_table_v2")

        if not args.ota_data_init_bin:
            args.ota_data_init_bin = get_s3_latest_release ("ota_data_initial_v2")

        if not args.bootloader_bin:
            args.bootloader_bin = get_s3_latest_release (device + "_bootloader")

        if not args.application_bin:
            ver = args.version.replace ('.', '_')
            if device == 'sr':
                bin1 = device + "_app_v" + ver
                args.application_bin = get_s3_latest_release (bin1)
            else:
                bin1 = device + "_app_v" + ver + "_" + args.serial + "_uat"
                args.application_bin = get_s3_latest_release (bin1)

        if not args.partition_table_start:
            args.partition_table_start = '0x9000'
        if not args.ota_data_start:
            args.ota_data_start = '0x40a000'
        if not args.app_bin_start:
            args.app_bin_start = '0x410000'

        if args.partition_table_bin != 'none':
            args.partition_table_bin = os.path.abspath (args.partition_table_bin)
        if args.ota_data_init_bin != 'none':
            args.ota_data_init_bin = os.path.abspath (args.ota_data_init_bin)
        if args.bootloader_bin != 'none':
            args.bootloader_bin = os.path.abspath (args.bootloader_bin)
        args.application_bin = os.path.abspath (args.application_bin)        
        args.version = "TODO implement when need"
        args.cert_file = "dummy"
        args.prvkey_file = "dummy"

        for arg in vars (args):
            if arg!='encrypt':
                if not getattr (args, arg):
                    raise Exception (f"Missing parameter: " + arg)
                else:
                    config['DEFAULT'][arg] = getattr (args, arg)


    except KeyError as ex:
        logging.error ("Missing parameter. Neither argument nor .ini found. See help with --help")
        logging.error (ex)
        sys.exit (-1)

    with open ('config.ini', 'w') as configfile:
        config.write (configfile)

    """Execute flashing"""
    # NOTE In case hub and halo programming will stay the same, then an abstract call can have the program function
    hub1 = hub.Hub (args.serial)
    hub1.program (args)
