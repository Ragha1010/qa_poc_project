import boto3
from datetime import date
import time
import random
import logging
try:
    from hardwares.hub import Hub
except ImportError:
    from .hardwares.hub import Hub
import ntpath
import os

class AWSIoT:
    def __init__(self, role, signing_profile, profile=""):
        if profile != "":
            boto3.setup_default_session(profile_name=profile)

        boto3.setup_default_session()
        self.awsIotJobId = None

    def delete_all_jobs(self, job_id_filter):
        iot = boto3.client('iot')
        response = iot.list_jobs()
        while "nextToken" in response:
            response = iot.list_jobs(nextToken=response['nextToken'])

            for job in response['jobs']:
                if job_id_filter in job['jobId']:
                    print( "Delete:" + job['jobId'])
                    iot.delete_job(jobId = job['jobId'])

    def shadow_update(json_string, thingname):
        # Publish the JSON to the list of Devices
        iot = boto3.client('iot-data')
        response = iot.update_thing_shadow(thingName=thingname, payload=json_string)
        print("Shadow updated for thing :"+thingname)

class AWSIoTOTA:
    def __init__(self, firmware_bucket_name, role, signing_profile, thing_name, thing_group="", profile=""):

        # TODO: Remove thing_name and add iot_thing_arn to Hub class. Get it when HUB being inited.
        if profile != "":
            boto3.setup_default_session(profile_name=profile)

        boto3.setup_default_session()
        self.thing_group = thing_group
        self.thing_name = thing_name
        self.awsIotJobId = None

        # Get OTA Role
        iam = boto3.resource('iam')
        ota_role = iam.Role(role)
        logging.debug(ota_role)
        self.ota_role_arn = ota_role.arn

        if thing_name:
            logging.info ("thingnames..: %s" % self.thing_name)
            iot = boto3.client ('iot')
            iot_thing = iot.describe_thing(thingName=self.thing_name)
            self.iot_thing_arn = iot_thing["thingArn"]
        else:
            logging.info("thing_group.: %s" % self.thing_group)
        self.bucket = firmware_bucket_name
        self.signing_profile = signing_profile

    def list_binaries(self):
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(self.bucket)
        for file in bucket.objects.all():
            print(file)

    def list_ota_updates(self):
        iot = boto3.client('iot')
        response = iot.list_ota_updates(maxResults=10)
        print(response)

    def list_signed_images(self):
        iot = boto3.client('signer')
        response = iot.list_signing_jobs()
        response_sum = response

        while "nextToken" in response: 
            response = iot.list_signing_jobs(nextToken=response['nextToken'])
            response_sum['jobs'].extend(response['jobs'])

        return response_sum

    def update_single_hub(self, hub: Hub, update_to, app_bin, timeout, fileType):
        if update_to is None:
            app_path = os.path.abspath(app_bin)
            s3_client = boto3.client('s3')
            s3_binary = ntpath.basename(app_path).replace('.bin', '-' + str(random.randint(1, 65535)) + '.bin')
            # TODO remove random number tag and upload/sign only if doens't exists.
            # Add write protection to release versions

            s3_client.upload_file(app_path,
                                  self.bucket,
                                  s3_binary)

            s3_versions = s3_client.list_object_versions(Bucket=self.bucket,
                                                         Prefix=s3_binary)
            versions = s3_versions['Versions']

            try:
                latestversion = [x for x in versions if x['IsLatest'] == True]
                s3_binary_version = latestversion[0]['VersionId']
                if not s3_binary_version:
                    raise Exception("Could not find s3 file version")
            except KeyError:
                raise Exception("Could not find s3 file version")

            self.create_ota_job_from_binary( s3_binary, s3_binary_version, timeout, fileType, self.signing_profile,is_group=False)
        else:
            self.create_ota_job(update_to, timeout, fileType)


    def update_group_fleet(self, thing_group, app_bin, update_to, timeout, fileType):
        iot = boto3.client ('iot')
        iot_thing_group = iot.describe_thing_group (thingGroupName=thing_group)
        self.iot_thing_group_arn = iot_thing_group["thingGroupArn"]
        ota_job_ids = []
        response = iot.list_things_in_thing_group (thingGroupName=thing_group)
        things = response['things']
        if not things:
            logging.info("No things found in the thing group.")
            return
        if update_to is None:
            init_path = os.path.abspath (app_bin)
            dir_name = os.path.dirname (init_path)
            app_path = os.path.join (dir_name, "build", app_bin)
            logging.info ("Absolute obtained: {}".format (app_path))
            s3_client = boto3.client ('s3')
            s3_binary = ntpath.basename (app_path).replace ('.bin', '-' + str (random.randint (1, 65535)) + '.bin')
            # TODO remove random number tag and upload/sign only if doens't exists.
            # Add write protection to release versions
            s3_client.upload_file (app_path, self.bucket, s3_binary)
            s3_versions = s3_client.list_object_versions (Bucket=self.bucket, Prefix=s3_binary)
            versions = s3_versions['Versions']
            try:
                latestversion = [x for x in versions if x['IsLatest'] == True]
                s3_binary_version = latestversion[0]['VersionId']
                if not s3_binary_version:
                    raise Exception ("Could not find s3 file version")
            except KeyError:
                raise Exception ("Could not find s3 file version")
            thing_jobid = self.create_ota_job_from_binary (s3_binary, s3_binary_version, timeout, int (fileType),
                                                           self.signing_profile,is_group=True)
            ota_job_ids.append (thing_jobid)
        else:
            thing_jobid = self.create_ota_job (update_to, timeout, fileType)
            ota_job_ids.append (thing_jobid)

        return ota_job_ids

    def print_signed_images(self):
        response = self.list_signed_images()
        print("Signed images:")
        for x in response['jobs']:
            print("jobId: " + str(x['jobId']) + " : " + str(x['source']))

    def verify_singing_profile(self):
        try:
            signer = boto3.client('signer')
            profiles = signer.list_signing_profiles()['profiles']

            foundProfile = False
            afrProfile = None
            print("Searching for profile %s" % self.otasigningprofile)

            if len(profiles) > 0:
                for profile in profiles:
                    if profile['profileName'] == self.otasigningprofile:
                        foundProfile = True
                        afrProfile = profile

            if (afrProfile != None):
                foundProfile = True
                print("Found Profile %s in account" % self.otasigningprofile)

            if (not foundProfile):
                raise Exception("Error getting signing profile: {}".format(self.otasigningprofile))

        except Exception as e:
            logging.info("Error getting signing profiles: {}".format(e))
            raise e

    def create_ota_job_from_binary(self, s3_binary, s3_binary_version, timeout, fileType, signing_profile,is_group=False):
        try:
            iot = boto3.client('iot')
            t = time.localtime()
            today = date.today()
            time_tag = time.strftime("%H%M%S", t) + today.strftime("-%d%m%Y")
            # Initialize the template to use
            files = [{
                        'fileName': s3_binary,
                        'fileVersion': '1',
                        'fileLocation': {
                            's3Location': {
                                'bucket': self.bucket,
                                'key': s3_binary,
                                'version': s3_binary_version
                            }
                        },
                        'fileType': fileType,
                        'codeSigning': {
                            'startSigningJobParameter': {
                                'signingProfileName': signing_profile,
                                'destination': {
                                    's3Destination': {
                                        'bucket': self.bucket
                                    }
                                }
                            }
                        }
                    }]
            if is_group:
                target = self.iot_thing_group_arn
                updateId = str(self.thing_group) + "-" + time_tag + "-" + str (random.randint (1, 65535)) + "-" + os.getlogin ()
                logging.info ("thinggroupname: %s" % self.thing_group)
            else:
                target = self.iot_thing_arn
                updateId = self.thing_name + "-" + time_tag + "-" + str (random.randint (1, 65535)) + "-" + os.getlogin ()
                logging.info ("thingnames: %s" % self.thing_name)
            logging.info("Files for update: %s" % files)
            ota_update = iot.create_ota_update(
                otaUpdateId=updateId,
                targetSelection='SNAPSHOT',
                awsJobTimeoutConfig={
                    'inProgressTimeoutInMinutes': timeout
                },
                files=files,
                targets=[target],
                roleArn=self.ota_role_arn
            )

            logging.info("OTA Update Status: %s" % ota_update)
            logging.info(f"OTA update ID: {ota_update['otaUpdateId']}")
            self.otaUpdateId = ota_update["otaUpdateId"]
            self.awsIotJobId = self.get_ota_update()
            time.sleep (10)
            return self.awsIotJobId

        except Exception as e:
            logging.info("Error creating OTA Job: %s" % e)
            raise e
        pass

    def create_ota_job(self, version_nr, timeout, fileType):
        found = False

        try:
            signed_images = self.list_signed_images()
            for x in signed_images['jobs']:
                if (version_nr in x['source']['s3']['key'] and
                        self.bucket == x['source']['s3']['bucketName'] and
                        'Succeeded' == x['status'] and
                        False == x['isRevoked'] and
                        self.signing_profile == x['profileName']):
                    logging.info(x['jobId'])
                    logging.info(x['source']['s3']['key'])
                    logging.info(x)
                    found = True
                    break

            if not found:
                raise Exception("No signed image found with key: " + version_nr)

            iot = boto3.client('iot')
            t = time.localtime()
            today = date.today()
            time_tag = time.strftime("%H%M%S", t) + today.strftime("-%d%m%Y")
            # Initialize the template to use
            files = [{
                'fileName': x['source']['s3']['key'],
                'fileType': fileType,
                'codeSigning': {
                    'awsSignerJobId': x['jobId'],
                }
            }]

            target = self.iot_thing_arn
            updateId = self.thing_name + "-" + time_tag + "-" + str(random.randint(1, 65535)) + "-" + os.getlogin()

            print("Files for update: %s" % files)

            if self.ota_role_arn != "":
                ota_update = iot.create_ota_update(
                    otaUpdateId=updateId,
                    protocols=['MQTT'],
                    targetSelection='SNAPSHOT',
                    awsJobTimeoutConfig={
                        'inProgressTimeoutInMinutes': timeout
                    },
                    files=files,
                    targets=[target],
                    roleArn=self.ota_role_arn
                )
            else:
                ota_update = iot.create_ota_update(
                    otaUpdateId=updateId,
                    protocols=['MQTT'],
                    targetSelection='SNAPSHOT',
                    awsJobTimeoutConfig={
                        'inProgressTimeoutInMinutes': timeout
                    },
                    files=files,
                    targets=[target]
                )

            print("OTA Update Status: %s" % ota_update)
            print(f"OTA update ID: {ota_update['otaUpdateId']}")
            self.otaUpdateId = ota_update["otaUpdateId"]
            self.awsIotJobId = self.get_ota_update()

        except Exception as e:
            print("Error creating OTA Job: %s" % e)
            raise e

    def get_ota_update(self):
        # extract "awsIotJobId" which is required for tracking job completion
        iot = boto3.client('iot')
        response = iot.get_ota_update(otaUpdateId=self.otaUpdateId)
        while True:
            if "awsIotJobId" in response["otaUpdateInfo"]:
                awsIotJobId = response["otaUpdateInfo"]["awsIotJobId"]
                return awsIotJobId
            elif response["otaUpdateInfo"]["otaUpdateStatus"] == "CREATE_FAILED":
                print(f"Response: {response}")
                print(f"Status:", response["otaUpdateInfo"]["otaUpdateStatus"])
                break
            else:
                print("WAIT job creation status to be complete")
                response = iot.get_ota_update(otaUpdateId=self.otaUpdateId)
                print(f"Response: {response}")
                print(f"Status:", response["otaUpdateInfo"]["otaUpdateStatus"])
                time.sleep(5)


class AWSSimplifiedIoTOTA (AWSIoTOTA):

    def __init__(self, thing_name=None, thing_group=None):
        super (AWSSimplifiedIoTOTA, self).__init__ (thing_name=thing_name, thing_group=thing_group,
                                                    firmware_bucket_name="afr-ota-sentry-firmware-qa",
                                                    role="iot-ota-service", signing_profile='ESP32Sentry2')
        self.default_ota_timeout_minutes = 20

    def launch_ota(self, app_bin, file_type):
        hub = Hub(self.thing_name)
        self.update_single_hub(hub, None, app_bin, self.default_ota_timeout_minutes, file_type)
        return self.awsIotJobId
    
    def launch_fota(self, thing_group, app_bin, update_to, timeout, fileType):
        logging.info ("thinggroupname: %s" % thing_group)
        ota_job_ids = self.update_group_fleet (thing_group=thing_group, app_bin=app_bin, update_to=update_to,
                                               timeout=self.default_ota_timeout_minutes,
                                               fileType=fileType)
        return ota_job_ids

    def status_check(self):
        iot = boto3.client('iot')
        reply = iot.describe_job_execution(jobId=self.awsIotJobId, thingName=self.thing_name)
        return reply["execution"]["status"]

    def complete_check(self):
        result = ''
        timeout = 120
        timeout_start = time.time()
        while time.time() < timeout_start + timeout:
            result = self.status_check()
            if result == 'SUCCEEDED' or result == 'FAILED':
                break
            time.sleep(5)
        return result

    def status_check_fleet(self, job_id):
        iot = boto3.client ('iot')
        reply = iot.describe_job (jobId=job_id)
        logging.info ('Status Check Fleet - Job ID: {}, Status: {}'.format (job_id, reply["job"]["status"]))
        return reply["job"]["status"]

    def thing_job_validations(self, job_id, thing_group):
        logging.info ('Status Check Fleet2 - Job ID: {}, Thing Group: {}'.format (job_id, thing_group))
        iot = boto3.client ('iot')
        response = iot.list_things_in_thing_group (thingGroupName=thing_group)
        thing_names = []
        overall_status = {}
        if 'things' in response:
            thing_names = response['things']
            logging.info ('Thing Names: {}'.format (thing_names))
        for thing_name in thing_names:
            response = iot.describe_job_execution (jobId=job_id, thingName=thing_name)
            job_status = response['execution']['status']
            overall_status[thing_name] = job_status
            logging.info ('in fleet2 Thing/Device1: {}, Job ID: {}, job_status: {}'.format (thing_name, job_id, job_status))
        time.sleep (10)
        return overall_status

    def complete_check_fleet(self, job_id: int, thing_group: str, filetype: str) -> str:
        logging.info ('Complete Check Fleet - Job ID: {}, Thing Group: {}'.format (job_id, thing_group))
        Otajobstatus = 'SUCCEEDED'
        TIMEOUT = 1200
        SLEEP_INTERVAL = 5
        timeout_start = time.time ()
        completed = False

        while time.time () < timeout_start + TIMEOUT and not completed:
            logging.info ('Complete Check Fleet - Checking status')
            jobdescriptionstatus = self.status_check_fleet (job_id)

            if jobdescriptionstatus == 'COMPLETED':
                completed = True
            else:
                time.sleep (SLEEP_INTERVAL)

        if not completed:
            logging.info ('job description status is not completed switching to timeout validations')
        else:
            logging.info ('Complete Check Fleet - Fetching thing statuses')

        thing_statuses = self.thing_job_validations (job_id, thing_group)

        for thing_name, job_status in thing_statuses.items ():
            logging.info ('Thing/Device: {}, Job ID: {}, Job Status: {}'.format (thing_name, job_id, job_status))

            if job_status != 'SUCCEEDED':
                Otajobstatus= 'FAILED'
                logging.info ("Result is: {}".format (Otajobstatus))
                break

        return Otajobstatus

    def cancel_ota_job(self, job_id):
        iot_client = boto3.client ('iot')
        response = iot_client.cancel_job (jobId=job_id)
        return response