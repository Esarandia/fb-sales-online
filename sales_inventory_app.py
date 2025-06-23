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

# --- Simplified Inventory Display ---
@st.cache_data(show_spinner=False)
def get_simple_inventory():
    # Buko Juice
    buko_juice_cup = [
        int(sheet.acell(cell_map["Buko Juice"]["Cup"][size]).value or 0)
        for size in ["Small", "Medium", "Large"]
    ]
    buko_juice_bottle = [
        int(sheet.acell(cell_map["Buko Juice"]["Bottle"][size]).value or 0)
        for size in ["Small", "Medium", "Large"]
    ]
    # Buko Shake
    buko_shake_cup = [
        int(sheet.acell(cell_map["Buko Shake"]["Cup"][size]).value or 0)
        for size in ["Small", "Medium", "Large"]
    ]
    buko_shake_bottle = [
        int(sheet.acell(cell_map["Buko Shake"]["Bottle"][size]).value or 0)
        for size in ["Small", "Medium", "Large"]
    ]
    # Pizza
    pizza_flavors = [
        int(sheet.acell(cell_map["Pizza"]["Box"][flavor]).value or 0)
        for flavor in ["Supreme", "Hawaiian", "Pepperoni", "Ham & Cheese", "Shawarma"]
    ]
    data = [
        ["Buko Juice - Cup"] + buko_juice_cup,
        ["Buko Juice - Bottle"] + buko_juice_bottle,
        ["Buko Shake - Cup"] + buko_shake_cup,
        ["Buko Shake - Bottle"] + buko_shake_bottle,
        ["Pizza"] + pizza_flavors
    ]
    columns = [
        "Product",
        "Small", "Medium", "Large"
    ]
    pizza_columns = [
        "Product",
        "Supreme", "Hawaiian", "Pepperoni", "Ham & Cheese", "Shawarma"
    ]
    df1 = pd.DataFrame(data[:4], columns=columns)
    df2 = pd.DataFrame([data[4]], columns=pizza_columns)
    return df1, df2

# --- Streamlit App ---

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

st.title("Facebuko Sales")

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

# Make Add to Order button green
add_to_order = st.button("Add to Order", key="add_to_order_btn", help="Add item to order", use_container_width=True, type="secondary")

# Add current item to cart
if add_to_order:
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
    order_total = 0
    for idx, item in enumerate(st.session_state["cart"], 1):
        # Calculate price for each item
        if item["product"] == "Pizza":
            item_price = price_map[item["packaging"]]["Supreme" if item["size"] == "Supreme" else "Others"]
            desc = f"{item['product']} - {item['pizza_type']} (x{item['qty']})"
        else:
            item_price = price_map[item["packaging"]][item["size"]]
            desc = f"{item['product']} - {item['packaging']} - {item['size']} (x{item['qty']})"
        item_total = item_price * item["qty"]
        order_total += item_total
        cols = st.columns([6, 2, 1])
        cols[0].write(f"{idx}. {desc}")
        cols[1].write(f"₱{item_price} x {item['qty']} = ₱{item_total}")
        # Use a red X text button for remove
        if cols[2].button("X", key=f"remove_{idx}", help="Remove item from cart"):
            remove_idx = idx - 1
        cols[2].markdown(
            f"<div class='remove-x-btn' style='display:inline-block;'><button disabled style='background-color: #db2828; color: white; border: none; font-weight: bold;'>X</button></div>",
            unsafe_allow_html=True
        )
    st.markdown(f"**Total Order Price: ₱{order_total}**")
    if remove_idx is not None:
        st.session_state["cart"].pop(remove_idx)
        st.rerun()
    # Make Submit Order button green
    submit_order = st.button("Submit Order", key="submit_order_btn", help="Submit the entire order", use_container_width=True, type="secondary")
    if submit_order:
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
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- Place this at the very end of the script ---
st.subheader("Current Inventory")
if st.button("Refresh Inventory"):
    st.cache_data.clear()
df1, df2 = get_simple_inventory()
st.dataframe(df1, hide_index=True)
st.dataframe(df2, hide_index=True)

# Add custom CSS for green and red buttons
st.markdown("""
    <style>
    .add-order-btn button, .submit-order-btn button {
        background-color: #21ba45 !important;
        color: white !important;
    }
    .remove-x-btn button {
        background-color: #db2828 !important;
        color: white !important;
        border: none !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)
