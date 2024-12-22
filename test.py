import pandas_market_calendars as mcal

# Get all available calendars
calendars = mcal.get_calendar_names()

# Print the list of calendar names
print(calendars)