import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import base64
import pandas as pd
from datetime import datetime
import pytz

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

# --- Daily Sheet Automation ---
def get_daily_worksheets():
    today_str = datetime.now(pytz.timezone("Asia/Manila")).strftime("%Y-%m-%d")
    inventory_title = f"MighteeMart1_{today_str}"
    saleslog_title = f"SalesLog_{today_str}"
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    # Check if sheets exist
    sheet_titles = [ws.title for ws in spreadsheet.worksheets()]
    # Inventory sheet
    if inventory_title not in sheet_titles:
        # Copy structure from original inventory sheet
        new_sheet = spreadsheet.duplicate_sheet(
            source_sheet_id=spreadsheet.worksheet(SHEET_NAME).id,
            insert_sheet_index=None,
            new_sheet_name=inventory_title
        )
        # Set all inventory cells to 0
        ws = spreadsheet.worksheet(inventory_title)
        # Buko Juice
        for packaging in ["Cup", "Bottle"]:
            for size in ["Small", "Medium", "Large"]:
                ws.update_acell(cell_map["Buko Juice"][packaging][size], 0)
        # Buko Shake
        for packaging in ["Cup", "Bottle"]:
            for size in ["Small", "Medium", "Large"]:
                ws.update_acell(cell_map["Buko Shake"][packaging][size], 0)
        # Pizza
        for flavor in ["Supreme", "Hawaiian", "Pepperoni", "Ham & Cheese", "Shawarma"]:
            ws.update_acell(cell_map["Pizza"]["Box"][flavor], 0)
    # SalesLog sheet
    if saleslog_title not in sheet_titles:
        # Copy structure from original sales log sheet
        spreadsheet.duplicate_sheet(
            source_sheet_id=spreadsheet.worksheet("SalesLog").id,
            insert_sheet_index=None,
            new_sheet_name=saleslog_title
        )
        # Clear all rows except header in the new sales log sheet
        ws_log = spreadsheet.worksheet(saleslog_title)
        all_rows = ws_log.get_all_values()
        if len(all_rows) > 1:
            ws_log.batch_clear([f"A2:G{len(all_rows)}"])
    # Return worksheet objects
    inventory_ws = spreadsheet.worksheet(inventory_title)
    saleslog_ws = spreadsheet.worksheet(saleslog_title)
    return inventory_ws, saleslog_ws

# --- Simplified Inventory Display ---
@st.cache_data(show_spinner=False)
def get_simple_inventory():
    # Buko Juice
    buko_juice_cup = [
        int(inventory_ws.acell(cell_map["Buko Juice"]["Cup"][size]).value or 0)
        for size in ["Small", "Medium", "Large"]
    ]
    buko_juice_bottle = [
        int(inventory_ws.acell(cell_map["Buko Juice"]["Bottle"][size]).value or 0)
        for size in ["Small", "Medium", "Large"]
    ]
    # Buko Shake
    buko_shake_cup = [
        int(inventory_ws.acell(cell_map["Buko Shake"]["Cup"][size]).value or 0)
        for size in ["Small", "Medium", "Large"]
    ]
    buko_shake_bottle = [
        int(inventory_ws.acell(cell_map["Buko Shake"]["Bottle"][size]).value or 0)
        for size in ["Small", "Medium", "Large"]
    ]
    # Pizza
    pizza_flavors = [
        int(inventory_ws.acell(cell_map["Pizza"]["Box"][flavor]).value or 0)
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

# Always initialize session state keys before any logic
if "cart" not in st.session_state:
    st.session_state["cart"] = []
if "show_change" not in st.session_state:
    st.session_state["show_change"] = False
if "last_change" not in st.session_state:
    st.session_state["last_change"] = 0

# Use tabs for navigation (restore tab design)
tabs = st.tabs(["Facebuko Sales", "Current Inventory", "Remove Order", "Stocks Inventory"])

with tabs[0]:
    inventory_ws, saleslog_ws = get_daily_worksheets()
    st.markdown('<h2 style="color:#21ba45;">🛒 Facebuko Sales</h2>', unsafe_allow_html=True)
    # --- Total Sales (from Current Inventory Table) ---
    df1, df2 = get_simple_inventory()
    total_sales = 0
    # Buko Juice & Buko Shake
    for idx, row in df1.iterrows():
        product = row['Product']
        for size in ['Small', 'Medium', 'Large']:
            qty = row[size]
            if qty > 0:
                if 'Cup' in product:
                    price = price_map['Cup'][size]
                elif 'Bottle' in product:
                    price = price_map['Bottle'][size]
                else:
                    continue
                total_sales += qty * price
    # Pizza
    pizza_row = df2.iloc[0]
    for flavor in ['Supreme', 'Hawaiian', 'Pepperoni', 'Ham & Cheese', 'Shawarma']:
        qty = pizza_row[flavor]
        if qty > 0:
            price = price_map['Box']['Supreme' if flavor == 'Supreme' else 'Others']
            total_sales += qty * price
    # If all inventory is zero, total_sales should be zero
    if (df1[['Small', 'Medium', 'Large']].sum().sum() + df2[['Supreme', 'Hawaiian', 'Pepperoni', 'Ham & Cheese', 'Shawarma']].sum().sum()) == 0:
        total_sales = 0
    st.markdown(f"<h2 style='color:#2185d0;'>₱{total_sales:,.2f} <span style='font-size:22px;'>Total Sales</span></h2>", unsafe_allow_html=True)
    st.markdown('---')

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
    add_to_order = st.button("Add to Order", key="add_to_order_btn")
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
    st.markdown('---')

    # --- Current Order Section ---
    if st.session_state["cart"]:
        st.markdown('<h2 style="color:#2185d0;">🧾 Current Order</h2>', unsafe_allow_html=True)
        st.markdown('---')
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
            if cols[2].button("X", key=f"remove_{idx}", help="Remove item from cart"):
                remove_idx = idx - 1
        st.markdown(f"**Total Order Price: ₱{order_total}**")
        # Cash received input
        cash_key = "cash_received"
        if cash_key not in st.session_state:
            st.session_state[cash_key] = 0
        cash_received = st.number_input("Cash Received", min_value=0, step=1, key=cash_key)
        if remove_idx is not None:
            st.session_state["cart"].pop(remove_idx)
            st.rerun()
        submit_order = st.button("Submit Order", key="submit_order_btn")
        # State for showing change and waiting for OK
        if "show_change" not in st.session_state:
            st.session_state["show_change"] = False
        if "last_change" not in st.session_state:
            st.session_state["last_change"] = 0
        if submit_order and not st.session_state["show_change"]:
            if cash_received < order_total:
                st.error(f"Insufficient cash! Received ₱{cash_received}, need ₱{order_total}.")
            else:
                st.session_state["last_change"] = cash_received - order_total
                st.session_state["show_change"] = True
                st.session_state["success_msg"] = f"Order ready to complete! {len(st.session_state['cart'])} items."
        # Show change and Complete Order button if needed
        if st.session_state["show_change"]:
            st.success(f"Order submitted! Change: ₱{st.session_state['last_change']}")
            if st.button("Complete Order", key="ok_btn"):
                try:
                    for item in st.session_state["cart"]:
                        if item["product"] == "Pizza":
                            target_cell = cell_map[item["product"]][item["packaging"]][item["size"]]
                            item_price = price_map[item["packaging"]]["Supreme" if item["size"] == "Supreme" else "Others"]
                            size_or_flavor = item["pizza_type"]
                        else:
                            target_cell = cell_map[item["product"]][item["packaging"]][item["size"]]
                            item_price = price_map[item["packaging"]][item["size"]]
                            size_or_flavor = item["size"]
                        current_value = inventory_ws.acell(target_cell).value
                        current_value = int(current_value) if current_value and str(current_value).isdigit() else 0
                        new_value = current_value + item["qty"]
                        inventory_ws.update_acell(target_cell, new_value)
                        # Log each item in the sales log
                        ph_tz = pytz.timezone("Asia/Manila")
                        now = datetime.now(ph_tz)
                        saleslog_ws.append_row([
                            now.strftime("%Y-%m-%d"),
                            now.strftime("%H:%M:%S"),
                            item["product"],
                            item["packaging"],
                            size_or_flavor,
                            item["qty"],
                            item_price * item["qty"]
                        ])
                    st.session_state["cart"] = []
                    st.session_state["show_change"] = False
                    st.session_state["last_change"] = 0
                    st.session_state.pop("success_msg", None)
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        st.markdown('---')

with tabs[1]:
    inventory_ws, _ = get_daily_worksheets()
    st.markdown('<h2 style="color:#f2711c;">📦 Current Inventory</h2>', unsafe_allow_html=True)
    st.markdown('---')
    if st.button("Refresh Inventory"):
        st.cache_data.clear()
    df1, df2 = get_simple_inventory()
    st.dataframe(df1, hide_index=True)
    st.dataframe(df2, hide_index=True)
    st.markdown('---')

with tabs[2]:
    inventory_ws, _ = get_daily_worksheets()
    st.markdown('<h2 style="color:#db2828;">➖ Remove Order</h2>', unsafe_allow_html=True)
    remove_product = st.selectbox("Select Product to Remove", ["Buko Juice", "Buko Shake", "Pizza"], key="remove_product")
    if remove_product != "Pizza":
        remove_packaging = st.selectbox("Select Packaging", ["Cup", "Bottle"], key="remove_packaging")
        remove_size = st.selectbox("Select Size", ["Small", "Medium", "Large"], key="remove_size")
        remove_pizza_type = None
    else:
        remove_packaging = "Box"
        remove_pizza_type = st.selectbox(
            "Select Pizza Flavor to Remove",
            ["Supreme", "Hawaiian", "Pepperoni", "Ham & Cheese", "Shawarma"],
            key="remove_pizza_type"
        )
        if remove_pizza_type == "Supreme":
            remove_size = "Supreme"
        else:
            remove_size = remove_pizza_type
    remove_qty = st.number_input("Enter Quantity to Remove", min_value=1, step=1, key="remove_qty")
    # Add cooldown to prevent rapid repeated calls
    if "remove_order_cooldown" not in st.session_state:
        st.session_state["remove_order_cooldown"] = 0
    import time
    now = time.time()
    cooldown_period = 3  # seconds
    cooldown_left = cooldown_period - (now - st.session_state["remove_order_cooldown"])
    button_disabled = cooldown_left > 0
    if st.button("Remove Order", key="remove_order_btn", disabled=button_disabled):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                if remove_product == "Pizza":
                    target_cell = cell_map[remove_product][remove_packaging][remove_size]
                else:
                    target_cell = cell_map[remove_product][remove_packaging][remove_size]
                current_value = inventory_ws.acell(target_cell).value
                current_value = int(current_value) if current_value and str(current_value).isdigit() else 0
                new_value = max(0, current_value - remove_qty)
                inventory_ws.update_acell(target_cell, new_value)
                st.success(f"Removed {remove_qty} from {remove_product} {remove_packaging} {remove_size if not remove_pizza_type else remove_pizza_type}.")
                st.session_state["remove_order_cooldown"] = time.time()
                st.cache_data.clear()
                st.rerun()
            except gspread.exceptions.APIError as e:
                import random
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                if attempt < max_retries - 1:
                    st.warning(f"Google Sheets API rate limit hit. Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                else:
                    st.error("Google Sheets API rate limit reached. Please wait a few seconds and try again.")
                    break
            except Exception as e:
                st.error(f"Error: {e}")
                break
    if cooldown_left > 0:
        st.info(f"Please wait {int(cooldown_left)+1}s before removing another order.")
    st.markdown('---')

with tabs[3]:
    st.markdown('<h2 style="color:#a333c8;">📊 Stocks Inventory</h2>', unsafe_allow_html=True)
    st.markdown('---')
    stocks = [
        "Milk", "Sugar", "buko", "S-Bottle", "M-Bottle", "L-Bottle", "S-Cup", "M-Cup", "L-Cup", "Dough", "Pizza sauce", "Ham", "Pepperoni", "Pineapple", "Beep/Bacon", "W Onion", "Bellpepper", "Mushroom", "Hot Sauce", "Catsup", "Beef Shawarma", "Pizza Cheese", "Mozza Cheese", "Pizza Box", "Ice", "Plastic Twine", "Tissue", "Spoon", "Straw", "Sando bag", "Carrier bag", "Siomai"
    ]
    start_row = 17  # Start one row below the title

    def fetch_stocks_table():
        # Connect and fetch all stocks data from Google Sheets
        creds_b64 = os.environ["GOOGLE_SERVICE_ACCOUNT_B64"]
        creds_bytes = base64.b64decode(creds_b64)
        creds_dict = json.loads(creds_bytes.decode("utf-8"))
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        today_str = datetime.now(pytz.timezone("Asia/Manila")).strftime("%Y-%m-%d")
        inventory_title = f"MighteeMart1_{today_str}"
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        inventory_ws = spreadsheet.worksheet(inventory_title)
        beg_bal_range = inventory_ws.get(f"G{start_row}:G{start_row+len(stocks)-1}")
        qty_in_range = inventory_ws.get(f"I{start_row}:I{start_row+len(stocks)-1}")
        end_bal_range = inventory_ws.get(f"M{start_row}:M{start_row+len(stocks)-1}")
        table_data = []
        for i, stock in enumerate(stocks):
            beg_bal = beg_bal_range[i][0] if i < len(beg_bal_range) and beg_bal_range[i] else None
            qty_in = qty_in_range[i][0] if i < len(qty_in_range) and qty_in_range[i] else None
            end_bal = end_bal_range[i][0] if i < len(end_bal_range) and end_bal_range[i] else None
            beg_bal = float(beg_bal) if beg_bal not in (None, "") else None
            qty_in = float(qty_in) if qty_in not in (None, "") else None
            end_bal = float(end_bal) if end_bal not in (None, "") else None
            table_data.append({
                "Stock": stock,
                "Beg. Bal": beg_bal,
                "Qty. In": qty_in,
                "Ending Bal": end_bal
            })
        return table_data

    # Use session state to cache table data
    if "stocks_table_data" not in st.session_state:
        st.session_state["stocks_table_data"] = fetch_stocks_table()

    if st.button("Refresh Inventory", key="refresh_stocks_btn"):
        st.session_state["stocks_table_data"] = fetch_stocks_table()
        st.success("Stocks inventory refreshed from Google Sheets.")

    df = pd.DataFrame(st.session_state["stocks_table_data"])
    edited_df = st.data_editor(
        df,
        column_config={
            "Stock": st.column_config.TextColumn(disabled=True),
            "Beg. Bal": st.column_config.NumberColumn(required=False),
            "Qty. In": st.column_config.NumberColumn(required=False),
            "Ending Bal": st.column_config.NumberColumn(required=False)
        },
        hide_index=True,
        num_rows="fixed"
    )
    if st.button("Save Stocks", key="save_stocks_btn"):
        try:
            import pandas as pd  # Ensure pd is available in this scope
            # Connect to Google Sheets and get today's worksheet only when saving
            creds_b64 = os.environ["GOOGLE_SERVICE_ACCOUNT_B64"]
            creds_bytes = base64.b64decode(creds_b64)
            creds_dict = json.loads(creds_bytes.decode("utf-8"))
            scope = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            client = gspread.authorize(creds)
            today_str = datetime.now(pytz.timezone("Asia/Manila")).strftime("%Y-%m-%d")
            inventory_title = f"MighteeMart1_{today_str}"
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            inventory_ws = spreadsheet.worksheet(inventory_title)
            # Fetch all current values in a single batch to minimize API calls
            beg_bal_range = inventory_ws.get(f"G{start_row}:G{start_row+len(stocks)-1}")
            qty_in_range = inventory_ws.get(f"I{start_row}:I{start_row+len(stocks)-1}")
            end_bal_range = inventory_ws.get(f"M{start_row}:M{start_row+len(stocks)-1}")
            beg_bal_updates = []
            qty_in_updates = []
            end_bal_updates = []
            for i, row in edited_df.iterrows():
                beg_val = row["Beg. Bal"]
                qty_val = row["Qty. In"]
                end_val = row["Ending Bal"]
                # Defensive: check if the row exists and has a value, else use None
                beg_old = beg_bal_range[i][0] if i < len(beg_bal_range) and beg_bal_range[i] and len(beg_bal_range[i]) > 0 else None
                qty_old = qty_in_range[i][0] if i < len(qty_in_range) and qty_in_range[i] and len(qty_in_range[i]) > 0 else None
                end_old = end_bal_range[i][0] if i < len(end_bal_range) and end_bal_range[i] and len(end_bal_range[i]) > 0 else None
                if pd.isna(beg_val) or beg_val == "":
                    beg_bal_updates.append([beg_old])
                else:
                    beg_bal_updates.append([int(beg_val)])
                if pd.isna(qty_val) or qty_val == "":
                    qty_in_updates.append([qty_old])
                else:
                    qty_in_updates.append([int(qty_val)])
                if pd.isna(end_val) or end_val == "":
                    end_bal_updates.append([end_old])
                else:
                    end_bal_updates.append([int(end_val)])
            inventory_ws.update(f"G{start_row}:G{start_row+len(stocks)-1}", beg_bal_updates)
            inventory_ws.update(f"I{start_row}:I{start_row+len(stocks)-1}", qty_in_updates)
            inventory_ws.update(f"M{start_row}:M{start_row+len(stocks)-1}", end_bal_updates)
            # Update session state cache after saving
            st.session_state["stocks_table_data"] = fetch_stocks_table()
            st.success("Stocks updated successfully!")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Error updating stocks: {e}")
    st.markdown('---')

# --- Place this at the very end of the script ---
# st.subheader("Current Inventory")
# if st.button("Refresh Inventory"):
#     st.cache_data.clear()
# df1, df2 = get_simple_inventory()
# st.dataframe(df1, hide_index=True)
# st.dataframe(df2, hide_index=True)

# Add custom CSS for green and red buttons by button order and text
st.markdown("""
    <style>
    /* Green for Add to Order and Submit Order (first two buttons in the form) */
    div.stButton > button {
        background-color: #21ba45 !important;
        color: white !important;
        border: none !important;
        box-shadow: none !important;
    }
    /* Red for X remove buttons (by button text) */
    div.stButton > button:has(span:contains('X')) {
        background-color: #db2828 !important;
        color: white !important;
        border: none !important;
        font-weight: bold;
        box-shadow: none !important;
        width: 2.2em !important;
        height: 2.2em !important;
        padding: 0 !important;
        border-radius: 6px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: auto !important;
    }
    /* Center the X button in its column */
    div[data-testid="column"] div.stButton {
        display: flex;
        justify-content: center;
        align-items: center;
    }
    </style>
""", unsafe_allow_html=True)