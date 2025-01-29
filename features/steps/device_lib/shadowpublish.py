

# https://endpoint/things/thingName/shadow

from aws_iot import AWSIoT
import argparse
import logging
import os
import json


#Enter the thing name of the devices that needs to be controlled via Shadow Here.

listofthings = ["" , ""]

if __name__ == '__main__':
    """Shadow Update Tool"""

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('-jsonfilename', required=True, help='JSON object to publish Desired config values')
    args = parser.parse_args()

    if (not args.jsonfilename):
        raise Exception("You need to give the json document name")
    
    if(os.path.exists('./'+args.jsonfilename))==False:
        raise Exception("Json File not Found")
    else:
        f = open(args.jsonfilename)
        data = json.load(f)
        for thing in listofthings:
            AWSIoT.shadow_update(json.dumps(data), str(thing))


    #To Do : Pass the list of Devices and JSON document to the Aws IoT 
    # Class.