import csv
import sys
import gzip
import shutil
import smtplib
import os
import getpass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# VARIABLES ----------------------------------------------
# For Email

SENDER = ''
RECIPIENT = ['']
SUBJECT = 'Scan Report'
BODY = 'Please see attached'
MAIL_SERVER = ''
MAIL_SMTP_P = 
MAIL_ISSL = False
def_pw = ''
# --------------------------------------------------------


def conv_and_send(password, s_file, file_gzip):
    # Convert text to csv
    print('Converting text to csv...')
    with open(s_file, 'r') as file_raw, gzip.open(file_gzip, 'wb') as csv_zip:
        file_read = csv.reader(file_raw, delimiter='\t')
        file_csv = csv.writer(csv_zip)
        for raw_row in file_read:
            file_csv.writerow(raw_row)

    # remove these two lines if you do not want to delete csv
    # print('Deleting csv...')
    # os.remove(sys.argv[2])

    # Email
    print('Sending csv to email...')
    msg = MIMEMultipart()
    msg['From'] = SENDER
    msg['To'] = ','.join(RECIPIENT)
    msg['Subject'] = SUBJECT
    msg.attach(MIMEText(BODY))

    # Attachment
    with open(file_gzip, 'r') as file_send:
        e_attachment = MIMEApplication(file_send.read(), 'x-gzip')
        e_attachment.add_header('Content-Disposition', 'attachment', filename=file_gzip)
    msg.attach(e_attachment)

    # send the email
    s_email = smtplib.SMTP(MAIL_SERVER, port=MAIL_SMTP_P)
    s_email.ehlo()
    # Enable this if TLS is required
    # s_email.starttls()
    s_email.login(SENDER, password)
    s_email.sendmail(SENDER, RECIPIENT, msg.as_string())
    s_email.quit()

def use_def_pass():
    return def_pw

if __name__ == '__main__':
    print('\nseek convert version 1.1')
    if len(sys.argv) < 3 and len(sys.argv) < 4:
        print('Syntax: seekconver.py <source.txt> <destination.csv> <auto>\n')
    else:
        in_file_gzip = sys.argv[2] + '.gz'
        if len(sys.argv) == 4 and sys.argv[3] == 'auto':
            # use default password
            in_password = def_pw
        else:
            # Get password
            in_password = getpass.getpass('E-mail Password: ')
        conv_and_send(in_password, sys.argv[1], in_file_gzip)