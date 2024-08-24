from flask import Flask, request, render_template, url_for
from youtube_transcript_api import YouTubeTranscriptApi
import re
import requests
import json
import mysql.connector
import pandas as pd
import os
from graphviz import Digraph
import sqlparse
from datetime import datetime

# Define exceptions for column classifications
classification_exceptions = {
    'SP': {
        'season': 'dimension'
    },
    # Add more data marts and their exceptions here
}

# Function to classify columns based on their data types with exceptions inccluded
def get_column_classification(data_mart, column_name, data_type):
    # Check if there's an exception for this column in the given data mart
    if data_mart in classification_exceptions and column_name in classification_exceptions[data_mart]:
        return classification_exceptions[data_mart][column_name]
    
    # Default classification logic
    if any(data_type.startswith(t) for t in ('varchar', 'char', 'text', 'date')):
        return "dimension"
    elif any(data_type.startswith(t) for t in ('int', 'float')):
        return "measure"
    else:
        return "other"

selected_datamart = 'SP'
column_name = 'character_id'
data_type = 'int'

print(get_column_classification(selected_datamart, column_name, data_type))