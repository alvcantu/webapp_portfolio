import mysql.connector
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Frame, PageTemplate, SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# Register Roboto fonts
pdfmetrics.registerFont(TTFont('Roboto', '/home/alvcantu/mysite/static/Roboto-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Roboto-Bold', '/home/alvcantu/mysite/static/Roboto-Bold.ttf'))

# Connect to MySQL database
mydb = mysql.connector.connect(
    host="alvcantu.mysql.pythonanywhere-services.com",
    user="alvcantu",
    password="h63Efp09-d",
    database="alvcantu$default"
)
cursor = mydb.cursor()

# Function to format price based on currency
def format_price(price, currency):
    if currency == 'USD':
        return f'${price:.2f}'
    elif currency == 'EUR':
        return f'€{price:.2f}'
    # Add more currency formats as needed
    else:
        return f'{price:.2f} {currency}'

# Directory to save PDFs
pdf_directory = "/home/alvcantu/mysite/static"

# Create custom styles using Roboto
styles = getSampleStyleSheet()
styles['Normal'].fontName = 'Roboto'
styles['Heading1'].fontName = 'Roboto-Bold'
styles['Heading3'].fontName = 'Roboto-Bold'

right_style = ParagraphStyle('RightStyle', parent=styles['Normal'], alignment=TA_RIGHT, fontName='Roboto')

# Create a custom color for the lines
line_color = colors.HexColor('#4CAF50')

# Fetch all company info
cursor.execute("""
    SELECT name, ticker, country, website, industry, currency, summary
    FROM ST_DimCompany
""")
company_info_list = cursor.fetchall()

for company_info in company_info_list:
    company_name, ticker = company_info[0], company_info[1]

    # Fetch price data for this company
    cursor.execute("""
        SELECT
            date,
            close_price,
            forecast_price_arima
        FROM
            ST_FactPrices
        WHERE
            ticker = %s
            AND (
                date = CURRENT_DATE()
                OR date = DATE_ADD(CURRENT_DATE(), INTERVAL -2 DAY)
                OR date = DATE_ADD(CURRENT_DATE(), INTERVAL -1 DAY)
                OR date = DATE_ADD(CURRENT_DATE(), INTERVAL 1 DAY)
                OR date = DATE_ADD(CURRENT_DATE(), INTERVAL 2 DAY)
                OR date = DATE_ADD(CURRENT_DATE(), INTERVAL 3 DAY)
                OR date = DATE_ADD(CURRENT_DATE(), INTERVAL 4 DAY)
                OR date = DATE_ADD(CURRENT_DATE(), INTERVAL 5 DAY)
            )
        ORDER BY
            date;
    """, (ticker,))
    price_data = cursor.fetchall()

    # Function to add logo to the topr right of page
    def add_logo(canvas, doc):
        logo_path = "/home/alvcantu/mysite/static/apple-touch-icon.png"
        if os.path.exists(logo_path):
            # Adjust logo placement
            canvas.drawImage(logo_path, doc.width + doc.rightMargin - 1.2*inch, doc.height + doc.topMargin - 1.2*inch, width=1*inch, height=1*inch)

    # Create PDF with names that atch each company
    pdf_filename = os.path.join(pdf_directory, f"stock_report_{company_name.replace(' ', '_')}.pdf")
    # Reduce top margin
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4, topMargin=0.5*inch, rightMargin=0.5*inch, leftMargin=0.5*inch, bottomMargin=0.5*inch)

    # Create a custom PageTemplate
    # Adjust frame to use full page height
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    template = PageTemplate(id='test', frames=frame, onPage=add_logo)
    doc.addPageTemplates([template])

    story = []

    # Add company name as title
    story.append(Paragraph(company_name, styles['Heading1']))
    story.append(Spacer(1, 0.1*inch))

    # Add company info on separate lines
    info_items = [
        f"Ticker: {ticker}",
        f"Country: {company_info[2]}",
        f"Website: {company_info[3]}",
        f"Industry: {company_info[4]}",
        f"Currency: {company_info[5]}"
    ]
    for item in info_items:
        story.append(Paragraph(item, styles['Normal']))
        story.append(Spacer(1, 0.05*inch))

    # Add a green line
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph('<para spaceBefore="0" spaceAfter="0"><font color="#4CAF50">_______________________________</font></para>', styles['Normal']))
    story.append(Spacer(1, 0.1*inch))

    # Add summary
    story.append(Paragraph("Summary:", styles['Heading3']))
    story.append(Paragraph(company_info[6], styles['Normal']))

    # Add another green line
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph('<para spaceBefore="0" spaceAfter="0"><font color="#4CAF50">_______________________________</font></para>', styles['Normal']))
    story.append(Spacer(1, 0.1*inch))

    # Add price data
    if price_data:
        story.append(Paragraph("Price Data:", styles['Heading3']))
        data = [['Date', 'Close Price', 'Forecast Price']]
        for row in price_data:
            formatted_close = format_price(row[1], company_info[5]) if row[1] else 'N/A'
            formatted_forecast = format_price(row[2], company_info[5]) if row[2] else 'N/A'
            data.append([row[0].strftime('%Y-%m-%d'), formatted_close, formatted_forecast])

        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), line_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Roboto'),
            ('FONTNAME', (0, 0), (-1, 0), 'Roboto-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, line_color)
        ]))
        story.append(table)

    # Build PDF
    doc.build(story)

    pdf_filename = f"stock_report_{company_name.replace(' ', '_')}.pdf"
    full_path = os.path.join(pdf_directory, pdf_filename)

    print(f"PDF generated for {company_name}: {pdf_filename}")

# Close database connection
cursor.close()
mydb.close()