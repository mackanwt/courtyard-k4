import json
import pandas as pd
import requests
import streamlit as st
from github import Github

st.set_page_config(
    page_title="Courtyard Skattehantering", page_icon="🎴", layout="wide"
)

# --- GITHUB INTEGRATION ---
def get_github_repo():
    token = st.secrets["GITHUB_TOKEN"]
    repo_name = st.secrets["GITHUB_REPO"]
    g = Github(token)
    return g.get_repo(repo_name)


def load_json_from_github(filename, default_value):
    try:
        repo = get_github_repo()
        file_content = repo.get_contents(filename)
        data = json.loads(file_content.decoded_content.decode("utf-8"))
        return data, file_content.sha
    except Exception as e:
        return default_value, None


def save_json_to_github(filename, data, sha, commit_message="Uppdatera data"):
    try:
        repo = get_github_repo()
        json_str = json.dumps(data, indent=4, ensure_ascii=False)
        if sha:
            repo.update_file(filename, commit_message, json_str, sha)
        else:
            repo.create_file(filename, commit_message, json_str)
        
        st.toast("✅ Sparat till GitHub!", icon="🎉")
        st.cache_data.clear()
        st.cache_resource.clear()
        return True
    except Exception as e:
        st.error(f"Kunde inte spara till GitHub: {e}")
        return False


# --- HÄMTA VALUTAKURS ---
@st.cache_data(ttl=3600)
def get_usd_sek_rate(date_str=None):
    try:
        url = (
            f"https://api.exchangerate.host/{date_str}?base=USD&symbols=SEK"
            if date_str
            else "https://api.exchangerate.host/latest?base=USD&symbols=SEK"
        )
        res = requests.get(url).json()
        if "rates" in res and "SEK" in res["rates"]:
            return float(res["rates"]["SEK"])
        return 10.5
    except Exception:
        return 10.5


# --- LÄS DATA FRÅN GITHUB ---
cards_data, cards_sha = load_json_from_github(
    "courtyard_cards_history.json", []
)
withdrawals_data, withdrawals_sha = load_json_from_github(
    "courtyard_withdrawals_history.json", []
)

st.title("🎴 Courtyard Skattehantering")

menu = st.sidebar.radio(
    "Navigering", ["Registrera Köp", "Registrera Försäljning", "Registrera Uttag", "Översikt & K4"]
)

# --- 1. REGISTRERA KÖP ---
if menu == "Registrera Köp":
    st.header("➕ Registrera Nytt Köp")

    with st.form("buy_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Kortnamn (t.ex. Charizard Base Set)")
            buy_date = st.date_input("Köpdatum")
            img_url = st.text_input("Bild-URL (Valfritt)")
        with col2:
            buy_usd = st.number_input(
                "Inköpspris (USD)", min_value=0.0, step=0.1
            )
            buy_link = st.text_input("Länk till köp/kort")

        rate = get_usd_sek_rate(str(buy_date))
        buy_sek = buy_usd * rate
        st.info(
            f"Beräknat inköpspris i SEK: **{buy_sek:.2f} SEK** (Kurs: {rate:.4f})"
        )

        submitted = st.form_submit_button("💾 Spara Köp")
        if submitted:
            if not name:
                st.error("Du måste fylla i ett kortnamn!")
            else:
                new_card = {
                    "Bild": img_url,
                    "Länk": buy_link,
                    "Name": name,
                    "Buy_Date": str(buy_date),
                    "Buy_USD": buy_usd,
                    "Buy_Currency_Rate": rate,
                    "Buy_SEK": buy_sek,
                    "Sell_Date": "",
                    "Sell_USD": None,
                    "Sell_Currency_Rate": None,
                    "Sell_SEK": None,
                    "Status": "Ägd",
                }
                cards_data.append(new_card)
                success = save_json_to_github(
                    "courtyard_cards_history.json",
                    cards_data,
                    cards_sha,
                    f"Lade till köp: {name}",
                )
                if success:
                    st.success(f"Kortet '{name}' har sparats!")
                    st.rerun()

# --- 2. REGISTRERA FÖRSÄLJNING ---
elif menu == "Registrera Försäljning":
    st.header("🏷️ Registrera Försäljning")

    owned_cards = [c for c in cards_data if c.get("Status") == "Ägd"]

    if not owned_cards:
        st.warning("Du har inga ägda kort registrerade att sälja.")
    else:
        card_names = [f"{c['Name']} (Köpt: {c['Buy_Date']})" for c in owned_cards]
        selected_idx = st.selectbox(
            "Välj kort att sälja", range(len(card_names)), format_func=lambda x: card_names[x]
        )
        selected_card = owned_cards[selected_idx]

        with st.form("sell_form"):
            sell_date = st.date_input("Försäljningsdatum")
            sell_usd = st.number_input(
                "Försäljningspris (USD)", min_value=0.0, step=0.1
            )

            sell_rate = get_usd_sek_rate(str(sell_date))
            sell_sek = sell_usd * sell_rate
            st.info(
                f"Beräknat försäljningspris i SEK: **{sell_sek:.2f} SEK** (Kurs: {sell_rate:.4f})"
            )

            submitted = st.form_submit_button("💰 Spara Försäljning")
            if submitted:
                for c in cards_data:
                    if (
                        c["Name"] == selected_card["Name"]
                        and c["Buy_Date"] == selected_card["Buy_Date"]
                        and c["Status"] == "Ägd"
                    ):
                        c["Sell_Date"] = str(sell_date)
                        c["Sell_USD"] = sell_usd
                        c["Sell_Currency_Rate"] = sell_rate
                        c["Sell_SEK"] = sell_sek
                        c["Status"] = "Såld"
                        break

                success = save_json_to_github(
                    "courtyard_cards_history.json",
                    cards_data,
                    cards_sha,
                    f"Sålde kort: {selected_card['Name']}",
                )
                if success:
                    st.success(f"Försäljningen av '{selected_card['Name']}' har sparats!")
                    st.rerun()

# --- 3. REGISTRERA UTTAG ---
elif menu == "Registrera Uttag":
    st.header("🏦 Registrera Bankuttag")

    with st.form("withdrawal_form"):
        w_date = st.date_input("Uttagsdatum")
        w_busd = st.number_input("Belopp (BUSD/USD)", min_value=0.0, step=0.1)
        w_rate = get_usd_sek_rate(str(w_date))
        w_sek = w_busd * w_rate

        st.info(f"Beräknat värde i SEK: **{w_sek:.2f} SEK**")

        submitted = st.form_submit_button("💾 Spara Uttag")
        if submitted:
            new_w = {
                "Datum": str(w_date),
                "BUSD": w_busd,
                "Valutakurs": w_rate,
                "SEK": w_sek,
            }
            withdrawals_data.append(new_w)
            success = save_json_to_github(
                "courtyard_withdrawals_history.json",
                withdrawals_data,
                withdrawals_sha,
                "Lade till uttag",
            )
            if success:
                st.success("Uttaget har sparats!")
                st.rerun()

    if withdrawals_data:
        st.subheader("Registrerade Uttag")
        st.dataframe(pd.DataFrame(withdrawals_data))

# --- 4. ÖVERSIKT & K4 ---
elif menu == "Översikt & K4":
    st.header("📊 Översikt & K4-underlag")

    if cards_data:
        df_cards = pd.DataFrame(cards_data)
        st.subheader("Alla Kort")
        st.dataframe(df_cards)
    else:
        st.info("Inga kort registrerade än.")
