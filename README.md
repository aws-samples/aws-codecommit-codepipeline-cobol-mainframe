# ***Enabling mainframe automated code build and deployment for financial institutions using AWS and Micro Focus solutions***

![alt text](https://github.com/aws-samples/aws-codecommit-codepipeline-cobol-mainframe/blob/master/figure_1.png)

**Mainframes** are used by **Financial Institutions** for critical applications, batch data processing, online transaction processing, and mixed concurrent workloads. Mainframes have non-functional requirements such as performance, security, and resource availability to process all workloads. However, a potential resource deadlock may occur during the parallel development of new programs and subsequent testing. For example, two or more programs needing to access the same DB2 table or VSAM file simultaneously can generate a deadlock situation.
Thus, the idea of this blogpost is to present a solution to the resource availability issue in the COBOL development process, using **Continuous Integration/Continuous Deployment services (CI/CD) from AWS** connected to an IDE such as Eclipse or Visual Studio. In the same pipeline of development, we use a plugin to connect **Micro Focus solution called Enterprise Developer**, for the step of compiling and running unit and functional tests.

**SOLUTION OVERVIEW**

The developer can use Git-compliant IDEs such as Eclipse or Visual Studio to make changes to COBOL code that are installed on desktops either locally using Amazon EC2 instances or the managed and secure Desktop as a Service (DaaS) solution named Amazon WorkSpaces. 

For example, download the Toolkit for Eclipse to connect to the AWS CodeCommit repository. Use your access key and the password of your AWS IAM registered user. Once installed and configured, the developer can clone a CodeCommit repository in Eclipse or create a CodeCommit repository from Eclipse via the AWS Explorer tab.

The automated build process uses an EC2 server as its environment, to run and for that server to be automatically configured, the process uses the functionality of execution templates. Execution templates allow you to store execution parameters so that you do not have to specify them each time you run an instance. For example, an execution template might contain the Operating System, instance type, permissions, and network settings that you typically use to run instances.

Using the execution template, the process creates an EC2 instance, which will be used in the code compilation process and also in the emulation of the mainframe environment. This EC2 instance has Micro Focus Enterprise Developer installed, which contains the COBOL compiler and Enterprise Server to perform the required tests. Attached to this blogpost are the main commands used to compile COBOL code.

The process launches the EC2 instance using the execution template and waits until this new instance is connected to the management platform AWS System Manager. When the connection to the management platform is complete, the process uses the functionality of Run Commands remotely to begin the validation and compilation phase of COBOL code.

Remote command execution, used to perform the COBOL code validation and compilation process, can send records to the AWS event management platform, thus keeping process execution records on the same platform, unifying and simplifying the monitoring and troubleshooting process.

When the process is finished, the script sends the compiled files and processing logs to the S3 bucket. That way, other processes may use this information for processing.

The next step in the process is waiting for the user to perform their unit and functional tests, with Micro Focus Enterprise Developer accessing the already running EC2 instance and setting up the emulation environment, including the application version. newly compiled. To make this possible, the developer receives an email announcement sent by the platform Amazon SNS together with Amazon SES.

One of the features CodePipeline provides is to pause pipeline execution pending user approval. Once the user approves, the pipeline continues to perform the next steps.

All pipeline steps as well as their status and execution times are available for consultation and follow-up in the CodePipeline console.

![alt text](https://github.com/aws-samples/aws-codecommit-codepipeline-cobol-mainframe/blob/master/MainframePipeline-8.jpg)

*Following is the summary of the with the flow of execution:*

**1- User connects and commits changes to AWS CodeCommit repository.**

**2- AWS CodePipeline starts build pipeline.**

**3- AWS CodeBuild sends build Instructions for an AWS Lambda function (addendum).**

**4- AWS Lambda stores source code in an Amazon S3 bucket.**

**5- AWS Lambda starts an Amazon EC2 instance.**

**6- AWS Lambda sends build instructions to AWS Systems Manager (addendum).**

**7- AWS System Manager sends the Amazon EC2 instance build instructions (addendum).**

**8- The Amazon EC2 instance downloads the source code from the Amazon S3 bucket.**

**9- The Amazon EC2 instance builds artifacts back to the Amazon S3 bucket.**

**10- The Amazon EC2 instance sends build status to AWS CodeBuild.**

**11- AWS CodePipeline sends an email via Amazon SNS to inform the developer that the build is complete and the EC2 instance IP to connect.**

**12- AWS CodePipeline begins the deployment process.**

**13- AWS CodeDeploy sends approved source code to bucket S3.**

With approved source code, developer can be sent back to the mainframe to perform the final recompilation through the connection with Micro Focus Changeman ZMF, for example. Another alternative is to use Micro Focus Enterprise Test Server for integration testing between programs before send back to mainframe.

**ADDENDUM:**

*COBOL COMPILATION INSTRUCTIONS:*

Following are the commands the developer can use to compile COBOL programs via command line using Micro Focus Enterprise Developer. All commands have been entered into the CodeBuild build script:
 
*For Windows:*

> cobol <nome-programa>.cbl,,, preprocess(EXCI) USE(diretivas_compilacao.dir);
 
The above command references the file named "diretivas_compilacao.dir". This file must have the necessary build directives for COBOL/CICS programs, for example, from the BANKDEMO server.

Below is the content of the directive_compilacao.dir file:

- NOOBJ
- DIALECT"ENTCOBOL"   ---  COPYEXT"cpy,cbl"   ---  SOURCETABSTOP"4"   ---  COLLECTION"BANKTEST"  ---  NOCOBOLDIR   ---  MAX-ERROR"100"   ---  LIST()  ---   NOPANVALET NOLIBRARIAN   ---  WARNING"1"   ---  EXITPROGRAM"GOBACK"    --- SOURCEFORMAT"fixed"   ---  CHARSET"EBCDIC"  ---   CICSECM()  ---   ANIM   ---  ERRFORMAT(2)   ---  NOQUERY  ---   NOERRQ    --- STDERR
 
If using Windows, the developer needs to run the cobol command in the directory where the source code is. The developer needs to copy to the same directory the copybooks used by these programs (.cpy extension files), or point to the directory containing the copybooks through the COBCPY environment variable.
 
The build script contains the environment variables required to run the BANKDEMO server:

*SET COBDIR=C:\Program Files (x86)\Micro Focus\Enterprise Developer\;%COBDIR%
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
SET COBCPY=c:\build\copybook*

For some non-COBOL/CICS programs, such as BANKDEMO's UDATECNV.CBL and SSSECUREP.CBL, simply run the commands without the “preprocess (EXCI)” directive. This directive is responsible for calling the CICS precompiler.

*COMMANDS FOR GENERATING DLL FILES:*

The developer must execute the command “cbllink” to produce a dynamic link library file of programs. Example:

               C:\>cbllink -d name_pgm.obj
 
The “-d” parameter indicates that a .DLL file is generated. The output from compilation “name_pgm.obj” will be used as input to the link.
 
After that, the developer needs to copy them to the destination directory (... \ loadlib) only the result of the link, ie, the name_pgm.DLL file

*COMMANDS TO START MICRO FOCUS SERVICES:*

After the files are compiled, you can start MicroFocus services and the BANKDEMO server on the EC2 instance to run the tests because Micro Focus Enterprise Developer already contains the Enterprise Server.

Micro Focus CES daemon and Directory Server services must be started:

**1- >net start mfcesd**

**2- >net start mf_CCITCP2**

**3- >net start "EA Integration Service Host"**

**4- >net start escwa**

**5- >net start "Micro Focus XDB Server for ETD 5.0"**

 
We enter the command lines to activate the server, for example BANKDEMO, in the build script. The command is basically: > casstart /r <name-of-server>. In the case of the BANKDEMO example, the command used is: 
 
 **> casstart /rBANKDEMO**

 
Following are links to documentation that gives more details on command lines (https://www.microfocus.com/documentation/enterprise-developer/ed50pu2/ED-Eclipse/HRCMRHCOML01.html).
      
Check that the BANKDEMO server is started in the browser (https://localhost:86)

Set up the directory structure with the “Transaction Path” and “Map Path” fields for CICS programs and the “JES Program path” field for Batch programs. In these fields, the developer needs to point to the directories where they copied the .DLLs files of programs.


## License

This library is licensed under the MIT-0 License. See the LICENSE file.

