import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import base64

# --- Google Sheets Setup ---
SHEET_NAME = "MighteeMart1"
SPREADSHEET_ID = "1rNAba2jqzBqzXZZxplfkXc5XthDbgVVvntDOIdDEx9w"

# --- Decode base64 secret and authorize ---
creds_b64 = os.environ["GOOGLE_SERVICE_ACCOUNT_B64"]
creds_bytes = base64.b64decode(creds_b64)
creds_dict = json.loads(creds_bytes.decode("utf-8"))

scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

# --- Cell Map Matching Excel Structure ---
cell_map = {
    "Buko Juice": {
        "Cup": {
            "Small": "C6",
            "Medium": "D6",
            "Large": "E6"
        },
        "Bottle": {
            "Small": "F6",
            "Medium": "G6",
            "Large": "H6"
        }
    },
    "Buko Shake": {
        "Cup": {
            "Small": "I6",
            "Medium": "J6",
            "Large": "K6"
        },
        "Bottle": {
            "Small": "L6",
            "Medium": "M6",
            "Large": "N6"
        }
    },
    "Pizza": {
        "Box": {
            "Supreme": "O6",
            "Others": "P6"
        }
    }
}

# --- Prices ---
price_map = {
    "Cup": {"Small": 65, "Medium": 75, "Large": 95},
    "Bottle": {"Small": 65, "Medium": 75, "Large": 115},
    "Box": {"Supreme": 250, "Others": 190}
}

# --- Streamlit App ---
st.title("Sales Entry - Google Sheets")

product = st.selectbox("Select Product", ["Buko Juice", "Buko Shake", "Pizza"])

if product != "Pizza":
    packaging = st.selectbox("Select Packaging", ["Cup", "Bottle"])
    size = st.selectbox("Select Size", ["Small", "Medium", "Large"])
    price = price_map[packaging][size]
else:
    packaging = "Box"
    size = st.selectbox("Select Pizza Type", ["Supreme", "Others"])
    price = price_map[packaging][size]

qty = st.number_input("Enter Quantity", min_value=1, step=1)
amount = qty * price
st.write(f"**Amount: ₱{amount}**")

if st.button("Submit"):
    try:
        target_cell = cell_map[product][packaging][size]
        current_value = sheet.acell(target_cell).value
        current_value = int(current_value) if current_value and current_value.isdigit() else 0

        new_value = current_value + qty
        sheet.update_acell(target_cell, new_value)

        st.success(f"Updated {product} - {packaging} - {size} with +{qty} (New total: {new_value})")
    except Exception as e:
        st.error(f"Error: {e}")
