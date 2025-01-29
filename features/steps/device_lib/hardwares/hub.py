import subprocess

import sys
import time
import csv
import io
import os
import re
import serial
from contextlib import redirect_stdout
import importlib
try:
    nvs_partition_gen = importlib.import_module('esp-afr-sdk.components.nvs_flash.nvs_partition_generator.nvs_partition_gen')
except:
    nvs_partition_gen = None

class Hub:
    """
    __init__(self, serial_nr: String): No connection, use only the object
    __init__(self, hot_water_gpio: Integer, heat_gpio: Integer, serial_nr: String):
    """
    def __init__(self, *args):
        if len(args) == 1 and isinstance(args[0], str):
            self.serial_nr = args[0]
        elif len(args) == 3 and isinstance(args[0], int) and isinstance(args[1], int) and isinstance(args[2], str):
            self.serial_nr = args[0]
            self.doorMonitorGpio = args[1]
            self.doorRelayGpio = args[2]
        else:
            raise Exception('Invalid init args')

    def open_relay(self):
        # TODO
        return False

    def program(self, args):
        esptoolList = ['--chip', "esp32", '--port', args.port, '-b', '460800', '--before=default_reset', '--after=hard_reset',
                'write_flash', '--flash_mode', 'dio', '--encrypt', '--flash_freq', '40m', '--flash_size', '8MB', args.partition_table_start,
                args.partition_table_bin, args.ota_data_start, args.ota_data_init_bin, '0x1000', args.bootloader_bin, args.app_bin_start,
                args.application_bin]

        if args.encrypt is False:
            esptoolList.remove('--encrypt')
        
        if args.partition_table_bin == "none":
            esptoolList.remove(args.partition_table_start)
            esptoolList.remove(args.partition_table_bin)

        if args.ota_data_init_bin == "none":
            esptoolList.remove(args.ota_data_start)
            esptoolList.remove(args.ota_data_init_bin)

        if args.bootloader_bin == "none":
            esptoolList.remove('0x1000')
            esptoolList.remove(args.bootloader_bin)       

        __import__('esptool').main(esptoolList)
        time.sleep(2)

    def connect(self):
        #TODO
        return False 

    def disconnect(self):
        #TODO
        return False 

    def wait_for_response(self, response, timeout):
        #TODO
        return False 

    @staticmethod
    def wait_for_response_blocking(response, timeout):
        #TODO
        return False

    def genCsv(self, cFileName, kFileName):
        """Generate csv file of certificate and private key for next step to make partition bin.

        Args:
            cFileName (str): file name of certificate
            kFileName (str): file name of private key
        """
        with open('flash_nvs.csv','w', newline='') as fNvs:
            wNvs = csv.writer(fNvs)
            wNvs.writerow(['key','type','encoding','value']) 
            wNvs.writerow(['cert_key','namespace','',''])
            wNvs.writerow(['aws_cert','file','string',cFileName])
            wNvs.writerow(['aws_priv_key','file','string',kFileName])

    def genNorPartition(self):
        """Generate non-encrypted partition bin file for certificate and private key based on cvs file made from genCsv()
        """
        filePath = os.path.join('.\esp-afr-sdk','components','nvs_flash','nvs_partition_generator','nvs_partition_gen.py')
        os.system('python '+ filePath + ' generate flash_nvs.csv certKeyDnload.bin 40960')
        os.remove('flash_nvs.csv') 

    def genEncryptPartition(self, args):
        """Generate encrypted partition bin file for certificate and private key based on cvs file made from genCsv(), and also generate encryption key
        """
        args.outdir = os.getcwd()
        nvs_partition_gen.encrypt(args)
        os.remove('flash_nvs.csv')

    def downNorCertImage(self, args):
        """Flash generated non-encrypted certificate and private key into nvs_certs partition with address 0x7ed000

        Args:
            port (str): port connected to terminal
        """
        print('Download normal certificate and private key')
        __import__('esptool').main(
            ['--chip', "esp32",'--port', args.port, '--before=default_reset', '--after=no_reset',
             'write_flash', args.nvs_cert_start, 'certKeyDnload.bin'])
        os.remove('certKeyDnload.bin')      
        
    def downEnCertImage(self, args):
        """Flash generated encrypted certificate and private key into nvs_certs partition with address 0x7ed000

        Args:
            port (str): port connected to terminal
        """
        print('Download encrypted certificate')
        __import__('esptool').main(
            ['--chip', "esp32",'--port', args.port, '--before=default_reset', '--after=no_reset',
             'write_flash', args.nvs_cert_start, 'en_certKeyDnload.bin'])
        os.remove('en_certKeyDnload.bin')        

    def downEnKeyImage(self, args):
        """Flash generated encrytion key into ESP32 nvs_aws_key partition with address 0x7f8000

        Args:
            port (str): port connected to terminal
        """ 
        print('Download encryption key')
        dnkeyFile = os.path.join('.\keys','certs_en_key.bin')
        __import__('esptool').main(
            ['--chip', "esp32",'--port', args.port, '--before=default_reset', '--after=no_reset',
             'write_flash', '--encrypt', args.nvs_aws_key_start, dnkeyFile])
        os.remove(dnkeyFile)
        dnKeyPath = os.path.join('.\keys')
        os.rmdir(dnKeyPath)


    def chkSerialPortAvailable(self, port):   
        """check if serial port is accessible

        Args:
            port (str): port connected to terminal

        Returns:
            True if port is accessible, error message if not
        """
        try:
            ser = serial.Serial(port)
        except Exception as e:     
            return e
        ser.close()
        return True   


    def chkESP32Response(self, port, isProd, chklist, prodChklist):
        """To capture output print from esptool flash_id command to confirm if ESP32 serial link is ok and if ESP32 chip is what we want according to ESP32_CHECKLIST 
        and production check list 

        Args:
            port (str): port connected to terminal
            isProd (bool): True in production mode, False in development mode
            chklist (list): The list of sentences/words to be checked with ESP32 response
            prodChklist (list): The production list of WORDS to have exact match check with ESP32 response

        Returns:
            True if response match checklist, else return error messages
        """
        err = list()
        chk = 0
        with io.StringIO() as buf, redirect_stdout(buf):
            __import__('esptool').main(['-p',port,'flash_id'])
            output = buf.getvalue()

        for i in chklist:
            if(output.find(i)!=-1):
                chk += 1
            else:     
                err.append(f"This ESP32 chip feature doesn't match with requirement: {i}\n")         

        if chk < len(chklist):
            err.append(f"\nThis chip configuration is: {output}")
            err.append("\nAbort MAC flash process")
            return (''.join(err))            
        else:
            if isProd:
                return (self.__chkESP32ProdResponse(output, prodChklist))
            else:
                return True   


    def createDnMac(self):
        """Create download version mac address by inserting ':' symbol between each octet in serial no.

        Returns:
            str: MAC address in format XX:XX:XX:XX:XX:XX
        """
        serialList = list()
        for x in range (0,len(self.serial_nr),2):
            serialList.append(self.serial_nr[x:x+2])
            if (x+2) < len(self.serial_nr):
                serialList.append(":")
        return ("".join(serialList))


    def burnCustomMac(self, port, flash, macAdr):
        """To burn custom MAC into ESP32

        Args:
            port (str): port connected to the terminal
            flash (bool): True if flash MAC into ESP32 efuse, False if testing MAC download by writting to a file in PC
            macAdr (str): MAC address in format XX:XX:XX:XX:XX:XX

        Return:
            True if burn is success, else return error message
        """
        EFUSE_FILE = "efuse_memory.bin"
        #check if custom MAC address efuse if empty
        ret = self.__chkCustomMacEmpty(port, flash, EFUSE_FILE)            
        if ret == True:
            if flash:        
                print("\n========= Flash custom mac into eFuse of ESP32 =========\n")
                __import__('espefuse').main(['--do-not-confirm', '-p', port,'burn_custom_mac',macAdr])
                ret =  self.chkCustomMac(port, flash, macAdr)        
            else:
                print("\n========= TEST custom mac burn & read.  This DOESN'T flash into efuse of EPS32. =========\n")
                __import__('espefuse').main(['--do-not-confirm', '--virt','--path-efuse-file',EFUSE_FILE,'burn_custom_mac',macAdr])
                ret =  self.chkCustomMac(port, flash, macAdr, EFUSE_FILE) 
                os.remove(EFUSE_FILE)             

        return ret
   

    def chkCustomMac(self, port, flash, macAdr, efuseFile = ''):
        """Check if eFuse custom MAC address matches with macAdr argument

        Args:
            port (str): port connected to the terminal
            flash (bool): True if flash MAC into ESP32 efuse, False if testing MAC download by writting to a file in PC
            macAdr (str): MAC address in format XX:XX:XX:XX:XX:XX
            efuseFile (str, optional): For the case argument 'flash' is False, it's the file name containing eFuse . Defaults to ''.

        Returns:
            True if match, error message if not
        """
        with io.StringIO() as buf, redirect_stdout(buf):
            if flash:
                __import__('espefuse').main(['-p', port,'get_custom_mac'])
            else:    
                __import__('espefuse').main(['--virt','--path-efuse-file',efuseFile,'get_custom_mac'])
            output = buf.getvalue()
           
        if re.search(r'\b' + macAdr + r'\b', output, re.IGNORECASE):            
            return True
        else:
            return (f"Read custom MAC address from ESP32 eFuse isn't matched with {macAdr}\n{output}")




    #To do exact match check between response and the ESP32_PROD_CHECKLIST for production mode.  It is called by chkESP32Response
    def __chkESP32ProdResponse(self, resp, prodChklist):
        err = list()
        prodChk = 0
        for i in prodChklist:
            if re.search(r'\b' + i + r'\b', resp):
                prodChk += 1
            else:
                err.append(f"This ESP32 chip feature doesn't match with production requirement: {i}\n")   

        if prodChk == len(prodChklist):
            return True
        else:        
            err.append(f"\nDump of chip configuration:\n {resp}")
            err.append("\nAbort MAC download process")
            return (''.join(err))



    # TO check if custom MAC is empty in EPS32 efuse. It's called by burnCustomMac
    def __chkCustomMacEmpty(self, port, flash, efuseFile = ''):
        with io.StringIO() as buf, redirect_stdout(buf):
            if flash:
                __import__('espefuse').main(['-p', port,'get_custom_mac'])
            else:    
                __import__('espefuse').main(['--virt','--path-efuse-file',efuseFile,'get_custom_mac'])
            output = buf.getvalue()
        if (output.find("Custom MAC Address is not set in the device")!=-1):
            return True
        else:            
            return (f"\nCustom mac efuse is not empty. The chip efuse custom mac address:\n {output}\nAbort MAC flash process")
         

