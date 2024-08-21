import subprocess
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Function that sends email using SendGrid
def send_email(subject, body, to_email):
    message = Mail(
        from_email='alvcantu@icloud.com',  # SendGrid sender email
        to_emails=to_email,
        subject=subject,
        plain_text_content=body)
    try:
        sg = SendGridAPIClient('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')  # SendGrid API key
        response = sg.send(message)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Function that runs commands
def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Command '{command}' executed successfully.")
        print(result.stdout.decode())
        return result.stdout.decode()
    except subprocess.CalledProcessError as e:
        error_message = f"Command '{command}' failed with error:\n{e.stderr.decode()}"
        print(error_message)
        send_email(
            subject="Stocks ETL Alert: Command Execution Failed",
            body=error_message,
            to_email="alvcantu@icloud.com"
        )
        return None

commands = [
    "scrapy runspider /home/alvcantu/stocks/stocks/spiders/company_list_spider.py",
    "python /home/alvcantu/stocks/etl/etl_ST_DimCompany.py",
    "python /home/alvcantu/stocks/etl/etl_ST_FactPrices.py"
]

# Run each command one by one
for command in commands:
    output = run_command(command)
    if output is None:
        break

# Only run forecasting if quality checks passed
if output and 'All quality checks passed.' in output:
    forecast_output = run_command("python /home/alvcantu/stocks/etl/etl_ST_FactPrices_Forecast.py")

    # Additional conditional to run PDF generation script if forecast records were updated
    if forecast_output and 'forecast records updated in ST_FactPrices' in forecast_output:
        pdf_output = run_command("python /home/alvcantu/stocks/etl/pdf_gen_stocks.py")
        if pdf_output:
            print("PDF generation completed successfully.")
        else:
            print("PDF's could not be generated.")
    else:
        print("Forecast records not updated. Skipping the PDF generation step.")
else:
    print("Quality checks did not pass. Skipping the forecast step.")

