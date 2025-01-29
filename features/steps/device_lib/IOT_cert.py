# -*- coding: utf-8 -*-
"""
This package calls AWS IOT Core services & retrieves certificate information,
which can then be stored on the server
"""
import boto3
from botocore.config import Config
import pathlib
from pathlib import Path
import random
import sys
import time
import csv
import re

# include the below lines in each module to implement logging ---------
import logging

from botocore.utils import S3ArnParamHandler
logger = logging.getLogger(__name__) #inherits from the root logger
# ---------------------------------------------------------------------

#development DEV credentials
DEV_ACCESS_KEY = ""
DEV_SECRET_KEY = ""
DEV_SESSION_TOKEN = "" 

#production credentials
PROD_ACCESS_KEY = ""
PROD_SECRET_KEY = ""
PROD_SESSION_TOKEN = "" 

ROOT_CA = """"""

def _convertCert_toHex(certificateString): 
    """Convert String to HEX string"""
    listHex = [((ord(char))) for char in certificateString]
    listHex = [("{0:#0{1}x}".format(char,4))[2:] for char in listHex]
    seperator = "" #blank 
    return seperator.join(listHex)


def _login_IOT_core(IOT_ENV):
    """login to IOT CORE - with hardcoded credentials"""
    my_config = Config(
        region_name = 'eu-west-2',
        signature_version = 's3v4',
        retries = {
            'max_attempts': 10,
            'mode': 'standard'
        }
    )

    try:
        if IOT_ENV == "dev":
            iot = boto3.client('iot')
        elif IOT_ENV == "prod":
            iot = boto3.client('iot', config=my_config, aws_access_key_id=PROD_ACCESS_KEY, aws_secret_access_key=PROD_SECRET_KEY)
    except Exception as e:
        print(f"{__name__} exception occured: {e}")
        raise e

    return iot
    #todo: error handling, if credentials fail

def generate_certificates(IOT_ENV):
    """generate keys and certificates, returns dict with 
    string/HEX keys """
    if IOT_ENV == "dev":
        iot = _login_IOT_core(IOT_ENV="dev")
    elif IOT_ENV == "prod": 
        iot = _login_IOT_core(IOT_ENV="prod")
    response = iot.create_keys_and_certificate(setAsActive=True)
    return(response)

def create_thing(deviceSN, IOT_ENV):
    if IOT_ENV == "dev":
        iot = _login_IOT_core(IOT_ENV="dev")
    elif IOT_ENV == "prod": 
        iot = _login_IOT_core(IOT_ENV="prod")
    try: 
        response = iot.create_thing(thingName=deviceSN)        
        return response
    except iot.exceptions.ResourceAlreadyExistsException as e: 
        logger.warning(f"AWS IoT Thing already exists. Exception: {e}")
        return False
        

def attach_thing_principal(thingName, certificateArn, IOT_ENV):
    if IOT_ENV == "dev":
        iot = _login_IOT_core(IOT_ENV="dev")
    elif IOT_ENV == "prod": 
        iot = _login_IOT_core(IOT_ENV="prod")
    try: 
        iot.attach_thing_principal(
        thingName=thingName,
        principal=certificateArn
        )
        return True
    except Exception as e: 
        print(f"{__name__} exception occured: {e}")
        return False

def attach_policy(policyName, certificateArn, IOT_ENV):
    if IOT_ENV == "dev":
        iot = _login_IOT_core(IOT_ENV="dev")
    elif IOT_ENV == "prod": 
        iot = _login_IOT_core(IOT_ENV="prod")
    try: 
        iot.attach_policy(
            policyName=policyName, 
            target=certificateArn
        )
        return True
    except Exception as e: 
        print(f"{__name__} exception occured: {e}")
        return False

# return provisioning information
# arguements: 
#               1) deviceSN is an 8 digit serial number (passed a string)
#               2) IOT_ENV 
#                   a) "prod"
#                   b) "dev"
def provisionHub(deviceSN, IOT_ENV):
    # If the device is a field return a Thing will not be able to be created
    # A Resorce already exists exception will be raised
    ThingDict = create_thing(deviceSN, IOT_ENV)
    if ThingDict == False:
        ThingDict = {"thingName": deviceSN} #Thing already exists. Reuse it. 

    CertDict = generate_certificates(IOT_ENV)
    if attach_thing_principal(ThingDict["thingName"], CertDict["certificateArn"], IOT_ENV):
        print("Provisioning Success")
        if attach_policy("dummy-do-not-use", CertDict["certificateArn"], IOT_ENV):
            # Append the null character to the certificate information
            privateKey_data = CertDict["keyPair"]["PrivateKey"] + "\0"
            privateKey_length = len(privateKey_data)
            certificatePEM_Data = CertDict["certificatePem"] + "\0"
            certificatePEM_length = len(certificatePEM_Data)
            rootCA_Data = ROOT_CA + "\0"
            rootCA_length = len(rootCA_Data)
            certificateID_data = CertDict["certificateId"] +"\0"
            certificateID_len = len(certificateID_data)
            return ({
                "PrivateKey": privateKey_data,
                "certificatePem": certificatePEM_Data,
                "rootCA": rootCA_Data,
                "length_PrivateKey": privateKey_length,
                "length_certificatePem": certificatePEM_length,
                "length_rootCA": rootCA_length,
                "certificateID_data": certificateID_data,
                "certificateID_len": certificateID_len
            })
        else: 
            print("failed to attach general policy")
            return False
    else: 
        print("failed to provision")
        return False