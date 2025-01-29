from aws_iot import AWSIoT
import argparse
import logging

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-fl', '--filter', required=True, help='Subscrting filter for the Job ID')
    args = parser.parse_args()

    ota_client = AWSIoT(role="iot-ota-service",
                        signing_profile='ESP32Sentry')

    ota_client.delete_all_jobs(job_id_filter=args.filter)