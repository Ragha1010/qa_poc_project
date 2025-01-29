from aws_iot import AWSIoTOTA
from hardwares.hub import Hub
import argparse
import logging

if __name__ == '__main__':
    """OTA update tool"""

    DEFAULT_OTA_TIMEOUT_MINUTES = 480

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument('-sn', '--serial', required=True, help='Serial number e.x. 00100270')
    parser.add_argument('-ft', '--fileType', type=int, required=True, help='e.x. hub = 1, halo = 2')
    parser.add_argument('-v', '--version', required=False, help='Version number to update to e.x. v0_3_1')
    parser.add_argument('-app', '--app_bin', required=False, help='Application binary to update to')
    parser.add_argument('-t', '--timeout', default=DEFAULT_OTA_TIMEOUT_MINUTES, type=int, required=False, help='Optional in progress timeout')
    args = parser.parse_args()

    if (not args.version and not args.app_bin) or (args.version != None and args.app_bin != None):
        raise Exception("You can give either app binary or version number")

    ota_client = AWSIoTOTA(thing_name=args.serial,
                           firmware_bucket_name="afr-ota-sentry-firmware-qa",
                           role="iot-ota-service",
                           signing_profile='ESP32Sentry2')

    hub1 = Hub(args.serial)
    if not args.app_bin:
        ota_client.update_single_hub(hub1, args.version, None, args.timeout, args.fileType)
    else:
        ota_client.update_single_hub(hub1, None, args.app_bin, args.timeout, args.fileType)
