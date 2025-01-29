# Device-lib toolbox

This repository contains multiple scripts(tools) to make easy certain common processes with IoT devices.

Each tool is possibly utilized by users or software components.

Each script has --help function.

When the project is pushed to the repository, the following scripts are automatically generated as Windows executable files and stored in GitLab CI/CD artifacts:
* flash
* start_ota
* provision
* mac

Whenever a developer modifies the above scripts, the developer should verify if the executable files work properly since the final products are the exe files but not the python scripts.

### Compatible architectures
**exe files**
* x86

**python files**
* x86
* v7arm


### Compatible OS
**exe files**
* Windows 10

**python files**
* Ubuntu 18.04 LTS (or higher)
* Windows 10
* Raspberry Pi OS

### Dependencies
**exe files**
* No dependency

**python files**
* Python 3.7 or higher
* venv


### Device libaries executable artifact
https://gitlab.com/essensys1/flex/interfaces/firmware/device-lib/-/pipelines

Download the latest pipline artifacts and unzip the file to get the exeuctables

### Development environment setup
The development is done in Windows in order to create Windows executables
1. Install CP210x driver
https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers

2. Create your virtual environment: `python -m venv .venv`
3. Activate venv: `PS C:\work\embedded_workspace\device-lib> .\.venv\Scripts\activate`
4. Install requirements on venv: `(.venv) PS C:\work\embedded_workspace\device-lib> pip install -r .\requirements.txt`

## Flash firmware executable
It flashes the application binary into the device
### Examples
```
flash --help
flash -p COM5
flash -p COM5 -e -app hub_app_v2.1.1_405c957_c19939e3_sha256.bin -boot bootloader.bin -ota_data ota_data_initial.bin -table partition-table.bin -part_start 0xc000 -ota_data_start 0x30d000 -app_start 0x310000
flash -p COM5 -e -app hub_app_v2.1.1_405c957_c19939e3_sha256.bin -boot none -ota_data none -table none 
```
* -p: com port
* -e: Add this option if flash memory is already encrypted
* -app: application binary file
* -boot: bootloader file.  If it's set as none, the file won't be downloaded
* -ota: ota data initial file. If it's set as none, the file won't be downloaded
* -table: partition table file. If it's set as none, the file won't be downloaded 
* -part_start: partition table start offset address (in hex form start with 0x)
* -ota_data_start: ota data initial table start offset address (in hex form start with 0x)
* -app_start: application binary start offset address (in hex form start with 0x)

**Config feature**

The script creates a config.ini file next to the flash.exe and saves the latest inputs into the file.
In case a parameter is not given as argument it will try to load from the config.ini file.
This means you need to give the parameters only once.
After that you can just call the flash.exe without any parameters or with a subset of the parameters that you want to change compared to the previous call.
You can also change the config file as you wish.

**Create executable file in development**
```
pyinstaller --onefile --hidden-import esptool --hidden-import esp-afr-sdk.components.nvs_flash.nvs_partition_generator.nvs_partition_gen  --paths .\esp-afr-sdk\components\nvs_flash\nvs_partition_generator --paths .\esptool_release_v3 flash.py
```
The executable file is located in dist directory

## OTA firmware executable
It run AWS OTA service to flashes the application binary into the device
### Examples
```
start_ota --help
start_ota -sn e0e2e65b5ddc -ft 1 -app halo_app_v2.0.2_94f6da7_948308c9_sha256.bin
```
* -sn serial number
* -ft file type: 1 = hub OTA, 2 = halo OTA
* -app binary file

**Create executable file in development**
```
pyinstaller --onefile --hidden-import configparser --hidden-import esp-afr-sdk.components.nvs_flash.nvs_partition_generator.nvs_partition_gen --paths .\esp-afr-sdk\components\nvs_flash\nvs_partition_generator start_ota.py
```
The executable file is located in dist directory
## Provision firmware executable
This tool is a one-stop tool to do AWS IoT provision of hardware devices:
* register a thing record
* create and flash certificate and private key into non-volatile storage (NVS) of devices
* can work with USB barcode scanner to get serial number
### Usage 

**Enter serial no. manually** 
```
provision -sn e0e2e65b5ddc -p COM5
provision -sn e0e2e65b5ddc -p COM5 -cert_start 0x7ed000 -cert_size 40960 -key_start 0x7f8000
```
**Scan serial no. by USB barcode scanner**
```
provision -p COM5
provision -p COM5 -cert_start 0x7ed000 -cert_size 40960 -key_start 0x7f8000
```
* -p, port number connected to PC. e.g. COM6
* -sn, serial number. If no this argument, serial no. is read from barcode 
scanner
* -cert_start, NVS AWS certificate partition start address (hex form in 0xaaaaa)
* -cert_size, NVS AWS certificate partition size in bytes (decimal)
* -key_start, NVS cert encryption key partition start address (hex form in 0xaaaaa)

**Config feature**

The script creates a config.ini file next to the provision.exe and saves the latest inputs into the file.
In case a parameter is not given as argument it will try to load from the config.ini file.
This means you need to give the parameters only once.
After that you can just call the provision.exe without any parameters or with a subset of the parameters that you want to change compared to the previous call.
You can also change the config file as you wish.

**Create executable file in development**
```
pyinstaller --onefile --hidden-import configparser --hidden-import esptool --hidden-import nvs_partition_gen --hidden-import esp-afr-sdk.components.nvs_flash.nvs_partition_generator.nvs_partition_gen --paths .\esp-afr-sdk\components\nvs_flash\nvs_partition_generator --paths .\esptool_release_v3 provision.py
```
The executable file is located in dist directory

## Set MAC address executable
This tool is to flash the custom MAC address into efuse of the device, if the efuse for custom MAC address is empty. There is two modes:
* Production mode: checks if ESP32 chip version is "ESP32-D0WD-V3" before proceeding flashing mac
* Development mode: does not check check if ESP32 chip version is "ESP32-D0WD-V3" before proceeding flashing mac
#### Usage
**Enter serial no. manually and flash into efuse in production mode.**
```
mac -sn e0e2e65b5ddc -p COM5 -m prod -f
```
**Scan serial no. by USB barcode scanner into efuse in production mode.**
```
mac -p COM5 -m prod -f
```
**Scan serial no. by USB barcode scanner in development mode for testing.**
```
mac -p COM5 -m dev
```
* -p, [REQUIRED] port number connected to PC. e.g. COM6
* -m, [REQUIRED] mode: dev or prod. If this is production mode, it checks if ESP32 chip version is "ESP32-D0WD-V3" before proceeding flashing mac.
* -sn, [OPTIONAL] serial number. If no this argument, serial no. is read from barcode scanner
* -f, [OPTIONAL] flash efuse. Add this argument to flash custom mac into efuse of ESP32. If no this argument, it just runs the test mac address flashing procedure without real flashing.


**Create executable file in development**
```
pyinstaller --onefile --hidden-import esptool --hidden-import espefuse --hidden-import esp-afr-sdk.components.nvs_flash.nvs_partition_generator.nvs_partition_gen --paths .\esp-afr-sdk\components\nvs_flash\nvs_partition_generator --paths .\esptool_release_v3 mac.py
```
The executable file is located in dist directory


### Device binaries in S3
https://s3.console.aws.amazon.com/s3/buckets/afr-ota-sentry-firmware-qa?region=eu-west-2&tab=objects

### Setup to Run This Tool.
**Windows**
1. Install CP210x driver
https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers

2. Create your virtual environment: `python -m venv .venv`
3. Activate venv: `PS C:\work\embedded_workspace\device-lib> .\.venv\Scripts\activate`
4. Install requirements on venv: `(.venv) PS C:\work\embedded_workspace\device-lib> pip install -r .\requirements.txt`
5. Run the scipt you need: `(.venv) PS C:\work\embedded_workspace\device-lib> python provision.py -sn abc123 -p COM9`

**Ubuntu**
```
...
```

**Raspberry Pi OS (v7arm)**
...

### Examples
```
$: python3 flash.py --help
$: python3 flash.py -sn e0e2e65b5ddc -p COM5
$: python3 flash.py -sn e0e2e65b5ddc -p COM5 -boot .\build\sr_bootloader.bin -app .\build\sr_app_v0_3_1.bin
```

### Main features
**1 .Config feature**
The script creates a .ini file next to the .py and saves the latest inputs into the file.
In case a parameter is not given as argument it will try to load from the .ini file.
This means you need to give the parameters only once.
After that you can just call the .py without any parameters or with a subset of the parameters that you want to change compared to the previous call.
You can also change the config file as you wish.

**2.Quick latest release flash feature**
With minimal argument the script will download the latest release binaries from S3 and flash it to the device.

**3. Auto device type detection**
It determines the device type from the serial number. 

**4. Run OTA Jobs from CommandLine** It picks the binary from either S3 or locally to execute a OTA JOB.

**5. Shadow Pubish** It picks up the configured JSON to update shadows for a range of things.

```
$: python3 flash.py -sn e0e2e65b5ddc -p COM5
$: python3 flash.py
```


***Examples for using virtual environment***
Make sure you are using this python interpreter. If you need new modules, update the requirements.txt in a way below  
```
& c:/work/device-lib/.venv/Scripts/python.exe c:/work/device-lib/provision.py -sn 123abc -p COM9
& c:/work/device-lib/.venv/Scripts/python.exe -m pip freeze > .\requirements.txt
& c:/work/device-lib/.venv/Scripts/python.exe -m pip install esptool==4.2.1
```

## OTA JOB "start_ota.py"
* It triggets the OTA job for the corresponding device.
* You can define your own parameters and job configurations.
* You send use the binary from Either S3 bucker or locally.
* This is applicable to Hub and Halo. 

#### Usage :
    
    $: start_ota.py -sn 349454ba73a0 -ft 1 -app C:\work\FIT-419-HUB\build\si_app.bin 
    

## Shadow Update tool "shadowpublish.py"
* It updates the desired status of the Shadow for the list of things mentioned in the script.
* Edit the list of thing names in ```shadowpubish.py``` . example:  ```listofthings =  ["e0e2e65b5ddc" , "esdfds65b5ddc"]``` 
* You can define your own parameters and configure. 
* This is applicable to Hub and Halo. 

#### Usage :
**To Lockdown all Devices** 

```
    $: python3 shadowpublish.py -jsonfile disablelockdown.json 
``` 
**To UN-Lockdown all Devices** 

```python provision.py -p COM5
    $: python3 shadowpublish.py -jsonfile enablelockdown.json
``` 
**To Publish settings to all Devices** 

```
    $: python3 shadowpublish.py -jsonfile customuserconfig.json 
``` 

    
## Provision tool "provision.py"
This tool is a one-stop tool to do AWS IoT provision of hardware devices:
* register a thing record
* create and flash certificate and private key into non-volatile storage (NVS) of devices


### Setup
**Windows**
1. Install CP210x driver
https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers

2. Create your virtual environment: `python -m venv .venv`
3. Activate venv: `PS C:\work\embedded_workspace\device-lib> .\.venv\Scripts\activate`
4. Install requirements on venv: `(.venv) PS C:\work\embedded_workspace\device-lib> pip install -r .\requirements.txt`
5. Run AWS multi-factor authentication, if credentials are invalid in the PC: `(.venv) PS C:\work\embedded_workspace\device-lib> aws-mfa`  
6. Run the scipt you need: `(.venv) PS C:\work\embedded_workspace\device-lib> python provision.py -sn abc123 -p COM9`

    #### Parameters
    * -p, [REQUIRED] port number connected to PC. e.g. COM6
    * -sn, [OPTIONAL] serial number. If no this argument, serial no. is read from barcode scanner

### Usage 

**Enter serial no. manually** 
```
$: python provision.py -sn e0e2e65b5ddc -p COM5
```
**Scan serial no. by USB barcode scanner**
```
$: python provision.py -p COM5
```
    
## Flash custom MAC address tool "mac.py"
This tool is to flash the custom MAC address into efuse of the device, if the efuse for custom MAC address is empty

### Setup
**Windows**
1. Install CP210x driver
https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers

2. Create your virtual environment: `python -m venv .venv`
3. Activate venv: `PS C:\work\embedded_workspace\device-lib> .\.venv\Scripts\activate`
4. Install requirements on venv: `(.venv) PS C:\work\embedded_workspace\device-lib> pip install -r .\requirements.txt`
5. Run the scipt you need: `(.venv) PS C:\work\embedded_workspace\device-lib> python mac.py -sn abc123 -p COM9 -m prod`

#### Parameters
* -p, [REQUIRED] port number connected to PC. e.g. COM6
* -m, [REQUIRED] mode: dev or prod. If this is production mode, it checks if ESP32 chip version is "ESP32-D0WD-V3" before proceeding flashing mac.
* -sn, [OPTIONAL] serial number. If no this argument, serial no. is read from barcode scanner
* -f, [OPTIONAL] flash efuse. Add this argument to flash custom mac into efuse of ESP32. If no this argument, it just runs the test mac address flashing procedure without real flashing.

#### Usage
**Enter serial no. manually and flash into efuse in development mode.**
```
$: python mac.py -sn e0e2e65b5ddc -p COM5 -m dev -f
```
**Scan serial no. by USB barcode scanner into efuse in production mode.**
```
$: python mac.py -p COM5 -m prod -f
```
**Scan serial no. by USB barcode scanner in development mode for testing.**
```
$: python mac.py -p COM5 -m dev
```
**Generate N amount of fallback records**
```
for ($i=0; $i -lt 100; $i++) {./fallback_v2.2_gen.py -cnr=10 -cid 15 -snr=16 -rnr=65 -c=True}
```


### Troubleshooting 

If the there permission errors. Run the following command in powershell.

```
$: Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Unrestricted
```


