#
# Copyright (C) Essensys.tech, Ltd. or its affiliates.  All Rights Reserved.
#

""" Esys Test Applications """
import subprocess
import hashlib
import json
import os
import sys

from tiny_test_fw import App
from . import CIAssignExampleTest

import boto3

try:
    import gitlab_api
except ImportError:
    gitlab_api = None


def parse_flash_settings(userdata, path):
    file_name = os.path.basename(path)
    if file_name == "flasher_args.json":
        # CMake version using build metadata file
        with open(path, "r") as f:
            args = json.load(f)

        partition_version = '3'
        if 'partition_version' in userdata:
            partition_version = userdata['partition_version']
        flash_files = 'flash_files_v3'
        if partition_version == '4':
            flash_files = 'flash_files_v4'

        flash_files = [(offs, binary) for (offs, binary) in args[flash_files].items() if offs != ""]
        flash_settings = args["flash_settings"]
        app_name = os.path.splitext(args["app"]["file"])[0]
    else:
        # GNU Make version uses download.config arguments file
        with open(path, "r") as f:
            args = f.readlines()[-1].split(" ")
            flash_files = []
            flash_settings = {}
            for idx in range(0, len(args), 2):  # process arguments in pairs
                if args[idx].startswith("--"):
                    # strip the -- from the command line argument
                    flash_settings[args[idx][2:]] = args[idx + 1]
                else:
                    # offs, filename
                    flash_files.append((args[idx], args[idx + 1]))
            # we can only guess app name in download.config.
            for p in flash_files:
                if not os.path.dirname(p[1]) and "partition" not in p[1]:
                    # app bin usually in the same dir with download.config and it's not partition table
                    app_name = os.path.splitext(p[1])[0]
                    break
            else:
                app_name = None
    return flash_files, flash_settings, app_name


class Artifacts(object):
    def __init__(self, dest_root_path, artifact_index_file, app_path, config_name, target):
        assert gitlab_api
        # at least one of app_path or config_name is not None. otherwise we can't match artifact
        assert app_path or config_name
        assert os.path.exists(artifact_index_file)
        self.gitlab_inst = gitlab_api.Gitlab(os.getenv("CI_PROJECT_ID"))
        self.dest_root_path = dest_root_path
        with open(artifact_index_file, "r") as f:
            artifact_index = json.load(f)
        self.artifact_info = self._find_artifact(artifact_index, app_path, config_name, target)

    @staticmethod
    def _find_artifact(artifact_index, app_path, config_name, target):
        for artifact_info in artifact_index:
            match_result = True
            if app_path:
                # We use endswith here to avoid issue like:
                # examples_protocols_mqtt_ws but return a examples_protocols_mqtt_wss failure
                match_result = artifact_info["app_dir"].endswith(app_path)
            if config_name:
                match_result = match_result and config_name == artifact_info["config"]
            if target:
                match_result = match_result and target == artifact_info["target"]
            if match_result:
                ret = artifact_info
                break
        else:
            ret = None
        return ret

    def download_artifacts(self):
        if self.artifact_info:
            base_path = os.path.join(self.artifact_info["work_dir"], self.artifact_info["build_dir"])
            job_id = self.artifact_info["ci_job_id"]

            # 1. download flash args file
            if self.artifact_info["build_system"] == "cmake":
                flash_arg_file = os.path.join(base_path, "flasher_args.json")
            else:
                flash_arg_file = os.path.join(base_path, "download.config")

            self.gitlab_inst.download_artifact(job_id, [flash_arg_file], self.dest_root_path)

            # 2. download all binary files
            flash_files, flash_settings, app_name = parse_flash_settings(self.context.config.userdata,
                                                                         os.path.join(self.dest_root_path, flash_arg_file))
            artifact_files = [os.path.join(base_path, p[1]) for p in flash_files]
            artifact_files.append(os.path.join(base_path, app_name + ".elf"))

            self.gitlab_inst.download_artifact(job_id, artifact_files, self.dest_root_path)

            # 3. download sdkconfig file
            self.gitlab_inst.download_artifact(job_id, [os.path.join(os.path.dirname(base_path), "sdkconfig")],
                                               self.dest_root_path)
        else:
            base_path = None
        return base_path

    def download_artifact_files(self, file_names):
        if self.artifact_info:
            base_path = os.path.join(self.artifact_info["work_dir"], self.artifact_info["build_dir"])
            job_id = self.artifact_info["ci_job_id"]

            # download all binary files
            artifact_files = [os.path.join(base_path, fn) for fn in file_names]
            self.gitlab_inst.download_artifact(job_id, artifact_files, self.dest_root_path)

            # download sdkconfig file
            self.gitlab_inst.download_artifact(job_id, [os.path.join(os.path.dirname(base_path), "sdkconfig")],
                                               self.dest_root_path)
        else:
            base_path = None
        return base_path


class ESYSApp(App.BaseApp):
    """
    Implements common esp-idf application behavior.
    idf applications should inherent from this class and overwrite method get_binary_path.
    """

    IDF_DOWNLOAD_CONFIG_FILE = "download.config"
    IDF_FLASH_ARGS_FILE = "flasher_args.json"

    def __init__(self, app_path, config_name=None, target=None, context=None):
        super(ESYSApp, self).__init__(app_path)
        self.sha256 = ''
        self.firm_version = ''
        self.serial = ''
        self.bin_app_file = ''
        self.app_name = app_path
        self.config_name = config_name
        self.target = target
        self.context = context
        self.idf_path = self.get_sdk_path()
        self.binary_path = self.get_binary_path(app_path, config_name, target)
        self.elf_file = self._get_elf_file_path(self.binary_path)
        self._elf_file_sha256 = None
        assert os.path.exists(self.binary_path)
        if self.IDF_DOWNLOAD_CONFIG_FILE not in os.listdir(self.binary_path):
            if self.IDF_FLASH_ARGS_FILE not in os.listdir(self.binary_path):
                msg = ("Neither {} nor {} exists. "
                       "Try to run 'make print_flash_cmd | tail -n 1 > {}/{}' "
                       "or 'idf.py build' "
                       "for resolving the issue."
                       "").format(self.IDF_DOWNLOAD_CONFIG_FILE, self.IDF_FLASH_ARGS_FILE,
                                  self.binary_path, self.IDF_DOWNLOAD_CONFIG_FILE)
                raise AssertionError(msg)

        self.flash_files, self.flash_settings = self._parse_flash_download_config()
        self.partition_table = self._parse_partition_table()

    @classmethod
    def get_sdk_path(cls):
        # type: () -> str
        idf_path = os.getenv("IDF_PATH")
        assert idf_path
        assert os.path.exists(idf_path)
        return idf_path

    def _get_sdkconfig_paths(self):
        """
        returns list of possible paths where sdkconfig could be found

        Note: could be overwritten by a derived class to provide other locations or order
        """
        return [os.path.join(self.binary_path, "sdkconfig"), os.path.join(self.binary_path, "sdkconfig")]
        # return [os.path.join(self.binary_path, "sdkconfig"), os.path.join(self.binary_path, "..", "sdkconfig")]

    def get_sdkconfig(self):
        """
        reads sdkconfig and returns a dictionary with all configuredvariables

        :raise: AssertionError: if sdkconfig file does not exist in defined paths
        """
        d = {}
        sdkconfig_file = None
        for i in self._get_sdkconfig_paths():
            if os.path.exists(i):
                sdkconfig_file = i
                break
        assert sdkconfig_file is not None
        with open(sdkconfig_file) as f:
            for line in f:
                configs = line.split('=')
                if len(configs) == 2:
                    d[configs[0]] = configs[1].rstrip()
        return d

    def get_binary_path(self, app_path, config_name=None, target=None):
        # type: (str, str, str) -> str
        """
        get binary path according to input app_path.

        subclass must overwrite this method.

        :param app_path: path of application
        :param config_name: name of the application build config. Will match any config if None
        :param target: target name. Will match for target if None
        :return: abs app binary path
        """
        pass

    @staticmethod
    def _get_elf_file_path(binary_path):
        ret = ""
        file_names = os.listdir(binary_path)
        for fn in file_names:
            if os.path.splitext(fn)[1] == ".elf":
                ret = os.path.join(binary_path, fn)
        return ret

    def _parse_flash_download_config(self):
        """
        Parse flash download config from build metadata files

        Sets self.flash_files, self.flash_settings

        (Called from constructor)

        Returns (flash_files, flash_settings)
        """

        if self.IDF_FLASH_ARGS_FILE in os.listdir(self.binary_path):
            # CMake version using build metadata file
            path = os.path.join(self.binary_path, self.IDF_FLASH_ARGS_FILE)
        else:
            # GNU Make version uses download.config arguments file
            path = os.path.join(self.binary_path, self.IDF_DOWNLOAD_CONFIG_FILE)

        flash_files, flash_settings, app_name = parse_flash_settings(self.context.config.userdata, path)
        # The build metadata file does not currently have details, which files should be encrypted and which not.
        # Assume that all files should be encrypted if flash encryption is enabled in development mode.
        sdkconfig_dict = self.get_sdkconfig()
        flash_settings["encrypt"] = "CONFIG_SECURE_FLASH_ENCRYPTION_MODE_DEVELOPMENT" in sdkconfig_dict

        # make file offsets into integers, make paths absolute
        flash_files = [(int(offs, 0), os.path.join(self.binary_path, file_path.strip())) for (offs, file_path) in
                       flash_files]

        return flash_files, flash_settings

    def _parse_partition_table(self):
        """
        Parse partition table contents based on app binaries

        Returns partition_table data

        (Called from constructor)
        """
        partition_tool = os.path.join(self.idf_path,
                                      "components",
                                      "partition_table",
                                      "gen_esp32part.py")
        assert os.path.exists(partition_tool)

        errors = []
        # self.flash_files is sorted based on offset in order to have a consistent result with different versions of
        # Python
        for (_, path) in sorted(self.flash_files, key=lambda elem: elem[0]):
            if 'partition' in os.path.split(path)[1]:
                partition_file = os.path.join(self.binary_path, path)

                process = subprocess.Popen([sys.executable, partition_tool, partition_file],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (raw_data, raw_error) = process.communicate()
                if isinstance(raw_error, bytes):
                    raw_error = raw_error.decode()
                if 'Traceback' in raw_error:
                    # Some exception occured. It is possible that we've tried the wrong binary file.
                    errors.append((path, raw_error))
                    continue

                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode()
                break
        else:
            traceback_msg = os.linesep.join(['{} {}:{}{}'.format(partition_tool,
                                                                 p,
                                                                 os.linesep,
                                                                 msg) for p, msg in errors])
            raise ValueError("No partition table found for IDF binary path: {}{}{}".format(self.binary_path,
                                                                                           os.linesep,
                                                                                           traceback_msg))

        partition_table = dict()
        for line in raw_data.splitlines():
            if line[0] != "#":
                try:
                    _name, _type, _subtype, _offset, _size, _flags = line.split(",")
                    if _size[-1] == "K":
                        _size = int(_size[:-1]) * 1024
                    elif _size[-1] == "M":
                        _size = int(_size[:-1]) * 1024 * 1024
                    else:
                        _size = int(_size)
                    _offset = int(_offset, 0)
                except ValueError:
                    continue
                partition_table[_name] = {
                    "type": _type,
                    "subtype": _subtype,
                    "offset": _offset,
                    "size": _size,
                    "flags": _flags
                }

        return partition_table

    def get_elf_sha256(self):
        if self._elf_file_sha256:
            return self._elf_file_sha256

        sha256 = hashlib.sha256()
        with open(self.elf_file, 'rb') as f:
            sha256.update(f.read())
        self._elf_file_sha256 = sha256.hexdigest()
        return self._elf_file_sha256


class SiArtifact(ESYSApp):
    def __init__(self, app_path, config_name=None, target=None, context=None):
        super(SiArtifact, self).__init__(app_path, config_name, target, context)

    def _get_sdkconfig_paths(self):
        """
        overrides the parent method to provide exact path of sdkconfig for example tests
        """
        return [os.path.join(self.binary_path, "sdkconfig")]

    def _try_get_binary_from_local_fs(self, app_path, config_name=None, target=None, local_build_dir="build_examples"):
        # build folder of example path
        path = os.getcwd()
        # path = os.path.join(self.idf_path, app_path, "build")
        if os.path.exists(path):
            return path

        if not config_name:
            config_name = "default"

        if not target:
            target = "esp32"

        # Search for CI build folders.
        # Path format: $IDF_PATH/build_examples/app_path_with_underscores/config/target
        # (see tools/ci/build_examples_cmake.sh)
        # For example: $IDF_PATH/build_examples/examples_get-started_blink/default/esp32
        app_path_underscored = app_path.replace(os.path.sep, "_")
        example_path = os.path.join(self.idf_path, local_build_dir)
        for dirpath in os.listdir(example_path):
            if os.path.basename(dirpath) == app_path_underscored:
                path = os.path.join(example_path, dirpath, config_name, target, "build")
                if os.path.exists(path):
                    return path
                else:
                    return None

    def get_binary_input_job_id(self):
        gitlab_inst = gitlab_api.Gitlab(project_name=self.context.gitlab_proj)

        if 'job_id' in self.context.config.userdata:
            job_id = self.context.config.userdata['job_id']
        else:
            assert False, 'No job ID in argument'
        # Download into current directory and zip extract into build directory
        self.bin_app_file = gitlab_inst.download_artifacts(job_id, '.')

    def get_binary_latest_job_id(self):
        if self.app_name == 'si_app':
            project_name = 'sentry-interface'
        if self.app_name == 'sr_app':
            project_name = 'sentry-reader'

        gitlab_inst = gitlab_api.Gitlab(project_name=project_name)

        # As the job list is too long, we only need the latest 50 ones.
        jobs = gitlab_inst.project.jobs.list(page=1, per_page=50)
        job_id = 0
        for job in jobs:
            if hasattr(job, 'artifacts_file') and job.name == 'uat-build-job' and job.status == 'success':
                job_id = job.id
                break

        # Download into current directory and zip extract into build directory
        self.bin_app_file = gitlab_inst.download_artifacts(job_id, '.')

    def get_binary_path(self, app_path, config_name=None, target=None):

        if self.context.gitlab_proj == 'sentry-interface':
            gitlab_app = 'si_app'
        if self.context.gitlab_proj == 'sentry-reader':
            gitlab_app = 'sr_app'

        if gitlab_app == app_path:
            self.get_binary_input_job_id()
        else:
            # Use AWS S3 golden binary, which is already got before, so that it matches with partition version,
            # because we don't know what partition version the latest one is in GitLab by calling
            # self.get_binary_latest_job_id()
            return os.getcwd()

        # Extract version no. and SHA256 checksum from the file name
        verIdx = self.bin_app_file.find('_v')
        self.firm_version = self.bin_app_file[verIdx+2:verIdx+7]
        sha256Idx = self.bin_app_file.find('_sha256')
        self.sha256 = self.bin_app_file[sha256Idx-8:sha256Idx]

        return os.getcwd()

    def _parse_flash_download_config(self):
        """
        Parse flash download config from build metadata files and use artifact binary

        Sets self.flash_files, self.flash_settings

        (Called from constructor)

        Returns (flash_files, flash_settings)
        """

        if self.IDF_FLASH_ARGS_FILE in os.listdir(self.binary_path):
            # CMake version using build metadata file
            path = os.path.join(self.binary_path, self.IDF_FLASH_ARGS_FILE)
        else:
            # GNU Make version uses download.config arguments file
            path = os.path.join(self.binary_path, self.IDF_DOWNLOAD_CONFIG_FILE)

        flash_files, flash_settings, app_name = parse_flash_settings(self.context.config.userdata,path)
        # The build metadata file does not currently have details, which files should be encrypted and which not.
        # Assume that all files should be encrypted if flash encryption is enabled in development mode.
        sdkconfig_dict = self.get_sdkconfig()
        flash_settings["encrypt"] = "CONFIG_SECURE_FLASH_ENCRYPTION_MODE_DEVELOPMENT" in sdkconfig_dict

        # make file offsets into integers, make paths absolute
        flash_files = [(int(offs, 0), os.path.join(self.binary_path, file_path.strip())) for (offs, file_path) in
                       flash_files]

        # update the app bin file to be flashed as downloaded artifact. The app bin file is located at flash_files[3]
        list_binary = list(flash_files[3])

        bin_file = os.path.join(self.binary_path, self.bin_app_file)
        list_binary[1] = bin_file
        flash_files[3] = tuple(list_binary)

        return flash_files, flash_settings



class SiApp(ESYSApp):
    def _get_sdkconfig_paths(self):
        """
        overrides the parent method to provide exact path of sdkconfig for example tests
        """
        return [os.path.join(self.binary_path, "sdkconfig")]

    def _try_get_binary_from_local_fs(self, app_path, config_name=None, target=None, local_build_dir="build_examples"):
        # build folder of example path
        path = os.getcwd()
        # path = os.path.join(self.idf_path, app_path, "build")
        if os.path.exists(path):
            return path

        if not config_name:
            config_name = "default"

        if not target:
            target = "esp32"

        # Search for CI build folders.
        # Path format: $IDF_PATH/build_examples/app_path_with_underscores/config/target
        # (see tools/ci/build_examples_cmake.sh)
        # For example: $IDF_PATH/build_examples/examples_get-started_blink/default/esp32
        app_path_underscored = app_path.replace(os.path.sep, "_")
        example_path = os.path.join(self.idf_path, local_build_dir)
        for dirpath in os.listdir(example_path):
            if os.path.basename(dirpath) == app_path_underscored:
                path = os.path.join(example_path, dirpath, config_name, target, "build")
                if os.path.exists(path):
                    return path
                else:
                    return None

    def get_binary_path(self, app_path, config_name=None, target=None):
        self.firm_version = self.context.firm_version
        path = self._try_get_binary_from_local_fs(app_path, config_name, target)
        if path:
            return path
        else:
            artifacts = Artifacts(self.idf_path,
                                  CIAssignExampleTest.get_artifact_index_file(
                                      case_group=CIAssignExampleTest.ExampleGroup),
                                  app_path, config_name, target)
            path = artifacts.download_artifacts()
            if path:
                return os.path.join(self.idf_path, path)
            else:
                raise OSError("Failed to find example binary")

    def _parse_flash_download_config(self):
        """
        Parse flash download config from build metadata files and use defined binary file in build folder

        Sets self.flash_files, self.flash_settings

        (Called from constructor)

        Returns (flash_files, flash_settings)
        """
        if self.IDF_FLASH_ARGS_FILE in os.listdir(self.binary_path):
            # CMake version using build metadata file
            path = os.path.join(self.binary_path, self.IDF_FLASH_ARGS_FILE)
        else:
            # GNU Make version uses download.config arguments file
            path = os.path.join(self.binary_path, self.IDF_DOWNLOAD_CONFIG_FILE)

        flash_files, flash_settings, app_name = parse_flash_settings(self.context.config.userdata, path)
        # The build metadata file does not currently have details, which files should be encrypted and which not.
        # Assume that all files should be encrypted if flash encryption is enabled in development mode.
        sdkconfig_dict = self.get_sdkconfig()
        flash_settings["encrypt"] = "CONFIG_SECURE_FLASH_ENCRYPTION_MODE_DEVELOPMENT" in sdkconfig_dict

        # make file offsets into integers, make paths absolute
        flash_files = [(int(offs, 0), os.path.join(self.binary_path, file_path.strip())) for (offs, file_path) in
                       flash_files]

        # update the app bin file to be flashed as defined binary file. The app bin file is located at flash_files[3]
        list_binary = list(flash_files[3])

        self.bin_app_file = os.path.join('build', self.context.firm_name)
        bin_file = os.path.join(self.binary_path, self.bin_app_file)
        list_binary[1] = bin_file
        flash_files[3] = tuple(list_binary)

        return flash_files, flash_settings

class SiAppPreBuilt(ESYSApp):
    def _get_sdkconfig_paths(self):
        """
        overrides the parent method to provide exact path of sdkconfig for example tests
        """
        return [os.path.join(self.binary_path, "sdkconfig")]
        #return [os.path.join(self.binary_path, "..", "sdkconfig")]

    def _try_get_binary_from_local_fs(self, app_path, config_name=None, target=None, local_build_dir="build_examples"):
        # build folder of example path
        path = os.path.join(self.idf_path, app_path, "build")
        if os.path.exists(path):
            return path

        if not config_name:
            config_name = "default"

        if not target:
            target = "esp32"

        # Search for CI build folders.
        # Path format: $IDF_PATH/build_examples/app_path_with_underscores/config/target
        # (see tools/ci/build_examples_cmake.sh)
        # For example: $IDF_PATH/build_examples/examples_get-started_blink/default/esp32
        app_path_underscored = app_path.replace(os.path.sep, "_")
        example_path = os.path.join(self.idf_path, local_build_dir)
        for dirpath in os.listdir(example_path):
            if os.path.basename(dirpath) == app_path_underscored:
                path = os.path.join(example_path, dirpath, config_name, target, "build")
                if os.path.exists(path):
                    return path
                else:
                    return None

    def get_binary_path(self, app_path, config_name=None, target=None):
        """Some values defaulted to S3 if they are empty"""
        try:
            S3_BUCKET_NAME = "afr-ota-sentry-firmware-qa"
            client = boto3.client(
                's3'
            )
            if self.context.firm_ref_app == 'ARTF_ref_apps':
                search_path = self.context.firm_ref_app
                partition_version = '3'
                if 'partition_version' in self.context.config.userdata:
                    partition_version = self.context.config.userdata['partition_version']
                if partition_version == '4':
                    search_path = search_path + '/v4'
                else:
                    search_path = search_path + '/v3'

                if app_path == 'si_app':
                    ref_app_search = search_path + '/hub'
                else:
                    ref_app_search = search_path + '/halo'
                s3 = boto3.resource('s3', region_name='eu-west-2')
                bucket = s3.Bucket(S3_BUCKET_NAME)
                objects = bucket.objects.filter(Prefix=search_path)
                object_name = None
                for obj in objects:
                    if obj.key.startswith(ref_app_search):
                        object_name = obj.key
                        fileNameIdx = obj.key.find('/h')
                        self.context.firm_name = obj.key[fileNameIdx+1:]
                        break
            else:
                object_name = self.context.firm_name

            if object_name is not None:
                os.makedirs('build', mode=0o777, exist_ok=True)
                self.bin_app_file = os.path.join('build', self.context.firm_name)
                print("download from S3: " + object_name)
                client.download_file(S3_BUCKET_NAME, object_name, self.bin_app_file)
                print(object_name)

        except Exception as ex:
            print("Could not find binary in S3 bucket. Error msg: ")
            print(ex)
            raise ex

        # Extract version no. and SHA256 checksum from the file name
        verIdx = self.bin_app_file.find('_v')
        if verIdx != -1:
            self.firm_version = self.bin_app_file[verIdx+2:verIdx+7]

        sha256Idx = self.bin_app_file.find('_sha256')
        if sha256Idx != -1:
            self.sha256 = self.bin_app_file[sha256Idx-8:sha256Idx]
        else:
            self.sha256 = None

        path = os.path.dirname(os.path.abspath(self.context.firm_name))
        if path:
            return os.path.join(path)
        else:
            raise OSError("Failed to find example binary")

    def _parse_flash_download_config(self):
        """
        Parse flash download config from build metadata files and use S3 binary file saved in build folder

        Sets self.flash_files, self.flash_settings

        (Called from constructor)

        Returns (flash_files, flash_settings)
        """
        if self.IDF_FLASH_ARGS_FILE in os.listdir(self.binary_path):
            # CMake version using build metadata file
            path = os.path.join(self.binary_path, self.IDF_FLASH_ARGS_FILE)
        else:
            # GNU Make version uses download.config arguments file
            path = os.path.join(self.binary_path, self.IDF_DOWNLOAD_CONFIG_FILE)

        flash_files, flash_settings, app_name = parse_flash_settings(self.context.config.userdata, path)
        # The build metadata file does not currently have details, which files should be encrypted and which not.
        # Assume that all files should be encrypted if flash encryption is enabled in development mode.
        sdkconfig_dict = self.get_sdkconfig()
        flash_settings["encrypt"] = "CONFIG_SECURE_FLASH_ENCRYPTION_MODE_DEVELOPMENT" in sdkconfig_dict

        # make file offsets into integers, make paths absolute
        flash_files = [(int(offs, 0), os.path.join(self.binary_path, file_path.strip())) for (offs, file_path) in
                       flash_files]

        # update the app bin file to be flashed as S3 binary file. The app bin file is located at flash_files[3]
        list_binary = list(flash_files[3])

        self.bin_app_file = os.path.join('build', self.context.firm_name)
        bin_file = os.path.join(self.binary_path, self.bin_app_file)
        list_binary[1] = bin_file
        flash_files[3] = tuple(list_binary)

        return flash_files, flash_settings


class UT(ESYSApp):
    def get_binary_path(self, app_path, config_name=None, target=None):
        if not config_name:
            config_name = "default"

        path = os.path.join(self.idf_path, app_path)
        default_build_path = os.path.join(path, "build")
        if os.path.exists(default_build_path):
            return default_build_path

        # first try to get from build folder of unit-test-app
        path = os.path.join(self.idf_path, "tools", "unit-test-app", "build")
        if os.path.exists(path):
            # found, use bin in build path
            return path

        # ``make ut-build-all-configs`` or ``make ut-build-CONFIG`` will copy binary to output folder
        path = os.path.join(self.idf_path, "tools", "unit-test-app", "output", target, config_name)
        if os.path.exists(path):
            return path

        raise OSError("Failed to get unit-test-app binary path")


class TestApp(SiApp):
    def get_binary_path(self, app_path, config_name=None, target=None):
        path = self._try_get_binary_from_local_fs(app_path, config_name, target, local_build_dir="build_test_apps")
        if path:
            return path
        else:
            artifacts = Artifacts(self.idf_path,
                                  CIAssignExampleTest.get_artifact_index_file(
                                      case_group=CIAssignExampleTest.TestAppsGroup),
                                  app_path, config_name, target)
            path = artifacts.download_artifacts()
            if path:
                return os.path.join(self.idf_path, path)
            else:
                raise OSError("Failed to find example binary")


class LoadableElfTestApp(TestApp):
    def __init__(self, app_path, app_files, config_name=None, target=None):
        # add arg `app_files` for loadable elf test_app.
        # Such examples only build elf files, so it doesn't generate flasher_args.json.
        # So we can't get app files from config file. Test case should pass it to application.
        super(IDFApp, self).__init__(app_path)
        self.app_files = app_files
        self.config_name = config_name
        self.target = target
        self.idf_path = self.get_sdk_path()
        self.binary_path = self.get_binary_path(app_path, config_name, target)
        self.elf_file = self._get_elf_file_path(self.binary_path)
        assert os.path.exists(self.binary_path)

    def get_binary_path(self, app_path, config_name=None, target=None):
        path = self._try_get_binary_from_local_fs(app_path, config_name, target, local_build_dir="build_test_apps")
        if path:
            return path
        else:
            artifacts = Artifacts(self.idf_path,
                                  CIAssignExampleTest.get_artifact_index_file(
                                      case_group=CIAssignExampleTest.TestAppsGroup),
                                  app_path, config_name, target)
            path = artifacts.download_artifact_files(self.app_files)
            if path:
                return os.path.join(self.idf_path, path)
            else:
                raise OSError("Failed to find the loadable ELF file")


class SSC(ESYSApp):
    def get_binary_path(self, app_path, config_name=None, target=None):
        # TODO: to implement SSC get binary path
        return app_path


class AT(ESYSApp):
    def get_binary_path(self, app_path, config_name=None, target=None):
        # TODO: to implement AT get binary path
        return app_path
