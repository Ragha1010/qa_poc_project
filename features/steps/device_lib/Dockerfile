FROM mcr.microsoft.com/windows/servercore:ltsc2022
    
RUN powershell.exe -Command \
    $ErrorActionPreference = 'Stop'; \
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; \
    wget https://www.python.org/ftp/python/3.10.0/python-3.10.0.exe -OutFile c:\python-3.10.0.exe ; \
    Start-Process c:\python-3.10.0.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait ; \
    Remove-Item c:\python-3.10.0.exe -Force

RUN python -m pip install --upgrade pip pyinstaller
RUN python -m pip install bitstring==3.1.9 \
    boto3==1.24.70 \
    botocore==1.27.70 \
    cffi==1.15.1 \
    cryptography==38.0.1 \
    ecdsa==0.18.0 \
    jmespath==1.0.1 \
    pycparser==2.21 \
    pyserial==3.5 \
    pynput==1.7.6 \
    python-dateutil==2.8.2 \
    reedsolo==1.5.4 \
    s3transfer==0.6.0 \
    six==1.16.0 \
    urllib3==1.26.12
RUN python -m pip list
COPY ./esptool_release_v3  /esptool_release_v3/
COPY ./hardwares /hardwares/
CMD [ "cmd" ]


