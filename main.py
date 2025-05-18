import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

st.set_page_config(page_title="Finance App", page_icon="💰", layout="wide")

# Streamlit has states, everytime do anything, 
# We're going to lose anything that we dont explicitly store in state

category_file= "categories.json"
log_file= "log.json"

# Creating new state, Categories
# By default, we have a dictionary with one key "Uncategorized" and an empty list
if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": []
    }

if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)


if "matched" not in st.session_state:
    st.session_state.matched = {cat: [] for cat in st.session_state.categories}
elif os.path.exists(log_file):
    with open(log_file, "r") as f:
        try:
            st.session_state.matched = json.load(f)
        except json.JSONDecodeError:
            st.session_state.matched = {cat: [] for cat in st.session_state.categories}

def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

def save_log():
    with open(log_file, "w") as f:
        json.dump(st.session_state.matched, f)

def categorize_transaction(df):

    if "Details" not in df.columns:
        st.warning("The uploaded file does not contain a 'Details' column.")
        return df
    
    # Reinitialize matched properly with all categories present
    st.session_state.matched = {cat: [] for cat in st.session_state.categories}

    # new category col with default val
    df["Category"]= "Uncategorized"

    for category, keywords in st.session_state.categories.items():

        # skip
        if category == "Uncategorized" or not keywords:
            continue

        lowered_keywords= [keyword.strip().lower() for keyword in keywords]

        # Match keywords for each category
        for idx, row in df.iterrows():
            detail= row["Details"].lower().strip()
            if detail in lowered_keywords:
                df.loc[idx, "Category"]= category
                
                # Log the matched detail (not in keyword list)
                st.session_state.matched[category].append(detail)
                # break   # Gets the first match

    save_log()
    return df

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        st.success(f"Keyword '{keyword}' added to category '{category}'")
        return True
    return False


def load_transaction(file):
    try:
        df = pd.read_csv(file)

        # Data Cleaning
        df.columns= [col.strip() for col in df.columns]
        df["Amount"]= df["Amount"].str.replace(",", "").astype(float)
        df["Date"]= pd.to_datetime(df["Date"], format= "%d %b %Y")

        st.write(df.head(10))
        return categorize_transaction(df)
    except Exception as e:
        st.error(f"Error processing the file : {str(e)}")
        return None

def main():
    st.title("Financial Dashboard")

    uploaded_file = st.file_uploader("Upload your transcation data (CSV)", type=["csv"])

    if uploaded_file is not None:
        df = load_transaction(uploaded_file)

        if df is not None:
            # New DF only for debits and credits
            debits_df= df[df["Debit/Credit"]== "Debit"].copy()
            credits_df= df[df["Debit/Credit"]== "Credit"].copy()

             # Store DF in section storage for edited_df (so that it wont change the main df)
            st.session_state.debits_df= debits_df.copy() 

            tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])
            with tab1:
                new_category= st.text_input("Add a new category")
                add_button= st.button("Add Category")

                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category]= []
                        save_categories()
                        st.rerun()      # This will refresh the page and show the new category
                    else:
                        st.warning(f"Category '{new_category}' already exists!")

                st.subheader("Expenses (Debits)")

                edited_df= st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format= "DD/MM/YYYY"),
                        "Details": st.column_config.TextColumn("Details"),
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f $"),
                        "Category": st.column_config.SelectboxColumn("Category", options=list(st.session_state.categories.keys()))
                    },
                    hide_index=True,
                    use_container_width=True,
                    key= "category_editor",     # Just to identify the DF
                )

                save_button= st.button("Save Changes", type="primary")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        # if same pss
                        new_category= row["Category"]
                        if new_category == st.session_state.debits_df.loc[idx, "Category"]:
                            continue

                        details= row["Details"]
                        st.session_state.debits_df.loc[idx, "Category"]= new_category
                        add_keyword_to_category(new_category, details)

                # Expense Summary by Category
                st.subheader("Expense Summary by Category")
                category_totals= st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
                category_totals= category_totals.sort_values(by="Amount", ascending=False)

                st.dataframe(category_totals, column_config={
                    "Amount": st.column_config.NumberColumn("Amount", format="%.2f $"),
                }, use_container_width=True, hide_index=True)

                # Plotting
                fig = px.pie(category_totals, values='Amount', names='Category', title='Expenses by Category')
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader("Payments Summary")
                total_payments = credits_df["Amount"].sum()
                st.metric("Total Payments", f"{total_payments:,.2f} $")
                st.write(credits_df)



main()