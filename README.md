Use AWS CI/CD services and Micro Focus solutions to make agile the mainframe development environment in Financial Institutions 

Mainframes are used by Financial Institutions for critical applications, batch data processing, online transaction processing, and mixed concurrent workloads. Mainframes have non-functional requirements such as performance, security, and resource availability to process all workloads. However, a potential resource deadlock may occur during the parallel development of new programs and subsequent testing. For example, two or more programs needing to access the same DB2 table or VSAM file simultaneously can generate a deadlock situation.
Thus, the idea of this blogpost is to present a solution to the resource availability issue in the COBOL development process, using Continuous Integration/ Continuous Deployment services (CI/CD) from AWS connected to an IDE such as Eclipse or Visual Studio. In the same pipeline of development, we use a plugin to connect Micro Focus solution called Enterprise Developer, for the step of compiling and running unit and functional tests.

SOLUTION OVERVIEW

The developer can use Git-compliant IDEs such as Eclipse or Visual Studio to make changes to COBOL code that are installed on desktops either locally using Amazon EC2 instances or the managed and secure Desktop as a Service (DaaS) solution named Amazon WorkSpaces. 

For example, download the Toolkit for Eclipse to connect to the AWS CodeCommit repository. Use your access key and the password of your AWS IAM registered user. Once installed and configured, the developer can clone a CodeCommit repository in Eclipse or create a CodeCommit repository from Eclipse (figure 3) via the AWS Explorer tab



## License

This library is licensed under the MIT-0 License. See the LICENSE file.

