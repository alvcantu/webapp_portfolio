import os
import mysql.connector
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from matplotlib import font_manager as fm
from datetime import datetime
import requests
import json
import re
from reportlab.lib.fonts import addMapping
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import letter, landscape, portrait
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Frame, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

# SendGrid API Keys and emails
SENDGRID_API_KEY = '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'
SENDER_EMAIL = 'alvcantu@icloud.com'
RECIPIENT_EMAIL = 'alvcantu@icloud.com'

# Open Router API key used to connect to different LLM's
OPENROUTER_API_KEY = "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"

# Register Roboto fonts
pdfmetrics.registerFont(TTFont('Roboto', '/home/alvcantu/mysite/static/Roboto-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Roboto-Bold', '/home/alvcantu/mysite/static/Roboto-Bold.ttf'))
# Create custom font styles using Roboto
styles = getSampleStyleSheet()
styles['Normal'].fontName = 'Roboto'
styles['Normal'].fontSize = 8
styles['Heading1'].fontName = 'Roboto-Bold'
styles['Heading1'].fontSize = 18
styles['Heading3'].fontName = 'Roboto-Bold'
styles['Heading3'].fontSize = 9
right_style = ParagraphStyle('RightStyle',
                             parent=styles['Normal'],
                             alignment=TA_RIGHT,
                             fontName='Roboto',
                             fontSize=12)

# Company colors
# Codes
apple_green_code='#4CAF50'
dark_green_code = '#49714b'
red_code = '#9e3637'
# Use for pdf
apple_green = colors.HexColor(apple_green_code)
dark_green = colors.HexColor(dark_green_code)
red = colors.HexColor(red_code)

# Calculate the 16:9 page size
page_width, page_height = portrait(landscape(letter))
doc_width = page_width
doc_height = page_width * 9 / 16

# Connect to MySQL database
def get_db_connection():
    mydb = mysql.connector.connect(
        host="alvcantu.mysql.pythonanywhere-services.com",
        user="alvcantu",
        password="h63Efp09-d",
        database="alvcantu$default"
    )
    cursor = mydb.cursor()
    return mydb, cursor

# Function to get first slide subtitle
def generate_presentation_subtitle():
    today = datetime.now()
    today_date = today.strftime("%A %d %B %Y")

    return f"{today_date}"

# Function to clean generated text into clean bullets.
def fancy_bullet_points(text):
    # Replace various bullet point symbols with a circle bullet point
    bullet_symbols = r'[-•●○*]'
    text = re.sub(bullet_symbols, '• ', text)

    # Add new lines before each bullet point
    text = re.sub(r'(?<!^)\n', '\n\n', text)

    # Ensure there's no leading newline
    return text.lstrip('\n')

# Function to create stock graphs, saves them to presentation_graphs folder
def create_stock_graphs():
    # Get the database connection and cursor
    conn, cursor = get_db_connection()

    try:
        # Fetch company names from the database
        cursor.execute("SELECT name FROM ST_DimCompany")
        company_names = [row[0] for row in cursor.fetchall()]

        for company_name in company_names:
            # Create a new cursor for each iteration
            _, cursor = get_db_connection()

            try:
                # Extract data for last 3 weeks
                cursor.execute(f'''
                SELECT
                    sp.date,
                    COALESCE(sp.forecast_price_arima, sp.close_price) AS price,
                    CASE
                        WHEN sp.forecast_price_arima IS NOT NULL AND sp.date > CURDATE() THEN 'Forecast'
                        ELSE 'Actual'
                    END AS price_type
                FROM
                    ST_FactPrices sp
                JOIN
                    ST_DimCompany sc ON sp.ticker = sc.ticker
                WHERE
                    sc.name = %s
                    AND sp.date >= CURDATE() - INTERVAL 3 WEEK
                ORDER BY
                    sp.date;
                ''', (company_name,))
                three_week_data = cursor.fetchall()

                # Generate graphs png's
                # Load the Roboto fonts
                regular_font = fm.FontProperties(fname='/home/alvcantu/mysite/static/Roboto-Regular.ttf')
                bold_font = fm.FontProperties(fname='/home/alvcantu/mysite/static/Roboto-Bold.ttf')

                # Assuming three_week_data is a list of tuples with (date, ticker, price, price_type)
                dates = [row[0] for row in three_week_data]
                prices = [row[1] for row in three_week_data]
                price_types = [row[2] for row in three_week_data]

                # Create the plot with smaller dimensions
                fig, ax = plt.subplots(figsize=(12, 6))

                # Plot actual prices
                actual_mask = [pt == 'Actual' for pt in price_types]
                ax.plot(
                    [d for d, m in zip(dates, actual_mask) if m],
                    [p for p, m in zip(prices, actual_mask) if m],
                    label='Actual', color=dark_green_code
                )

                # Plot forecast prices
                forecast_mask = [pt == 'Forecast' for pt in price_types]
                ax.plot(
                    [d for d, m in zip(dates, forecast_mask) if m],
                    [p for p, m in zip(prices, forecast_mask) if m],
                    label='Forecast', color=red_code, linestyle='--'
                )

                # Customize the plot
                ax.set_xlabel('Date', fontproperties=regular_font)
                ax.set_ylabel('Price', fontproperties=regular_font)
                ax.legend(prop=bold_font)

                # Format x-axis to show dates without rotation
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
                plt.xticks(rotation=0, fontproperties=regular_font)  # No rotation of date labels

                # Add grid for better readability
                ax.grid(True, linestyle='--', alpha=0.7)

                # Removing the plot borders (spines)
                plt.gca().spines['top'].set_visible(False)
                plt.gca().spines['right'].set_visible(False)
                plt.gca().spines['left'].set_visible(False)
                plt.gca().spines['bottom'].set_visible(False)

                # Create the directory if it doesn't exist
                save_dir = "/home/alvcantu/mysite/static/presentation_graphs"
                os.makedirs(save_dir, exist_ok=True)

                # Save the plot as PNG
                filename = f"stock_graph_{company_name}.png"
                filepath = os.path.join(save_dir, filename)
                plt.savefig(filepath, dpi=300, bbox_inches='tight')

                # Close the plot to free up memory
                plt.close(fig)

            finally:
                # Close the cursor after each iteration
                cursor.close()

    finally:
        # Close the connection after all iterations
        conn.close()

# Function to create metrics and graphs for south park slide
def create_south_park_elements():
    # Get the database connection and cursor
    conn, cursor = get_db_connection()

    # Gather randomized character_id
    cursor.execute('''
    SELECT DISTINCT c.character_id
    FROM SP_DimCharacters c
    JOIN SP_FactEpisodesCharacters ec ON c.character_id = ec.character_id
    ORDER BY
        RAND()
    LIMIT 1;''')
    random_character_id = cursor.fetchone()[0]

    # Gather data for appearances per season
    cursor.execute(f'''
    SELECT
        e.season AS season,
        COUNT(fec.episode_id) AS appearances
    FROM SP_DimCharacters dc
    JOIN SP_FactEpisodesCharacters fec ON dc.character_id = fec.character_id
    JOIN SP_DimEpisodes e ON fec.episode_id = e.episode_id
    WHERE dc.character_id = %s
    GROUP BY e.season
    ORDER BY e.season;
    ''', (random_character_id,))
    appearances_per_season = cursor.fetchall()

    # Gather character_name and role
    cursor.execute(f'''
    SELECT character_name, role FROM SP_DimCharacters
    WHERE character_id = %s;
    ''',(random_character_id,))
    character_info = cursor.fetchall()

    # Creating the graph and saving it in static folder
    # Load the Roboto fonts
    regular_font = fm.FontProperties(fname='/home/alvcantu/mysite/static/Roboto-Regular.ttf')
    bold_font = fm.FontProperties(fname='/home/alvcantu/mysite/static/Roboto-Bold.ttf')

    # Extract data for plotting
    seasons = [row[0] for row in appearances_per_season]
    appearances = [row[1] for row in appearances_per_season]

    # Plotting the vertical bar graph
    plt.figure(figsize=(10, 6))
    bars = plt.bar(seasons, appearances, color=red_code)

    # Adding appearance counts above each bar
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2.0, height, str(int(height)),
                ha='center', va='bottom', fontproperties=regular_font)

    # Removing the plot borders (spines)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['left'].set_visible(False)
    plt.gca().spines['bottom'].set_visible(False)

    # Customizing x-axis to show all seasons
    plt.gca().set_xticks(seasons)
    plt.gca().set_xticklabels(seasons, fontproperties=regular_font, ha='right')

    # Removing y-axis ticks and labels
    plt.gca().tick_params(axis='y', left=False, labelleft=False)

    # Adding title and labels with the specified fonts
    character_name = character_info[0][0]
    plt.title(f'Appearances of {character_name} per Season', fontproperties=bold_font)
    plt.xlabel('Season', fontproperties=regular_font)

    # Define the save path
    save_directory = '/home/alvcantu/mysite/static/presentation_graphs'
    os.makedirs(save_directory, exist_ok=True)
    save_path = os.path.join(save_directory, f'southpark_appearances_per_season.png')

    # Save the plot
    plt.savefig(save_path)

    # LLM writes summary of south park character
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        },
        data=json.dumps({
        "model": "meta-llama/llama-3.1-8b-instruct:free", # Use free LLM to reduce costs
        "messages": [
            {"role": "system", "content": "Write 4 short bullet points about the attached South Park character information. Only include the bullet points."},
            {"role": "user", "content": f"{character_info}"}
        ]
        })
    )
    # Parsing response to json
    response_data = response.json()
    # Extracting actual response from json
    llm_response = response_data.get('choices', [{}])[0].get('message', {}).get('content', 'No content found')

    return character_name, llm_response

# Function to create master canvas
def master_canvas(canvas, doc, title, subtitle, text, image_path, is_intro_slide):
    # Set title
    heading_style = styles["Heading1"]
    title_paragraph = Paragraph(title, heading_style)

    # Set subtitle
    subheading_style = styles["Heading3"]
    subtitle_paragraph = Paragraph(subtitle, subheading_style)

    # Calculate title and subtitle dimensions
    title_width, title_height = title_paragraph.wrap(doc_width - 2*inch, doc_height)
    subtitle_width, subtitle_height = subtitle_paragraph.wrap(doc_width - 2*inch, doc_height)

    # Position title and subtitle
    title_x = 1 * inch
    subtitle_x = 1 * inch
    title_y = doc_height - 0.8 * inch # Adjust space between top of presentation and title

    # Adjust this value to change the space between title and subtitle
    title_subtitle_gap = 0.05 * inch

    subtitle_y = title_y - title_height - title_subtitle_gap

    # Draw title and subtitle
    title_paragraph.drawOn(canvas, title_x, title_y)
    subtitle_paragraph.drawOn(canvas, subtitle_x, subtitle_y)

    # Footer and line calculations
    footer_height = 1 * inch
    footer_width = doc_width * 0.85
    line_start_x = (doc_width - footer_width) / 2
    line_end_x = line_start_x + footer_width

    # Image positioning
    image_width = doc_width / 2
    image_height = doc_height / 2
    if is_intro_slide:
        image_x = (doc_width - image_width) / 2  # Center the image horizontally
    else:
        image_x = line_end_x - image_width

    # Ensure image is below subtitle and above footer line
    image_top_y = subtitle_y - subtitle_height - 0.05 * inch  # 0.05 inch gap below subtitle
    image_bottom_y = footer_height + 0.25 * inch  # 0.25 inch above footer line
    available_height = image_top_y - image_bottom_y

    if available_height >= image_height:
        image_y = image_bottom_y
    else:
        # If not enough space, reduce image height to fit
        image_height = available_height
        image_y = image_bottom_y

    canvas.drawImage(image_path, image_x, image_y, width=image_width, height=image_height, preserveAspectRatio=True)

    # Set normal text
    normal_style = styles['Normal']
    formatted_text = fancy_bullet_points(text)
    lines = formatted_text.split('\n')  # Split into lines

    # Positioning variables
    text_padding = 0.25 * inch
    text_width = image_x - 1 * inch - text_padding
    text_x = 1 * inch
    text_y = image_top_y # Aligns text with image
    text_height = text_y - footer_height - 0.25 * inch

    # Draw each line as a separate paragraph
    for line in lines:
        if line.strip():  # Skip empty lines
            normal_paragraph = Paragraph(line, normal_style)
            w, h = normal_paragraph.wrap(text_width, text_height)
            normal_paragraph.drawOn(canvas, text_x, max(text_y - h, footer_height + 0.25 * inch))
            text_y -= h  # Move the y-position down by the height of the paragraph

    # Ensure we don't go below the footer
    text_y = max(text_y, footer_height + 0.25 * inch)

    # Footer line
    line_y = footer_height - 0.25 * inch
    canvas.saveState()
    canvas.setStrokeColor(apple_green)
    canvas.setLineWidth(2)
    canvas.line(line_start_x, line_y, line_end_x, line_y)

    # Logo (only for non-intro slides)
    if not is_intro_slide:
        logo_width = 0.5 * inch
        logo_height = 0.5 * inch
        logo_padding = 0.1 * inch
        logo_x = line_end_x - logo_width - logo_padding
        logo_y = logo_padding

        # Draw logo
        canvas.drawImage('/home/alvcantu/mysite/static/apple-touch-icon.png', logo_x, logo_y, width=logo_width, height=logo_height)

    # Finalize the page
    canvas.showPage()

# Function to generate slides
def create_slides():
    # Get the database connection and cursor
    conn, cursor = get_db_connection()

    # Fetch company names from the database
    cursor.execute("SELECT name FROM ST_DimCompany")
    company_names = [row[0] for row in cursor.fetchall()]

    # Create a new PDF document
    pdf_path = "/home/alvcantu/mysite/static/presentation.pdf"
    c = canvas.Canvas(pdf_path, pagesize=(doc_width, doc_height))

    # Adding first slide to canvas
    master_canvas(c, c, "Daily Auto-generated Presentation" ,generate_presentation_subtitle(),' ', '/home/alvcantu/mysite/static/apple-touch-icon.png', is_intro_slide=True)

    # Adding south park character slide
    character_name, character_text = create_south_park_elements()
    master_canvas(c,c, "South Park Character of the Day", character_name, character_text,'/home/alvcantu/mysite/static/presentation_graphs/southpark_appearances_per_season.png', is_intro_slide=False)

    # Loop to add one slide per company
    for company_name in company_names:
        # Define the image path
        image_path = f"/home/alvcantu/mysite/static/presentation_graphs/stock_graph_{company_name}.png"

        # Use LLM to write a summary of last 3 weeks of data and forecast
        # Extract data for last 3 weeks
        cursor.execute(f'''
        SELECT
            sc.name,
            sc.ticker,
            sp.date,
            COALESCE(sp.forecast_price_arima, sp.close_price) AS price,
            CASE
                WHEN sp.forecast_price_arima IS NOT NULL AND sp.date > CURDATE() THEN 'Forecast'
                ELSE 'Actual'
            END AS price_type
        FROM
            ST_FactPrices sp
        JOIN
            ST_DimCompany sc ON sp.ticker = sc.ticker
        WHERE
            sc.name = %s
            AND sp.date >= CURDATE() - INTERVAL 3 WEEK
        ORDER BY
            sp.date;
        ''', (company_name,))
        three_week_data = cursor.fetchall()

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}"
            },
            data=json.dumps({
            "model": "meta-llama/llama-3.1-8b-instruct:free", # Use free LLM to reduce costs
            "messages": [
                {"role": "system", "content": "Summarize the following company stock data in 3 short one line bullet points; one describing the latest actual price change, one describing overall trend, last one describing forecasted data. Only include the bullet points."},
                {"role": "user", "content": f"{three_week_data}"}
            ]
            })
        )
        # Parsing response to json
        response_data = response.json()
        # Extracting actual response from json
        text = response_data.get('choices', [{}])[0].get('message', {}).get('content', 'No content found')


        # Apply the master canvas
        master_canvas(c, c, company_name,'Last 3 weeks of data', text, image_path, is_intro_slide=False)

    # Save the pdf
    c.save()

    # Close the database connection
    conn.close()

# Send error messages function
def send_error_email(error_message):
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    from_email = Email(SENDER_EMAIL)
    to_email = To(RECIPIENT_EMAIL)
    subject = "Script Execution Error"
    content = Content("text/plain", f"An error occurred:\n{error_message}")
    mail = Mail(from_email, to_email, subject, content)
    
    try:
        response = sg.client.mail.send.post(request_body=mail.get())
        print(f"Email sent, status code: {response.status_code}")
    except Exception as e:
        print(f"Failed to send email: {e}")


# Execute the main logic with try-except blocks to handle exceptions and send error emails
# EMAILS DO NOT SEND IF MODULE FAILS TO LOAD, ONLY IF FUNCTION FAILS
try:
    # Call the function to create the graphs in png format to be later inserted into slides
    create_stock_graphs()
except Exception as e:
    error_message = f"Failed to create stock graphs: {str(e)}"
    send_error_email(error_message)
    raise  # Re-raise the exception if you want the script to stop here

try:
    # Call the function to create the weekly presentation
    create_slides()
except Exception as e:
    error_message = f"Failed to create slides: {str(e)}"
    send_error_email(error_message)
    raise  # Re-raise the exception if you want the script to stop here

print("All operations completed successfully.")