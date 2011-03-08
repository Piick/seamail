Seamail
=======================

Builds, maintains, and manages a cluster of EC2 instances for sending bulk emails from Amazon's Simple Email Service. 

Dependencies
------------------

* `tornado`(1).
* `fabric`(1).
* `boto`(1).

Amazon Services
--------------------

Seamail relies heavily on Amazon's web services. You will need an Amazon AWS account with access to EC2, SQS, and SES.

Getting Started
-------------------

1. Setup an Amazon AWS account and get access to EC2, SQS, and SES. 
2. Use pip or easy_install to install the latest versions of Fabric and Boto.
3. Move the example fabric file to your home directory, rename it ~/.fabricrc, and populate it with your account information.

Fabric Command Reference
-------------------

start_nodes

	Starts a set of new nodes for sending emails. It also configures the systems, updates their templates, and starts the send daemon.

configure

	Updates the configuration, code, and templates on every node running in the cluster.

count_queue

	Returns a count of emails in the queue.

clear_queue

	Clears the email send queue.

send_message

	Add one email message to the queue.

ssh

	Show a list of nodes in the cluster and provide a menu for choosing a node to ssh into.

stats

	Show all email sends stats that Amazon provides as well as a list of verified email addresses.

terminate_cluster

	Terminate all nodes in the cluster.

unverify_email

	Remove an email from the verified list.

verify_email

	Add an email to the verified list. It won't be fully verified until the link in the verification email is clicked.
