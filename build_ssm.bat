echo "Setup enviromemnt variables"
SET COBDIR=C:\Program Files (x86)\Micro Focus\Enterprise Developer\;%COBDIR%
SET PATH=C:\Program Files (x86)\Micro Focus\Enterprise Developer\bin64\;C:\Program Files (x86)\Micro Focus\Enterprise Developer\binn64\;C:\Program Files (x86)\Micro Focus\Enterprise Developer\bin\;C:\Program Files (x86)\Micro Focus\Enterprise Developer\AdoptOpenJDK\bin;C:\Program Files (x86)\Micro Focus\Enterprise Developer\AdoptRedis;%PATH%
SET LIB=C:\Program Files (x86)\Micro Focus\Enterprise Developer\lib64\;%LIB%
SET COBCPY=%COBCPY%;C:\Program Files (x86)\Micro Focus\Enterprise Developer\cpylib\;C:\Program Files (x86)\Micro Focus\Enterprise Developer\cpylib\basecl
SET MFTRACE_ANNOTATIONS=C:\Program Files (x86)\Micro Focus\Enterprise Developer\etc\mftrace\annotations
SET MFTRACE_LOGS=C:\ProgramData\Micro Focus\Enterprise Developer\5.0\mftrace\logs
SET INCLUDE=C:\Program Files (x86)\Micro Focus\Enterprise Developer\include;%INCLUDE%
SET JAVA_HOME=C:\Program Files (x86)\Micro Focus\Enterprise Developer\AdoptOpenJDK
SET CLASSPATH=C:\Program Files (x86)\Micro Focus\Enterprise Developer\bin\mfcobol.jar;C:\Program Files (x86)\Micro Focus\Enterprise Developer\bin\mfcobolrts.jar;C:\Program Files (x86)\Micro Focus\Enterprise Developer\bin\mfsqljvm.jar;C:\Program Files (x86)\Micro Focus\Enterprise Developer\bin\cw_java.jar;C:\Program Files (x86)\Micro Focus\Enterprise Developer\bin\mfunit.jar;C:\Program Files (x86)\Micro Focus\Enterprise Developer\bin\mfidmr.jar;%CLASSPATH%
SET MFDBFH_SCRIPT_DIR=C:\Program Files (x86)\Micro Focus\Enterprise Developer\etc\mfdbfh\scripts
SET MFPLI_PRODUCT_DIR=C:\Program Files (x86)\Micro Focus\Enterprise Developer\
SET TXDIR=C:\Program Files (x86)\Micro Focus\Enterprise Developer\
SET COBREG_64_PARSED=True

SET COBCPY=c:\build\copybook
SET BUILD_BUCKET=%1
SET SOURCE_FOLDER=%2

cd \
echo "Cleanup work directory"
if exist log (rmdir log /s /q)
if exist build (rmdir build /s /q)

echo "Downloading artifact zip"
mkdir log
aws s3 cp s3://%BUILD_BUCKET%/%SOURCE_FOLDER%/artifacts.zip \artifacts.zip --quiet
PowerShell Expand-Archive -Path \artifacts.zip -DestinationPath \
rename bankTest build
cd build\cbl
aws s3 cp s3://%BUILD_BUCKET%/diretivas_compilacao.dir diretivas_compilacao.dir --quiet

echo "Building cobol files"
For %%A in (*.cbl) do cobol %%A,,,preprocess(EXCI) USE(diretivas_compilacao.dir); > c:\log\%%A-cobol.log 2> c:\log\%%A-cobol.err

echo "Building dll files"
For %%A in (*.obj) do cbllink -d %%A > c:\log\%%A-cbllink.log 2> c:\log\%%A-cbllink.err

echo "Wait 5 seconds to work with compiled files"
ping -n 5 127.0.0.1 >nul

echo "Remove 0 bytes files from log directory"
cd \log
for /r %%F in (*) do if %%~zF==0 del "%%F"

echo "Coping log files to bucket"
cd \
aws s3 cp log s3://%BUILD_BUCKET%/%SOURCE_FOLDER%/log --recursive --acl bucket-owner-full-control --quiet


if exist \log\*.err (
    echo "Sending fail information to the pipeline"
    aws codepipeline put-job-failure-result --job-id %2 --failure-details type=JobFailed,message="Build process failed. Check bucket for details: s3://%BUILD_BUCKET%/%SOURCE_FOLDER%/log" --region us-west-2

    echo "Sending signal to finish the process with fail"
    aws sns publish --topic-arn %3 --subject "build completed with a result of 'failed'" --message s3://%BUILD_BUCKET%/%SOURCE_FOLDER%/log --message-attributes ec2_instance={DataType=String,StringValue=%4} --region us-west-2

    echo "Removing control tag from ec2"
    aws ec2 delete-tags --resources %INSTANCE_ID% --tags Key=job_id,Value=%SOURCE_FOLDER%

    echo "Copying process log file to bucket"
    aws s3 cp %SystemRoot%\Temp\process.log s3://%BUILD_BUCKET%/%SOURCE_FOLDER%/process.log --acl bucket-owner-full-control --quiet

    echo "Stopping ec2 instance"
    shutdown.exe /s /t 00
) else (
    echo "Starting MicroFocus services"
    net start mfcesd
    net start mf_CCITCP2

    net start escwa
    net start "EA Integration Service Host"
    net start "Micro Focus XDB Server for ETD 5.0"

    echo "Copying dll files"
    cd build\cbl
    For %%A in (*.dll) do copy %%A C:\Microfocus\bankTest\loadlib\%%A

    echo "Wait 10 seconds to start service"
    ping -n 10 127.0.0.1 >nul

    echo "Starting project"
    casstart /rBANKDEMO

    echo "Sending success information to the pipeline"
    aws codepipeline put-job-success-result --job-id %2 --region us-west-2

    echo "Copying dll files to bucket"
    aws s3 cp \build\cbl s3://%BUILD_BUCKET%/%SOURCE_FOLDER%/dll_files/ --acl bucket-owner-full-control --recursive --quiet --exclude "*" --include "*.dll"

    echo "Sending signal to finish the process with success"
    aws sns publish --topic-arn %3 --subject "build completed with a result of 'success'" --message "PrivateIpAddress: %5" --message-attributes ec2_instance={DataType=String,StringValue=%4} --region us-west-2    

    echo "Copying process log file to bucket"
    aws s3 cp %SystemRoot%\Temp\process.log s3://%BUILD_BUCKET%/%SOURCE_FOLDER%/process.log --acl bucket-owner-full-control --quiet
)