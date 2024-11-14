import streamlit as st
import plotly.express as px
import pandas as pd
import function as fn
import openai
import logging
import re
import base64

# Logging setup
logging.basicConfig(filename="log.log", level=logging.INFO, format="%(asctime)s - %(message)s")
# OpenAI API setup for multiple models
openai.api_type = "azure"
openai.api_base = "https://genai-openai-analytics0.openai.azure.com/"  
openai.api_version = "2024-05-01-preview"  
openai.api_key="51c83a65a56a47d4ab3f4a67463bd949"



def get_movement_commentary(selected_account, avg_data):
    account_filtered_data = avg_data[avg_data['Sap Account'] == selected_account]
    # Generate a prompt for OpenAI to provide commentary
    prompt = f""" This is the data for the SAP account '{selected_account}' for the years 2023 and 2024:
                {account_filtered_data.to_string(index=False)}
    Analyze the data and provide a one-line commentary on why there was a movement in the balance amount due to changes in the principal amount, floating rate, and interest rate for the SAP account '{selected_account}' from 2023 to 2024.

    Explain potential reasons for the observed changes in floating rate and interest rate.
    Additionally, include the percentage change for balance, principal amount, floating rate, and interest rate.
    """

    logging.info("Executing the following prompt:\n%s", prompt)

    try:
        response = openai.ChatCompletion.create(
            engine="gpt-35-turbo",
            messages=[
                {"role": "system", "content": "You are a financial data analyst who provides detailed commentaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800
        )
        commentary = response['choices'][0]['message']['content']
        logging.info("Commentary response: %s", commentary)
        return commentary
    except Exception as e:
        logging.error("An error occurred while generating commentary: %s", e)
        return "An Error has occurred" 
    

df_2023 = fn.create_2023_dataset()
df_2024 = fn.create_2024_dataset()
df_main = pd.concat([df_2023, df_2024], ignore_index=True)
df_summary = df_main.pivot_table(
            values='Balance Amount',
            index=['Sap Account', 'Cob Date'],
            aggfunc='mean'
        ).reset_index()

df_detailed = df_main.pivot_table(
            values=['Floating Rate', 'Interest Rate', 'Balance Amount', 'Principal Amount'],
            index=['Cob Date', 'Sap Account', 'Trade Date', 'Maturity Date'],
            aggfunc='first'
        ).reset_index()

def create_prompt_with_code_request(df_summary, df_detailed):
    df_summary_str = df_summary.head(10).to_string(index=False)
    df_detailed_str = df_detailed.head(10).to_string(index=False)
    prompt = f"""
    I have financial data for multiple SAP accounts for the years 2023 and 2024. The data includes two datasets:
    1. The first dataset (df_summary) contains daily records of balance for each SAP account with a COB Date and Balance Amount. Here is a sample: {df_summary_str}
    2. The second dataset (df_detailed) includes detailed records for each SAP account, with columns for COB Date, Trade Date, Maturity Date, Balance Amount, Floating Rate, Interest Rate, and Principal Amount. Here is a sample: {df_detailed_str}

    Please provide Python code that completes the following tasks and stores the results in the specified variable names, Note that the data is already loaded in the dataframes 'df_summary' and 'df_detailed' for your use, don't reload the data.::

    1. In `df_summary`, calculate the top 3 SAP accounts with the largest total increase in balance for September and store the result as a list in the variable `top3_increase`. Similarly, calculate the top 3 SAP accounts with the largest decrease in balance and store the result in the variable `top3_decrease`.

    2. Using `df_detailed`, calculate the average balance, principal amount, floating rate, and interest rate for each SAP account for September in both years 2023 and 2024. Ensure that date columns (e.g., COB Date) are converted to datetime format before processing, and verify that numeric columns are in the correct format to avoid errors. 

    3. Calculate the year-over-year (YoY) change from 2023 to 2024 for each SAP account in the columns for average balance, principal amount, floating rate, and interest rate, using the results from step 2. Store these YoY changes in a single DataFrame called `avg_data`, which should have only five columns: `SAP Account`, `Balance_chg`, `Principal_chg`, `FloatingRate_chg`, and `Interest_chg`.

    4. Identify and store the top 3 SAP accounts with the largest YoY increase in floating rate in a list named `top3_floating_increase`, and the top 3 with the largest YoY decrease in floating rate in a list named `top3_floating_decrease`. Similarly, store the top 3 SAP accounts with the largest YoY increase in interest rate in a list named `top3_int_increase` and the top 3 with the largest YoY decrease in interest rate in a list named `top3_int_decrease`.

    Ensure that only the columns specified are included in `avg_data`, with one row per SAP account, and that the YoY calculations are performed correctly. Respond with the code only, without any additional formatting or code block delimiters, so it can be run directly.
    """
    return prompt

def execute_prompt(prompt, df_summary, df_detailed, model="gpt-35-turbo"):
    try:
                
        # Request code from OpenAI
        response = openai.ChatCompletion.create(
            engine=model,
            messages=[
                {"role": "system", "content": "You are a data analyst who provides Python code."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800
        )
        
        # Extract Python code from response
        code = response['choices'][0]['message']['content']
        #st.subheader("Generated Python Code")
        #st.code(code, language='python')
        
        # Clean up the code using regex to remove markdown formatting and unexpected characters
        code_match = re.search(r"```(.*?)```", code, re.DOTALL)
        code_python = re.sub(r"```python(.*?)```", "", code, flags=re.DOTALL)
        if code_match:
            code_to_execute = code_match.group(1).strip()
        elif code_python:
            code_to_execute = code_python.group(1).strip()
        else:
            code_to_execute = code.strip()
        
        # Log the code execution
        logging.info("Executing the following code:\n%s", code_to_execute)

        # Execute the sanitized Python code and capture the output
        local_vars = {"df_summary": df_summary, "df_detailed": df_detailed}
        exec(code_to_execute, globals(), local_vars)
        
        # Display results
        result_vars = [
            'top3_increase', 'top3_decrease', 'avg_data', 
            'top3_floating_increase', 'top3_floating_decrease', 
            'top3_int_increase', 'top3_int_decrease'
        ]
        
        for var in result_vars:
            if var in local_vars:
                #st.subheader(f"{var.replace('_', ' ').title()}")
                #st.write(local_vars[var])
                logging.info("Print:", code_to_execute)
            # Button for commentary on balance movement

        return local_vars
    except Exception as e:
        logging.error("An error occurred during code execution: %s", e)
        st.error(f"An error occurred: {e}")

prompt = create_prompt_with_code_request(df_summary, df_detailed)
top3_increase, top3_decrease, avg_data, top3_floating_increase, top3_floating_decrease, top3_int_increase, top3_int_decrease = fn.prompt_response_run(df_summary, df_detailed)

# Configure the Streamlit page
st.set_page_config(
    page_title="MITR AI Analysis",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

AI_ICON = '''
<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <style>
        @keyframes pulse {
            0% { opacity: 0.4; }
            50% { opacity: 1; }
            100% { opacity: 0.4; }
        }
        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        @keyframes dash {
            to {
                stroke-dashoffset: 0;
            }
        }
        .brain-path {
            fill: none;
            stroke: #4a90e2;
            stroke-width: 2;
            stroke-dasharray: 1000;
            stroke-dashoffset: 1000;
            animation: dash 3s ease-in-out infinite alternate;
        }
        .circle {
            animation: pulse 2s infinite;
        }
        .rotating-circles {
            animation: rotate 10s linear infinite;
        }
        .node {
            fill: #4a90e2;
            animation: pulse 2s infinite;
        }
    </style>
    
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#2193b0;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#6dd5ed;stop-opacity:1" />
        </linearGradient>
    </defs>
    <circle cx="100" cy="100" r="90" fill="none" stroke="url(#grad1)" stroke-width="4"/>
    
    <g class="rotating-circles" transform="translate(100,100)">
        <circle class="circle" cx="0" cy="-60" r="10" fill="#4a90e2" opacity="0.7"/>
        <circle class="circle" cx="52" cy="-30" r="10" fill="#4a90e2" opacity="0.7"/>
        <circle class="circle" cx="52" cy="30" r="10" fill="#4a90e2" opacity="0.7"/>
        <circle class="circle" cx="0" cy="60" r="10" fill="#4a90e2" opacity="0.7"/>
        <circle class="circle" cx="-52" cy="30" r="10" fill="#4a90e2" opacity="0.7"/>
        <circle class="circle" cx="-52" cy="-30" r="10" fill="#4a90e2" opacity="0.7"/>
    </g>
    
    <path class="brain-path" d="M70,100 C80,80 120,80 130,100 S170,120 160,140 S120,160 100,150 S60,140 70,100"/>
    <path class="brain-path" d="M60,90 C70,70 130,70 140,90 S180,110 170,130 S130,150 110,140 S50,130 60,90"/>
    
    <circle cx="100" cy="100" r="20" fill="url(#grad1)"/>
    <text x="100" y="105" text-anchor="middle" fill="white" font-family="Arial" font-weight="bold" font-size="50">MITR</text>
    
    <g stroke="#4a90e2" stroke-width="1" opacity="0.5">
        <line x1="100" y1="80" x2="100" y2="40"/>
        <line x1="100" y1="120" x2="100" y2="160"/>
        <line x1="80" y1="100" x2="40" y2="100"/>
        <line x1="120" y1="100" x2="160" y2="100"/>
    </g>
</svg>
'''

# Convert SVG to base64 for embedding
AI_ICON_B64 = base64.b64encode(AI_ICON.encode()).decode()

AI_ICON_TITLE = '''
<svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <style>
        @keyframes pulse {
            0% { opacity: 0.4; }
            50% { opacity: 1; }
            100% { opacity: 0.4; }
        }
        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        @keyframes dash {
            to {
                stroke-dashoffset: 0;
            }
        }
        .brain-path {
            fill: none;
            stroke: #4a90e2;
            stroke-width: 2;
            stroke-dasharray: 1000;
            stroke-dashoffset: 1000;
            animation: dash 3s ease-in-out infinite alternate;
        }
        .circle {
            animation: pulse 2s infinite;
        }
        .rotating-circles {
            animation: rotate 10s linear infinite;
        }
        .node {
            fill: #4a90e2;
            animation: pulse 2s infinite;
        }
    </style>
    
    <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#2193b0;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#6dd5ed;stop-opacity:1" />
        </linearGradient>
    </defs>
    <circle cx="100" cy="100" r="90" fill="none" stroke="url(#grad1)" stroke-width="4"/>
    
    <g class="rotating-circles" transform="translate(100,100)">
        <circle class="circle" cx="0" cy="-60" r="10" fill="#4a90e2" opacity="0.7"/>
        <circle class="circle" cx="52" cy="-30" r="10" fill="#4a90e2" opacity="0.7"/>
        <circle class="circle" cx="52" cy="30" r="10" fill="#4a90e2" opacity="0.7"/>
        <circle class="circle" cx="0" cy="60" r="10" fill="#4a90e2" opacity="0.7"/>
        <circle class="circle" cx="-52" cy="30" r="10" fill="#4a90e2" opacity="0.7"/>
        <circle class="circle" cx="-52" cy="-30" r="10" fill="#4a90e2" opacity="0.7"/>
    </g>
    
    <path class="brain-path" d="M70,100 C80,80 120,80 130,100 S170,120 160,140 S120,160 100,150 S60,140 70,100"/>
    <path class="brain-path" d="M60,90 C70,70 130,70 140,90 S180,110 170,130 S130,150 110,140 S50,130 60,90"/>
    
    <circle cx="100" cy="100" r="20" fill="url(#grad1)"/>
    <text x="100" y="105" text-anchor="middle" fill="linear-gradient(135deg, #1a2980, #26d0ce)" font-family="Arial" font-weight="bold" font-size="50">MITR</text>
    
    <g stroke="#4a90e2" stroke-width="1" opacity="0.5">
        <line x1="100" y1="80" x2="100" y2="40"/>
        <line x1="100" y1="120" x2="100" y2="160"/>
        <line x1="80" y1="100" x2="40" y2="100"/>
        <line x1="120" y1="100" x2="160" y2="100"/>
    </g>
</svg>
'''

# Convert SVG to base64 for embedding
AI_ICON_TITLE_B64 = base64.b64encode(AI_ICON_TITLE.encode()).decode()

# Custom CSS for styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .mitr-container {
        background: linear-gradient(135deg, #1a2980, #26d0ce);
        border-radius: 20px;
        padding: 2rem;
        margin: auto;
        width: 600px;
        height: 500px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .mitr-container:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 30px rgba(0,0,0,0.2);
    }
    .mitr-text {
        color: white;
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        margin-top: 1rem;
    }
    .ai-badge {
        background: rgba(255,255,255,0.1);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        color: white;
        font-size: 0.8rem;
        margin-top: 0.5rem;
    }
    .box-container {
        display: flex;
        justify-content: center;
        gap: 2rem;
        margin-top: 2rem;
        width: 100%;
        padding: 20px;
    }
    .stButton {
        background: none;
        border: none;
        padding: 0;
        width: 250px;
    }
    .stButton > button {
        width: 100%;
        height: 100%;
        padding: 0;
        background: none;
        border: none;
    }
    .clickable-box {
        background: linear-gradient(135deg, #1a2980, #26d0ce);
        border-radius: 15px;
        padding: 1.5rem;
        width: 100%;
        height: 150px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        box-shadow: 0 5px 15px rgba(0,0,0,0);
    }
    .clickable-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }
    .box-title {
        color: white;
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .box-subtitle {
        color: rgba(255,255,255,0.8);
        font-size: 0.9rem;
        text-align: center;
    }
          
    .animated-image {
        position: absolute;
        top: 0%;        
        width: 300px;
        height: 100px;  
        transform: rotateX(45deg);      
    }    
            
    .animated-box {
        position: absolute;
        top: 0%;        
        width: 300px;
        height: 600px; 
    } 
    .left-image {
        left: -600px;
        animation-delay: 0s;
        animation: slide-in-right 1s forwards;
    }
    .right-image {
        right: -500px;
        animation-delay: 0s;
        animation: slide-in-left 1s forwards;
    }
    @keyframes slide-in-right {
    0%{
        transform: translateX(-50%);}
        100% {
            transform: translateX(-20%);
        }
    }

    @keyframes slide-in-left {
    0%{
        transform: translateX(150%);}
        100% {
            transform: translateX(-20%);
        }
    }
    .large-animated-text{
    font-size:80px;    
    font-weight: bold;        
    color: #ba33b6; 
    background-image: linear-gradient(135deg, #1a2980, #26d0ce); 
    background-clip: text; 
    -webkit-background-clip: text; 
    -webkit-text-fill-color: transparent; 
    text-shadow: -3px 2px 0px rgba(0,0,0,0.16);
}        
    .stButton {
        background: linear-gradient(135deg, #1a2980, #26d0ce);
        color: white;
    }
    
    .stButton:hover {
        background: linear-gradient(135deg, #26d0ce, #1a2980);
    }      
    </style>
    """, unsafe_allow_html=True)

def handle_click(page):
    st.session_state.page = page
    st.experimental_rerun()

# Session state to track pages
if 'page' not in st.session_state:
    st.session_state.page = 'home'

def show_home():
    # Center container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # MITR AI Icon with animations
        st.markdown(f'''                    
            <div class="animated-image left-image">
                <img width="200" src="data:image/svg+xml;base64, PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNDIgMjQiPjxwYXRoIGZpbGw9IiMwMGFlZWYiIGQ9Ik0xMS4yIDEwLjFjMi40LS42IDUuMS0yLjMgNS4xLTUuMkMxNi4zLjYgMTIuMi42IDEwLjEuNkgxLjVjLjQuMi42IDEuMy42IDIuOCAwIDEuOC0uMSA0LjMtLjQgNy43bC0uMSAxLjRDMS4yIDE4LjQgMSAyMS44IDAgMjIuNmg3LjdjNS45IDAgOS41LTMgOS41LTYuOS4xLTMuNi0yLjUtNS4yLTYtNS42ek02LjEgNy45Yy4xLTEuNi4zLTMuMi41LTQuNy41LS4xIDEuMS0uMSAxLjUtLjEgMi42IDAgMy44IDEuMSAzLjggMi42IDAgMi42LTIuNiAzLjYtNS40IDMuNkg2bC4xLTEuNHptMS40IDExLjljLTEuNSAwLTIuMS0uNC0yLjEtLjYgMC0xLjQuMS0yLjUuMi00bC4yLTMuMmgxLjZjMi45IDAgNS4yLjkgNS4yIDMuOCAwIDIuNi0yIDQtNS4xIDR6bTEyOS4yLTEwYy0yLjItMS40LTQuMy0yLjYtNC4zLTQuMiAwLTIgMS43LTIuOCAzLjYtMi44IDIuMiAwIDQuMSAxLjMgNSAyLjlsLjYtNS4yYy0xLjUgMC0zLS40LTUuNC0uNC00LjEgMC04LjEgMS42LTguMSA2LjMgMCAzLjIgMi4zIDQuOSA1LjkgNy4xIDEuNyAxIDMuMSAyLjEgMy4xIDMuNyAwIDItMS43IDMuMS00IDMuMS0zIDAtNS0xLjctNi4xLTRsLS40IDUuNWMyLjMuOSA0LjMgMS4yIDYuMiAxLjIgNC43IDAgOC43LTIuNiA4LjctNi43IDAtMy4yLTIuNC01LTQuOC02LjV6bS0xNS43LjljMS4xLTEuOCA2LjItOS45IDcuNC0xMC4xaC01LjljLjIuMi4zLjguMyAxLjMgMCAuNy0uMyAxLjMtLjYgMS45LTEuNCAyLjItMi40IDMuOS00IDYuMi0uNi0xLjgtMS43LTQuMi0zLjEtNy41LS45LTItMS4zLTIuMi0yLjgtMi4yLS44IDAtMi42LjEtMy45LjIuOC40IDIgMi4zIDMuMSA0LjMgMS43IDMuMiAyLjggNS45IDMuNiA4LjcuMSAxLjktLjQgOC4xLTEuNCA5LjFoNmMtLjUtLjUtLjYtMS44LS42LTIuOCAwLTIuNC4yLTQuNi41LTYuMi4yLS45LjktMiAxLjQtMi45em0tNjQuNyA4LjJsLTQuNS02Yy0uMy0uNC0uOC0xLjEtMS4xLTEuMyAyLjktLjkgNS4zLTIuOCA1LjMtNi4zQzU2IDEgNTIuMy42IDQ5LjcuNmgtOC4yYy40LjIuNiAxLjIuNiAyLjggMCAxLjgtLjEgNC4zLS40IDcuN2wtLjEgMS40Yy0uNSA2LjgtLjggOS40LTEuNyAxMC4xaDZjLS40LS4yLS42LTEuMy0uNi0yLjggMC0xLjMuMS0zLjEuMi01LjRsLjEtMS42aC4xYy44IDAgMS4xLjUgMS42IDEuMWw2LjIgOC42Yy41LjcuOSAxIDIuNiAxIDEuMSAwIDIuOC0uMSA0LS4yLS43LS41LTEtLjctMy44LTQuNHpNNDcgMTBjLS4zIDAtLjcgMC0xLS4xbC4xLTEuNWMuMi0yLjYuMy00LjMuNS01LjIuNS0uMSAxLjItLjEgMS43LS4xIDIuMSAwIDMuMyAxIDMuMyAyLjcgMCAyLjYtMS45IDQuMi00LjYgNC4yem0tMTIuMyAyLjdsLS45LTMuNEwzMS40LjZoLTQuOGMuMi4yLjMuNy4zIDEuMlMyNS40IDUuNiAyNCA4LjZsLTEuNSAzLjNjLTIuNyA1LjctNC42IDkuMi02LjEgMTAuN2g1LjNjLS4xLS4yLS4xLS43LS4xLTEgMC0xLjIgMS4xLTMuMyAxLjUtNC4zbC41LS45aDIuNmMyLjYgMCA0LjItLjMgNS4yLS43bC41IDEuOWMxLjUgNS4yIDEuNyA1LjMgMy42IDUuMy42IDAgMi4xLS4xIDMuNC0uMi0xLjUtMS4zLTIuNS00LjEtNC4yLTEwem0tOS45LjZsMy42LTcuNyAyLjIgNy43aC01Ljh6bTM4LjgtMS4xYzAtNC40IDEuOS05LjUgNi42LTkuNSAyLjQgMCA0LjIgMS4zIDUuMiAzLjNMNzYgLjRjLTEuOSAwLTMtLjQtNS40LS40QzYzIDAgNTkgNS43IDU5IDEzYzAgNS4zIDMuMyAxMCA5IDEwIDQuNCAwIDctMi4yIDguMi01LjktMi44IDItNC41IDIuNS02LjQgMi41LTMuNSAwLTYuMi0yLjYtNi4yLTcuNHptNDIuOS41bC0uOS0zLjRjLS40LTEuNS0yLjQtOC43LTIuNC04LjdoLTQuOGMuMi4yLjMuNy4zIDEuMiAwIC42LTEuNCAzLjctMi45IDYuOGwtMS41IDMuM2MtMS4xIDIuNS0yLjMgNC44LTMuNCA2LjctMS43IDEuMS0yLjYgMS4yLTYuMiAxLjItMSAwLTEuNC0uMi0xLjQtMS4yIDAtMi4yLjMtNC40LjQtNi42bC4xLTEuM2MuNC01LjkuNy05LjUgMS42LTEwaC02Yy40LjUuNSAxLjMuNiAyLjggMCAxLjgtLjEgNC4zLS40IDcuN2wtLjEgMS40Yy0uNCA1LjktLjcgOS4xLTEuNiAxMC4xaDE1LjZjLS4xLS4yLS4xLS43LS4xLTEgMC0xLjIuOS0yLjkgMS41LTQuM2wuNS0uOUg5OGMyLjYgMCA0LjItLjMgNS4yLS43bC41IDEuOWMxLjUgNS4yIDEuNyA1LjMgMy42IDUuMy42IDAgMi4yLS4xIDMuNC0uMi0xLjYtMS40LTIuNi00LjItNC4yLTEwLjF6bS05LjkuNmwzLjYtNy43IDIuMiA3LjdoLTUuOHoiLz48L3N2Zz4=" alt="Left Image">
            </div>
            <div class="animated-image right-image">
                <p class="large-animated-text">Your AI friend in Finance</p>
            </div>
                    
            <div class="mitr-container">
                <img src="data:image/svg+xml;base64,{AI_ICON_B64}" width="400" height="400">                
            </div>
            
            <div class="box-container">
            <div>
                    <div class="clickable-box">
                        <div class="box-title">Trial Balance Analysis</div>
                        <div class="box-subtitle"> </div>
                    </div>
                </div>
                 <div>
                    <div class="clickable-box">
                        <div class="box-title">SAP Account Analysis</div>
                        <div class="box-subtitle"> </div>
                    </div>
            </div>

               <div>
                    <div class="clickable-box">
                        <div class="box-title">More...</div>
                        <div class="box-subtitle"> </div>
                    </div>
            </div>

            </div>
            ''', unsafe_allow_html=True)

        # Hidden state management
        if st.button("Let's go", key="tb_analysis_btn"):
            st.session_state.page = 'analysis'

def show_analysis():
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: flex-start;">
        <img src="data:image/svg+xml;base64,{AI_ICON_TITLE_B64}" width="100" height="100" style="margin-right: 20px;">
        <h1 style="background: linear-gradient(135deg, #1a2980, #26d0ce); background-clip: text; color: transparent; text-align:center; text-fill-color: transparent;">
            Trial Balance Analysis Dashboard
        </h1>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    # Dropdown to select prompt
    prompt = st.selectbox(
        "Select Analysis Prompt",
        [
            "Top 3 SAP accounts with largest balance changes",
            "Top 3 SAP accounts with largest rate changes",
            "YoY change in Principal Sum Amount with Average Balance"
        ],
        format_func=lambda x: f"🔍 {x}"
    )

    if prompt == "Top 3 SAP accounts with largest balance changes":

                filtered_data_increase = avg_data[avg_data['Sap Account'].isin(top3_increase)][['Sap Account', 'Balance_chg', 'Principal_chg', 'FloatingRate_chg', 'Interest_chg']].sort_values(by='Balance_chg', ascending=False)
                filtered_data_increase.columns = ['Sap Account', 'Balance Change','Principal Change', 'Floating Rate Change', 'Interest Rate Change']
                filtered_data_increase['Balance Change'] = filtered_data_increase['Balance Change'].map('${:,.0f}'.format)
                filtered_data_increase['Principal Change'] = filtered_data_increase['Principal Change'].map('${:,.0f}'.format)
                filtered_data_increase['Floating Rate Change'] = filtered_data_increase['Floating Rate Change'].map('{:.4f}'.format)
                filtered_data_increase['Interest Rate Change'] = filtered_data_increase['Interest Rate Change'].map('{:.4f}'.format)
                # Display the table with gradient border
                col1a, col1c = st.columns(2)
                with col1a:
                    st.markdown(f"""
                        <div style="text-align: center;">
                            <h4 style="color: #1a2980; background: linear-gradient(135deg, #1a2980, #26d0ce); padding: 0.5rem; border-radius: 5px; color: white;">Top 3 SAP Accounts with Largest Increase in Balance</h4>
                        </div> """, unsafe_allow_html=True)
                    col2a, col2b = st.columns([1,1])
                    with col2a:
                        st.markdown(f"""
                            <div style="margin-top: 5rem; text-align: center;">
                                <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px;">
                                    <div style="background-color: #f0f0f0; padding: 1rem; border-radius: 5px;">
                                        {filtered_data_increase.to_html(index=False)}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    with col2b:
                        st.plotly_chart(px.bar(filtered_data_increase, x='Balance Change', y='Sap Account', labels={'Balance Change': 'Change'}, orientation='h'), use_container_width=True)                        
                        

                with col1c:
                    if st.button("Get Commentary for Largest Increase in Balance", key="increase_commentary_btn", use_container_width=True):
                            commentary_increase = get_movement_commentary(top3_increase[0], avg_data)
                            if commentary_increase:
                                st.session_state.commentary_increase = commentary_increase
                    if 'commentary_increase' in st.session_state:
                        st.markdown(f"""
                        <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px; background-color: #f0f0f0;">
                            <h3 style="color: #1a2980; text-align: center;">MITR Generated Commentary</h3>
                            <p class="typing-text">{st.session_state.commentary_increase}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("""
                        <style>
                        @keyframes typing {
                            from { width: 0; }
                            to { width: 100%; }
                        }
                        .typing-text {
                            overflow: hidden;
                            white-space: pre-wrap;
                            border-right: 0.15em solid orange;
                            animation: typing 4s steps(40, end), blink-caret 0.75s step-end infinite;
                            display: inline-block;
                            box-sizing: border-box;
                            width: 100%;
                        }
                        @keyframes blink-caret {
                            from, to { border-color: transparent; }
                            50% { border-color: orange; }
                        }
                        </style>
                        """, unsafe_allow_html=True)

                filtered_data_decrease = avg_data[avg_data['Sap Account'].isin(top3_decrease)][['Sap Account', 'Balance_chg', 'Principal_chg', 'FloatingRate_chg', 'Interest_chg']].sort_values(by='Balance_chg', ascending=True)
                filtered_data_decrease.columns = ['Sap Account', 'Balance Change', 'Principal Change', 'Floating Rate Change', 'Interest Rate Change']
                filtered_data_decrease['Balance Change'] = filtered_data_decrease['Balance Change'].map('${:,.0f}'.format)
                filtered_data_decrease['Principal Change'] = filtered_data_decrease['Principal Change'].map('${:,.0f}'.format)
                filtered_data_decrease['Floating Rate Change'] = filtered_data_decrease['Floating Rate Change'].map('{:.4f}'.format)
                filtered_data_decrease['Interest Rate Change'] = filtered_data_decrease['Interest Rate Change'].map('{:.4f}'.format)
                col1a, col1c = st.columns(2)
                with col1a:
                    st.markdown(f"""
                        <div style="text-align: center;">
                            <h4 style="color: #1a2980; background: linear-gradient(135deg, #1a2980, #26d0ce); padding: 0.5rem; border-radius: 5px; color: white;">Top 3 SAP Accounts with Largest Decrease in Balance</h4>
                        </div> """, unsafe_allow_html=True)
                    col2a, col2b = st.columns([1,1])
                    with col2a:
                        st.markdown(f"""
                            <div style="margin-top: 5rem; text-align: center;">
                                <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px;">
                                    <div style="background-color: #f0f0f0; padding: 1rem; border-radius: 5px;">
                                        {filtered_data_decrease.to_html(index=False)}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    with col2b:
                        st.plotly_chart(px.bar(filtered_data_decrease, x='Balance Change', y='Sap Account', labels={'Balance Change': 'Change'}, orientation='h', color_discrete_sequence=['#cd5c5c']), use_container_width=True)
                        
                        

                with col1c:
                    if st.button("Get Commentary for Largest Decrease in Balance", key="decrease_commentary_btn", use_container_width=True):
                            commentary_decrease = get_movement_commentary(top3_decrease[0], avg_data)
                            if commentary_decrease:
                                st.session_state.commentary_decrease = commentary_decrease

                    if 'commentary_decrease' in st.session_state:
                        st.markdown(f"""
                        <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px; background-color: #f0f0f0;">
                            <h3 style="color: #1a2980; text-align: center;">MITR Generated Commentary</h3>
                            <p class="typing-text">{st.session_state.commentary_decrease}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("""
                        <style>
                        @keyframes typing {
                            from { width: 0; }
                            to { width: 100%; }
                        }
                        .typing-text {
                            overflow: hidden;
                            white-space: pre-wrap;
                            border-right: 0.15em solid orange;
                            animation: typing 4s steps(40, end), blink-caret 0.75s step-end infinite;
                            display: inline-block;
                            box-sizing: border-box;
                            width: 100%;
                        }
                        @keyframes blink-caret {
                            from, to { border-color: transparent; }
                            50% { border-color: orange; }
                        }
                        </style>
                        """, unsafe_allow_html=True)


        
    elif prompt == "YoY change in Principal Sum Amount with Average Balance":
        st.markdown(f"""
                        <div style="text-align: center;">
                            <h4 style="color: #1a2980; background: linear-gradient(135deg, #1a2980, #26d0ce); padding: 0.5rem; border-radius: 5px; color: white;">Change in Floating and Interest Rates with Average Balance</h4>
                        </div> """, unsafe_allow_html=True)
        st.dataframe(avg_data)

    elif prompt == "Top 3 SAP accounts with largest rate changes":
        tab1, tab2 = st.tabs(["Floating Rate Changes", "Interest Rate Changes"])

        with tab1:
            filtered_data_floating_increase = avg_data[avg_data['Sap Account'].isin(top3_floating_increase)][['Sap Account', 'Balance_chg', 'Principal_chg', 'FloatingRate_chg', 'Interest_chg']]
            filtered_data_floating_increase.columns = ['Sap Account', 'Balance Change', 'Principal Change', 'Floating Rate Change', 'Interest Rate Change']
            
            filtered_data_floating_decrease = avg_data[avg_data['Sap Account'].isin(top3_floating_decrease)][['Sap Account', 'Balance_chg', 'Principal_chg', 'FloatingRate_chg', 'Interest_chg']]
            filtered_data_floating_decrease.columns = ['Sap Account', 'Balance Change', 'Principal Change', 'Floating Rate Change', 'Interest Rate Change']
            
            col3a, col3b = st.columns(2)
            
            with col3a:
                st.markdown(f"""
            <div style="text-align: center;">
            <h4 style="color: #1a2980; background: linear-gradient(135deg, #1a2980, #26d0ce); padding: 0.5rem; border-radius: 5px; color: white;">Top 3 SAP Accounts with Largest Increase in Floating Rate</h4>
            </div> """, unsafe_allow_html=True)

                col31a, col32  = st.columns([1, 1])
                with col31a:
                        st.markdown(f"""
                    <div style="margin-top: 5rem; text-align: center;">
                    <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px;">
                    <div style="background-color: #f0f0f0; padding: 1rem; border-radius: 5px;">
                    {filtered_data_floating_increase.to_html(index=False)}
                    </div>
                    </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col32:
                    st.plotly_chart(px.bar(filtered_data_floating_increase, x='Floating Rate Change', y='Sap Account', labels={'Floating Rate Change': 'Change'}, orientation='h'), use_container_width=True)
            
            with col3b:
                if st.button("Get Commentary for Largest Increase in Floating Rate", key="floating_increase_commentary_btn", use_container_width=True):
                    commentary_floating_increase = get_movement_commentary(top3_floating_increase[0], avg_data)
                    if commentary_floating_increase:
                        st.session_state.commentary_floating_increase = commentary_floating_increase
                if 'commentary_floating_increase' in st.session_state:
                    st.markdown(f"""
                    <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px; background-color: #f0f0f0;">
                    <h3 style="color: #1a2980; text-align: center;">MITR Generated Commentary</h3>
                    <p class="typing-text">{st.session_state.commentary_floating_increase}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("""
                    <style>
                    @keyframes typing {
                    from { width: 0; }
                    to { width: 100%; }
                    }
                    .typing-text {
                    overflow: hidden;
                    white-space: pre-wrap;
                    border-right: 0.15em solid orange;
                    animation: typing 4s steps(40, end), blink-caret 0.75s step-end infinite;
                    display: inline-block;
                    box-sizing: border-box;
                    width: 100%;
                    }
                    @keyframes blink-caret {
                    from, to { border-color: transparent; }
                    50% { border-color: orange; }
                    }
                    </style>
                    """, unsafe_allow_html=True)

            col2a, col2b = st.columns(2)
            
            with col2a:
                st.markdown(f"""
            <div style="text-align: center;">
            <h4 style="color: #1a2980; background: linear-gradient(135deg, #1a2980, #26d0ce); padding: 0.5rem; border-radius: 5px; color: white;">Top 3 SAP Accounts with Largest Decrease in Floating Rate</h4>
            </div> """, unsafe_allow_html=True)
                
                col23a, col23b = st.columns([1, 1])
                with col23a:
                    st.markdown(f"""
                <div style="margin-top: 5rem; text-align: center;">
                <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px;">
                <div style="background-color: #f0f0f0; padding: 1rem; border-radius: 5px;">
                {filtered_data_floating_decrease.to_html(index=False)}
                </div>
                </div>
                </div>
                """, unsafe_allow_html=True)
            
                with col23b:
                    st.plotly_chart(px.bar(filtered_data_floating_decrease, x='Floating Rate Change', y='Sap Account', labels={'Floating Rate Change': 'Change'}, orientation='h'), use_container_width=True)
            
            with col2b:
                if st.button("Get Commentary for Largest Decrease in Floating Rate", key="floating_decrease_commentary_btn", use_container_width=True):
                    commentary_floating_decrease = get_movement_commentary(top3_floating_decrease[0], avg_data)
                    if commentary_floating_decrease:
                        st.session_state.commentary_floating_decrease = commentary_floating_decrease
                if 'commentary_floating_decrease' in st.session_state:
                    st.markdown(f"""
                    <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px; background-color: #f0f0f0;">
                    <h3 style="color: #1a2980; text-align: center;">MITR Generated Commentary</h3>
                    <p class="typing-text">{st.session_state.commentary_floating_decrease}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("""
                    <style>
                    @keyframes typing {
                    from { width: 0; }
                    to { width: 100%; }
                    }
                    .typing-text {
                    overflow: hidden;
                    white-space: pre-wrap;
                    border-right: 0.15em solid orange;
                    animation: typing 4s steps(40, end), blink-caret 0.75s step-end infinite;
                    display: inline-block;
                    box-sizing: border-box;
                    width: 100%;
                    }
                    @keyframes blink-caret {
                    from, to { border-color: transparent; }
                    50% { border-color: orange; }
                    }
                    </style>
                    """, unsafe_allow_html=True)

        with tab2:
            filtered_data_int_increase = avg_data[avg_data['Sap Account'].isin(top3_int_increase)][['Sap Account', 'Balance_chg', 'Principal_chg', 'FloatingRate_chg', 'Interest_chg']]
            filtered_data_int_increase.columns = ['Sap Account', 'Balance Change', 'Principal Change', 'Floating Rate Change', 'Interest Rate Change']
            
            filtered_data_int_decrease = avg_data[avg_data['Sap Account'].isin(top3_int_decrease)][['Sap Account', 'Balance_chg', 'Principal_chg', 'FloatingRate_chg', 'Interest_chg']]
            filtered_data_int_decrease.columns = ['Sap Account', 'Balance Change', 'Principal Change', 'Floating Rate Change', 'Interest Rate Change']
            
            col1a, col1c = st.columns(2)
            
            with col1a:
                st.markdown(f"""
            <div style="text-align: center;">
            <h4 style="color: #1a2980; background: linear-gradient(135deg, #1a2980, #26d0ce); padding: 0.5rem; border-radius: 5px; color: white;">Top 3 SAP Accounts with Largest Increase in Interest Rate</h4>
            </div> """, unsafe_allow_html=True)
            
                col13a, col13b = st.columns([1, 1])
                with col13a:
                    st.markdown(f"""
                <div style="margin-top: 5rem; text-align: center;">
                <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px;">
                <div style="background-color: #f0f0f0; padding: 1rem; border-radius: 5px;">
                {filtered_data_int_increase.to_html(index=False)}
                </div>
                </div>
                </div>
                """, unsafe_allow_html=True)
                
                with col13b:
                    st.plotly_chart(px.bar(filtered_data_int_increase, x='Interest Rate Change', y='Sap Account', labels={'Interest Rate Change': 'Change'}, orientation='h'), use_container_width=True)
                
            with col1c:
                if st.button("Get Commentary for Largest Increase in Interest Rate", key="int_increase_commentary_btn", use_container_width=True):
                    commentary_int_increase = get_movement_commentary(top3_int_increase[0], avg_data)
                    if commentary_int_increase:
                        st.session_state.commentary_int_increase = commentary_int_increase
                if 'commentary_int_increase' in st.session_state:
                    st.markdown(f"""
                    <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px; background-color: #f0f0f0;">
                    <h3 style="color: #1a2980; text-align: center;">MITR Generated Commentary</h3>
                    <p class="typing-text">{st.session_state.commentary_int_increase}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("""
                    <style>
                    @keyframes typing {
                    from { width: 0; }
                    to { width: 100%; }
                    }
                    .typing-text {
                    overflow: hidden;
                    white-space: pre-wrap;
                    border-right: 0.15em solid orange;
                    animation: typing 4s steps(40, end), blink-caret 0.75s step-end infinite;
                    display: inline-block;
                    box-sizing: border-box;
                    width: 100%;
                    }
                    @keyframes blink-caret {
                    from, to { border-color: transparent; }
                    50% { border-color: orange; }
                    }
                    </style>
                    """, unsafe_allow_html=True)

            col2a, col2c = st.columns(2)
            
            with col2a:
                st.markdown(f"""
            <div style="text-align: center;">
            <h4 style="color: #1a2980; background: linear-gradient(135deg, #1a2980, #26d0ce); padding: 0.5rem; border-radius: 5px; color: white;">Top 3 SAP Accounts with Largest Decrease in Interest Rate</h4>
            </div> """, unsafe_allow_html=True)
                
                col22a, col22b = st.columns([1, 1])
                with col22a:
                    st.markdown(f"""
                <div style="margin-top: 5rem; text-align: center;">
                <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px;">
                <div style="background-color: #f0f0f0; padding: 1rem; border-radius: 5px;">
                {filtered_data_int_decrease.to_html(index=False)}
                </div>
                </div>
                </div>
                """, unsafe_allow_html=True)
                
                with col22b:
                    st.plotly_chart(px.bar(filtered_data_int_decrease, x='Interest Rate Change', y='Sap Account', labels={'Interest Rate Change': 'Change'}, orientation='h'), use_container_width=True)
                
            with col2c:
                if st.button("Get Commentary for Largest Decrease in Interest Rate", key="int_decrease_commentary_btn", use_container_width=True):
                    commentary_int_decrease = get_movement_commentary(top3_int_decrease[0], avg_data)
                    if commentary_int_decrease:
                        st.session_state.commentary_int_decrease = commentary_int_decrease
                if 'commentary_int_decrease' in st.session_state:
                    st.markdown(f"""
                    <div style="border: 2px solid; border-image: linear-gradient(135deg, #1a2980, #26d0ce) 1; padding: 1rem; border-radius: 10px; background-color: #f0f0f0;">
                    <h3 style="color: #1a2980; text-align: center;">MITR Generated Commentary</h3>
                    <p class="typing-text">{st.session_state.commentary_int_decrease}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("""
                    <style>
                    @keyframes typing {
                    from { width: 0; }
                    to { width: 100%; }
                    }
                    .typing-text {
                    overflow: hidden;
                    white-space: pre-wrap;
                    border-right: 0.15em solid orange;
                    animation: typing 4s steps(40, end), blink-caret 0.75s step-end infinite;
                    display: inline-block;
                    box-sizing: border-box;
                    width: 100%;
                    }
                    @keyframes blink-caret {
                    from, to { border-color: transparent; }
                    50% { border-color: orange; }
                    }
                    </style>
                    """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div style="text-align: center;">
            <h4 style="color: #1a2980; background: linear-gradient(135deg, #1a2980, #26d0ce); padding: 0.6rem; color: white;">View Data</h4>
            </div> """, unsafe_allow_html=True)

        col5, col6 = st.columns([1, 1])
        
        with col5:
            with st.expander("Show Previous Year Data", expanded=False):
                st.dataframe(df_2023.head(10))            
        with col6:
            with st.expander("Show Current Year Data", expanded=False):
                st.dataframe(df_2024.head(10))
    
    with col3:
        if st.button("← Back to Home"):
            st.session_state.page = 'home'
            st.rerun()

def show_reports():
    st.title("Reports Dashboard")
    
    # Add a back button
    if st.button("← Back to Home"):
        st.session_state.page = 'home'
        st.experimental_rerun()
    
    st.write("Reports dashboard content goes here...")

# Main app logic
if st.session_state.page == 'home':
    show_home()
elif st.session_state.page == 'analysis':
    show_analysis()
elif st.session_state.page == 'reports':
    show_reports()