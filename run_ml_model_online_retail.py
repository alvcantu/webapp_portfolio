import subprocess
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def run_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise Exception(f"Command failed with error: {stderr.decode('utf-8')}")
    return stdout.decode('utf-8')

def send_email(subject, body, to_email):
    from_email = "alvcantu@icloud.com"  # Replace with your email
    sendgrid_api_key = "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"  # Replace with your SendGrid API key

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

def main():
    to_email = "alvcantu@icloud.com"  # Replace with the email where you want to receive notifications
    try:
        # Run the first script
        print("Starting create_mlmodel script...")
        run_command('python online_retail/create_mlmodel_online_retail.py')
        print("create_mlmodel script completed.")

        # Wait for 30 seconds
        print("Waiting for 30 seconds before starting the next script...")
        time.sleep(30)

        # If the first script succeeds, run the second script
        print("Starting etl_mlmodel script...")
        run_command('python online_retail/etl_mlmodel_online_retail.py')
        print("etl_mlmodel script completed.")

        # Send success email
        send_email("Scripts Execution Completed", "Both scripts have run successfully.", to_email)
    except Exception as e:
        # Send failure email
        error_message = f"An error occurred: {str(e)}"
        send_email("Script Execution Failed", error_message, to_email)
        print(error_message)
        sys.exit(1)  # Exit with a non-zero status to indicate failure

if __name__ == "__main__":
    main()