import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import base64
import pandas as pd

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
            "Hawaiian": "P6",
            "Pepperoni": "Q6",
            "Ham & Cheese": "R6",
            "Shawarma": "S6"
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

# --- Inventory Display ---
@st.cache_data(show_spinner=False)
def get_inventory():
    inventory_data = []
    # Buko Juice
    for packaging in ["Cup", "Bottle"]:
        for size in ["Small", "Medium", "Large"]:
            cell = cell_map["Buko Juice"][packaging][size]
            value = sheet.acell(cell).value
            value = int(value) if value and str(value).isdigit() else 0
            inventory_data.append({
                "Product": "Buko Juice",
                "Packaging/Flavor": packaging,
                "Size": size,
                "Quantity": value
            })
    # Buko Shake
    for packaging in ["Cup", "Bottle"]:
        for size in ["Small", "Medium", "Large"]:
            cell = cell_map["Buko Shake"][packaging][size]
            value = sheet.acell(cell).value
            value = int(value) if value and str(value).isdigit() else 0
            inventory_data.append({
                "Product": "Buko Shake",
                "Packaging/Flavor": packaging,
                "Size": size,
                "Quantity": value
            })
    # Pizza
    for flavor in ["Supreme", "Hawaiian", "Pepperoni", "Ham & Cheese", "Shawarma"]:
        cell = cell_map["Pizza"]["Box"][flavor]
        value = sheet.acell(cell).value
        value = int(value) if value and str(value).isdigit() else 0
        inventory_data.append({
            "Product": "Pizza",
            "Packaging/Flavor": flavor,
            "Size": "Box",
            "Quantity": value
        })
    return pd.DataFrame(inventory_data)

st.subheader("Current Inventory")
st.dataframe(get_inventory())

# Handle qty reset before rendering widgets
if st.session_state.get("reset_qty", False):
    st.session_state["qty"] = 1
    st.session_state.pop("reset_qty")
    # Do NOT call st.rerun() here

# Show success message if present
if st.session_state.get("success_msg"):
    st.success(st.session_state["success_msg"])
    st.session_state.pop("success_msg")

# Initialize cart in session state
if "cart" not in st.session_state:
    st.session_state["cart"] = []

st.title("Sales Entry - Google Sheets")

product = st.selectbox("Select Product", ["Buko Juice", "Buko Shake", "Pizza"])

if product != "Pizza":
    packaging = st.selectbox("Select Packaging", ["Cup", "Bottle"])
    size = st.selectbox("Select Size", ["Small", "Medium", "Large"])
    price = price_map[packaging][size]
    pizza_type = None
else:
    packaging = "Box"
    pizza_type = st.selectbox(
        "Select Pizza Flavor",
        ["Supreme", "Hawaiian", "Pepperoni", "Ham & Cheese", "Shawarma"]
    )
    if pizza_type == "Supreme":
        size = "Supreme"
    else:
        size = pizza_type
    price = price_map[packaging]["Supreme" if pizza_type == "Supreme" else "Others"]

qty = st.number_input("Enter Quantity", min_value=1, step=1, key="qty")
amount = qty * price
st.write(f"**Amount: ₱{amount}**")

if st.button("Add to Order"):
    # Add current item to cart
    item = {
        "product": product,
        "packaging": packaging,
        "size": size,
        "qty": qty,
        "pizza_type": pizza_type
    }
    st.session_state["cart"].append(item)
    st.session_state["reset_qty"] = True
    st.rerun()

# Display cart
if st.session_state["cart"]:
    st.subheader("Current Order")
    remove_idx = None
    for idx, item in enumerate(st.session_state["cart"], 1):
        if item["product"] == "Pizza":
            desc = f"{item['product']} - {item['pizza_type']} (x{item['qty']})"
        else:
            desc = f"{item['product']} - {item['packaging']} - {item['size']} (x{item['qty']})"
        cols = st.columns([6, 1])
        cols[0].write(f"{idx}. {desc}")
        if cols[1].button("Remove", key=f"remove_{idx}"):
            remove_idx = idx - 1
    if remove_idx is not None:
        st.session_state["cart"].pop(remove_idx)
        st.rerun()
    if st.button("Submit Order"):
        try:
            for item in st.session_state["cart"]:
                if item["product"] == "Pizza":
                    target_cell = cell_map[item["product"]][item["packaging"]][item["size"]]
                else:
                    target_cell = cell_map[item["product"]][item["packaging"]][item["size"]]
                current_value = sheet.acell(target_cell).value
                current_value = int(current_value) if current_value and str(current_value).isdigit() else 0
                new_value = current_value + item["qty"]
                sheet.update_acell(target_cell, new_value)
            st.session_state["success_msg"] = f"Order submitted! {len(st.session_state['cart'])} items processed."
            st.session_state["cart"] = []
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
