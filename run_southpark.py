import subprocess
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Function that sends email using SendGrid
def send_email(subject, body, to_email):
    from_email = "alvcantu@icloud.com"  # SendGrid sender email
    sendgrid_api_key = "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"  # SendGrid API key

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body
    )

    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        print(f"Email sent successfully. Status code: {response.status_code}")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Function that runs commands
def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    stdout_decoded = stdout.decode()
    stderr_decoded = stderr.decode()
    if "Data quality issues found. Please resolve before proceeding." in stdout_decoded:
        error_message = f"Data quality issues found in southpark/etl/etl_southpark.py. Please resolve before proceeding."
        print(error_message)
        send_email(
            subject="South Park ETL Alert: Command Execution Failed",
            body=error_message,
            to_email="alvcantu@icloud.com"
        )
    if process.returncode != 0:
        error_message = f"Error executing command: {command}\nstderr: {stderr_decoded}"
        print(error_message)
        send_email(
            subject="South Park ETL Alert: Command Execution Failed",
            body=error_message,
            to_email="alvcantu@icloud.com"
        )
    else:
        print(f"Command executed successfully: {command}")

# Change directory to 'southpark'
os.chdir('/home/alvcantu/southpark')

# List of commands to execute sequentially
commands = [
    "scrapy crawl episode_details_spider -o /home/alvcantu/southpark/etl/raw_episode_details.csv",
    "scrapy crawl character_details_spider -L DEBUG",
    "python etl/etl_stg_southpark.py",
    "scrapy crawl episode_loop_spider -L DEBUG",
    "python etl/etl_southpark.py"
]

# Execute commands one by one
for command in commands:
    run_command(command)
