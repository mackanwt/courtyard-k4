import base64
import json
import mimetypes
import os
from datetime import date, datetime
import pandas as pd
import requests
import streamlit as st
from github import Github

# ==========================================
# 0. SIDINSTÄLLNINGAR & PIKACHU / LIGHTNING CSS
# ==========================================
st.set_page_config(
    page_title="Courtyard K4-Räknare | Pokémon Edition",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Injektera anpassad CSS med Pokémon-font och sprites-banner
st.markdown("""
<style>
    @import url('https://fonts.cdnfonts.com/css/pokemon-solid');

    /* Grundläggande mörk bakgrund */
    .main {
        background-color: #0E1117;
    }

    /* Pokémon Logo Font Styling (Röd Ruta) */
    .pokemon-font {
        font-family: 'Pokemon Solid', sans-serif;
        color: #FFDE00 !important;
        -webkit-text-stroke: 2px #3B4CCA;
        font-size: 3rem;
        letter-spacing: 3px;
        margin: 0;
        line-height: 1.1;
        text-shadow: 3px 3px 0px #1D2C5E;
    }

    /* Bannerlayout för Header & Sprites (Grön Ruta) */
    .pokemon-banner {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 20px;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid #2D3748;
    }

    .pokemon-sprites {
        display: flex;
        align-items: center;
        gap: 12px;
        background: rgba(26, 29, 36, 0.6);
        padding: 8px 16px;
        border-radius: 16px;
        border: 1px solid #3A3D45;
    }

    .pokemon-sprites img {
        height: 70px;
        width: auto;
        filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5));
        transition: transform 0.2s ease-in-out;
    }

    .pokemon-sprites img:hover {
        transform: scale(1.25) translateY(-5px);
    }
    
    /* Pikachu-gul Accentfärg på Underrubriker */
    h1, h2, h3 {
        color: #FFDE00 !important;
        font-family: 'Trebuchet MS', sans-serif;
    }

    /* Metric-boxar med elektrisk glöd vid hover */
    div[data-testid="stMetric"] {
        background-color: #1A1D24;
        border: 1px solid #3A3D45;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        transition: all 0.25s ease-in-out;
    }
    div[data-testid="stMetric"]:hover {
        border-color: #FFDE00;
        box-shadow: 0 0 12px rgba(255, 222, 0, 0.35);
        transform: translateY(-2px);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #A0AEC0 !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700;
        color: #FFFFFF !important;
    }

    /* Flikar med Pikachu-gul markering */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #14171F;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid #2D3748;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        border-radius: 8px;
        color: #A0AEC0;
        font-weight: 600;
        padding: 0px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFDE00 !important;
        color: #000000 !important;
        font-weight: 700;
        box-shadow: 0 0 10px rgba(255, 222, 0, 0.4);
    }

    /* Elektriska Knappar (Primary) */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #FFDE00 0%, #E6B800 100%) !important;
        color: #000000 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 10px rgba(255, 222, 0, 0.3) !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 0 15px rgba(255, 222, 0, 0.6) !important;
        transform: scale(1.01);
    }

    /* Elektrisk Avdelare */
    hr {
        margin: 2rem 0 !important;
        border-color: #3A3D45 !important;
    }

    /* Pikachu Highlight-kort för Nettovinst */
    .pikachu-card {
        background: linear-gradient(135deg, #2A2400 0%, #1A1700 100%);
        padding: 22px;
        border-radius: 14px;
        border: 2px solid #FFDE00;
        margin-bottom: 20px;
        box-shadow: 0 0 18px rgba(255, 222, 0, 0.25);
        color: #FFFDF0;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. GITHUB DATAHANTERING
# ==========================================
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
    except Exception:
        return default_value, None

def save_json_to_github(filename, data, sha, commit_message="Uppdatera data"):
    try:
        repo = get_github_repo()
        json_str = json.dumps(data, indent=4, ensure_ascii=False)
        if sha:
            repo.update_file(filename, commit_message, json_str, sha)
        else:
            repo.create_file(filename, commit_message, json_str)
        st.cache_data.clear()
        st.cache_resource.clear()
        return True
    except Exception as e:
        st.error(f"Kunde inte spara till GitHub: {e}")
        return False

DATA_FILE = "courtyard_cards_history.json"
WITHDRAWALS_FILE = "courtyard_withdrawals_history.json"

cards, cards_sha = load_json_from_github(DATA_FILE, [])
withdrawals, withdrawals_sha = load_json_from_github(WITHDRAWALS_FILE, [])

# ==========================================
# 2. HJÄLPFUNKTIONER
# ==========================================
def format_image_source(img_input):
    if not img_input:
        return ""
    clean_path = str(img_input).strip().strip('"').strip("'")
    if clean_path.startswith("http://") or clean_path.startswith("https://") or clean_path.startswith("data:image/"):
        return clean_path
    if os.path.exists(clean_path) and os.path.isfile(clean_path):
        try:
            mime_type, _ = mimetypes.guess_type(clean_path)
            if not mime_type:
                mime_type = "image/png"
            with open(clean_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return f"data:{mime_type};base64,{encoded_string}"
        except Exception:
            return clean_path
    return clean_path

@st.cache_data(ttl=86400)
def get_usd_sek_rate(fetch_date):
    if not fetch_date or pd.isna(fetch_date) or str(fetch_date).strip() in ["", "None", "Nat"]:
        return 10.50
    if isinstance(fetch_date, (datetime, date)):
        date_str = fetch_date.strftime("%Y-%m-%d")
    else:
        date_str = str(fetch_date).strip()

    try:
        url = f"https://api.frankfurter.app/{date_str}?from=USD&to=SEK"
        res = requests.get(url, timeout=5).json()
        if "rates" in res and "SEK" in res["rates"]:
            return round(res["rates"]["SEK"], 4)
    except Exception:
        pass
    
    try:
        url_alt = f"https://open.er-api.com/v6/historical/{date_str}"
        res_alt = requests.get(url_alt, timeout=5).json()
        if res_alt.get("result") == "success" and "SEK" in res_alt.get("rates", {}):
            return round(res_alt["rates"]["SEK"], 4)
    except Exception:
        pass

    return 10.50

# ==========================================
# 3. HEADER BANNER MED POKÉMON-FONT & SPRITES
# ==========================================
st.markdown("""
<div class="pokemon-banner">
    <div>
        <h1 class="pokemon-font">Pokémon</h1>
        <h2 style="font-size: 1.8rem; margin: 0; color: #FFDE00 !important;">⚡ Courtyard K4-Räknare ⚡</h2>
    </div>
    <div class="pokemon-sprites">
        <img src="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/172.png" alt="Pichu" title="Pichu">
        <img src="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png" alt="Pikachu" title="Pikachu">
        <img src="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/26.png" alt="Raichu" title="Raichu">
        <img src="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/10100.png" alt="Alolan Raichu" title="Alolan Raichu">
        <img src="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/778.png" alt="Mimikyu" title="Mimikyu">
    </div>
</div>
""", unsafe_allow_html=True)

st.caption("Pikachu-powered spårning av dina Pokémon- och samlarkort för Skatteverket.")

tab1, tab2, tab3 = st.tabs(["📊 Översikt & Skatt", "➕ Registrera Nytt Köp", "🏧 Registrera Uttag"])

shared_column_config = {
    "Bild": st.column_config.ImageColumn("Bild", width="small"),
    "Länk": st.column_config.LinkColumn("Länk", display_text="Öppna 🔗", width="small"),
    "Name": st.column_config.TextColumn("Kortnamn", width="medium"),
    "Buy_Date": st.column_config.DateColumn("Köpdatum", width="small"),
    "Buy_USD": st.column_config.NumberColumn("Köp ($)", format="$%.2f", width="small"),
    "Buy_Currency_Rate": st.column_config.NumberColumn("Köp Kurs", format="%.2f", width="small"),
    "Buy_SEK": st.column_config.NumberColumn("Köp (SEK)", format="%.2f kr", width="small"),
    "Sell_Date": st.column_config.DateColumn("Säljdatum", width="small"),
    "Sell_USD": st.column_config.NumberColumn("Sälj ($)", format="$%.2f", width="small"),
    "Sell_Currency_Rate": st.column_config.NumberColumn("Sälj Kurs", format="%.2f", width="small"),
    "Sell_SEK": st.column_config.NumberColumn("Sälj (SEK)", format="%.2f kr", width="small"),
    "Status": st.column_config.TextColumn("Status", width="small"),
}

cols_order = ["Bild", "Länk", "Name", "Buy_Date", "Buy_USD", "Buy_Currency_Rate", "Buy_SEK", "Sell_Date", "Sell_USD", "Sell_Currency_Rate", "Sell_SEK", "Status"]

# --- FLIK 2: REGISTRERA NYTT KÖP ---
with tab2:
    st.subheader("⚡ Lägg till nytt kort i samlingen")
    
    col_a, col_b = st.columns(2)
    with col_a:
        b_name = st.text_input("Kort / Paket Namn", placeholder="t.ex. Pikachu Special Art Rare")
        b_date = st.date_input("Köpdatum", value=date.today())
        
        auto_rate = get_usd_sek_rate(b_date)
        b_rate = st.number_input("USD/SEK Kurs (Hämtad från ECB)", value=auto_rate, step=0.01)
        b_usd = st.number_input("Inköpspris (USD)", min_value=0.0, step=1.0, value=50.0)
        
        st.markdown(f"💳 **Beräknat inköpspris:** `{round(b_usd * b_rate, 2)} SEK`")

    with col_b:
        card_url = st.text_input("Sida på Courtyard (Valfritt)", placeholder="https://courtyard.io/card/...")
        st.write("🖼️ **Bild på kortet:**")
        local_path = st.text_input(
            "Klistra in bild-URL", 
            placeholder="https://... eller D:\\Mapp\\bild.png"
        )

    st.write("")
    if st.button("⚡ Spara Köp i Samlingen", type="primary", use_container_width=True):
        if b_name and b_usd > 0:
            img_data = format_image_source(local_path) if local_path else ""

            new_card = {
                "Bild": img_data,
                "Länk": card_url if card_url else "",
                "Name": b_name,
                "Buy_Date": str(b_date),
                "Buy_USD": float(b_usd),
                "Buy_Currency_Rate": float(b_rate),
                "Buy_SEK": round(float(b_usd) * float(b_rate), 2),
                "Sell_Date": "",
                "Sell_USD": None,
                "Sell_Currency_Rate": None,
                "Sell_SEK": None,
                "Status": "Äger kvar"
            }
            cards.append(new_card)
            if save_json_to_github(DATA_FILE, cards, cards_sha, f"Lade till köp: {b_name}"):
                st.success(f"⚡ Lade till {b_name}!")
                st.rerun()
        else:
            st.error("Fyll i namn och inköpspris.")

# --- FLIK 3: REGISTRERA UTTAG TILL BANK ---
with tab3:
    st.subheader("🏧 Registrera Uttag till Bank")
    st.caption("Fyll i när du tar ut köpta USD/USDC från Courtyard till ditt svenska bankkonto.")
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        u_date = st.date_input("Uttagsdatum", value=date.today())
        u_usd = st.number_input("Antal USD du tog ut ($)", min_value=0.01, step=10.0, value=50.0)
    with col_u2:
        u_sek = st.number_input("Totalt erhållit belopp på banken (SEK)", min_value=0.0, step=100.0, value=500.0)
        
    st.write("")
    if st.button("⚡ Spara Uttags-transaktion", type="primary", use_container_width=True):
        if u_usd > 0 and u_sek > 0:
            new_withdrawal = {
                "Datum": str(u_date),
                "USD": float(u_usd),
                "Erhållen_SEK": float(u_sek)
            }
            withdrawals.append(new_withdrawal)
            if save_json_to_github(WITHDRAWALS_FILE, withdrawals, withdrawals_sha, "Lade till uttag"):
                st.success("✅ Uttag registrerat!")
                st.rerun()
        else:
            st.error("Ange ett giltigt USD-belopp och erhållit SEK-belopp.")

    if withdrawals:
        st.divider()
        st.subheader("📜 Registrerade Bankuttag")
        df_w = pd.DataFrame(withdrawals)
        st.dataframe(df_w, use_container_width=True)

# --- FLIK 1: ÖVERSIKT & SKATT ---
with tab1:
    if cards:
        if "edit_mode" not in st.session_state:
            st.session_state.edit_mode = False

        col_head, col_btn = st.columns([4, 1])
        with col_head:
            st.subheader("📜 Samling & Innehav")
        with col_btn:
            if not st.session_state.edit_mode:
                if st.button("✏️ Redigera Tabell", use_container_width=True):
                    st.session_state.edit_mode = True
                    st.rerun()

        cleaned_cards = []
        for c in cards:
            c_copy = c.copy()
            if c_copy.get("Bild"):
                c_copy["Bild"] = format_image_source(c_copy["Bild"])
            cleaned_cards.append(c_copy)

        df = pd.DataFrame(cleaned_cards)

        for c in cols_order:
            if c not in df.columns:
                df[c] = None
        
        df = df[cols_order]

        df["Buy_Date"] = pd.to_datetime(df["Buy_Date"], errors="coerce").dt.date
        df["Sell_Date"] = pd.to_datetime(df["Sell_Date"], errors="coerce").dt.date

        if st.session_state.edit_mode:
            st.info("💡 **Redigeringsläge:** Ändra värden fritt nedan. Tryck på **'⚡ Spara alla ändringar'** när du är klar.")
            
            with st.form("table_edit_form"):
                editable_config = {
                    "Bild": st.column_config.TextColumn("Bild URL / Sökväg", width="medium"),
                    "Länk": st.column_config.TextColumn("Courtyard Länk", width="medium"),
                    "Name": st.column_config.TextColumn("Kortnamn", width="medium"),
                    "Buy_Date": st.column_config.DateColumn("Köpdatum", width="small"),
                    "Buy_USD": st.column_config.NumberColumn("Köp ($)", format="$%.2f", width="small"),
                    "Buy_Currency_Rate": st.column_config.NumberColumn("Köp Kurs", format="%.2f", width="small"),
                    "Buy_SEK": st.column_config.NumberColumn("Köp (SEK)", format="%.2f kr", width="small"),
                    "Sell_Date": st.column_config.DateColumn("Säljdatum", width="small"),
                    "Sell_USD": st.column_config.NumberColumn("Sälj ($)", format="$%.2f", width="small"),
                    "Sell_Currency_Rate": st.column_config.NumberColumn("Sälj Kurs", format="%.2f", width="small"),
                    "Sell_SEK": st.column_config.NumberColumn("Sälj (SEK)", format="%.2f kr", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                }

                edited_df = st.data_editor(
                    df,
                    column_config=editable_config,
                    column_order=cols_order,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="table_editor_form"
                )

                submit_save = st.form_submit_button("⚡ Spara alla ändringar", type="primary", use_container_width=True)

            if submit_save:
                with st.spinner("Oppdaterar valutakurser och sparar till GitHub..."):
                    updated_data = edited_df.to_dict(orient="records")
                    for c in updated_data:
                        try:
                            if c.get("Bild"):
                                c["Bild"] = format_image_source(c["Bild"])

                            if pd.notna(c.get("Buy_Date")) and c.get("Buy_Date"):
                                c["Buy_Date"] = str(c["Buy_Date"])
                                c["Buy_Currency_Rate"] = get_usd_sek_rate(c["Buy_Date"])
                            else:
                                c["Buy_Date"] = ""

                            if c.get("Buy_USD") is not None and c.get("Buy_Currency_Rate"):
                                c["Buy_SEK"] = round(float(c["Buy_USD"]) * float(c["Buy_Currency_Rate"]), 2)
                            
                            if c.get("Sell_USD") is not None and str(c.get("Sell_USD")).strip() not in ["", "None"] and float(c.get("Sell_USD") or 0) > 0:
                                if pd.notna(c.get("Sell_Date")) and c.get("Sell_Date"):
                                    c["Sell_Date"] = str(c["Sell_Date"])
                                    c["Sell_Currency_Rate"] = get_usd_sek_rate(c["Sell_Date"])
                                else:
                                    c["Sell_Date"] = ""
                                    c["Sell_Currency_Rate"] = c.get("Sell_Currency_Rate") or 10.50
                                    
                                rate = float(c["Sell_Currency_Rate"])
                                c["Sell_SEK"] = round(float(c["Sell_USD"]) * rate, 2)
                                c["Status"] = "Såld"
                            else:
                                c["Sell_Date"] = ""
                                c["Sell_USD"] = None
                                c["Sell_Currency_Rate"] = None
                                c["Sell_SEK"] = None
                                c["Status"] = "Äger kvar"
                        except Exception:
                            pass

                    save_json_to_github(DATA_FILE, updated_data, cards_sha, "Manuell redigering i tabell")
                    st.session_state.edit_mode = False
                    st.success("Ändringarna har sparats!")
                    st.rerun()

            if st.button("❌ Avbryt redigering utan att spara"):
                st.session_state.edit_mode = False
                st.rerun()

        else:
            for idx, row in df.iterrows():
                col_del, col_data = st.columns([0.3, 9.7])
                with col_del:
                    if st.button("🗑️", key=f"del_{idx}", help="Radera rad"):
                        cards.pop(idx)
                        if save_json_to_github(DATA_FILE, cards, cards_sha, f"Tog bort rad {idx}"):
                            st.rerun()
                with col_data:
                    row_df = pd.DataFrame([row])
                    st.dataframe(
                        row_df,
                        column_config=shared_column_config,
                        column_order=cols_order,
                        hide_index=True,
                        use_container_width=True
                    )

        # --- A. KORT-SKATTEBERÄKNING ---
        total_gains_sek = 0.0
        total_losses_sek = 0.0
        total_sell_sek = 0.0
        total_buy_sek = 0.0
        sold_cards_count = 0

        for c in cards:
            if c.get("Status") == "Såld":
                try:
                    buy_sek = float(c.get("Buy_SEK", 0) or 0)
                    sell_sek = float(c.get("Sell_SEK", 0) or 0)
                    diff = sell_sek - buy_sek
                    
                    total_sell_sek += sell_sek
                    total_buy_sek += buy_sek
                    sold_cards_count += 1
                    
                    if diff >= 0:
                        total_gains_sek += diff
                    else:
                        total_losses_sek += abs(diff)
                except (ValueError, TypeError):
                    continue

        k4_card_export_rows = []
        if sold_cards_count > 0:
            k4_card_export_rows.append({
                "Antal / Belopp i utländsk valuta": sold_cards_count,
                "Beteckning / Valutakod": "Courtyard-kort",
                "Försäljningspris (SEK)": round(total_sell_sek),
                "Omkostnadsbelopp (SEK)": round(total_buy_sek),
                "Vinst (SEK)": round(total_gains_sek),
                "Förlust (SEK)": round(total_losses_sek)
            })

        deductible_loss = total_losses_sek * 0.70
        net_taxable_base = max(0.0, total_gains_sek - deductible_loss)
        card_tax = net_taxable_base * 0.30

        st.divider()
        st.markdown("### 🏷️ Skatt på Kortförsäljning (Bilaga K4 - Avsnitt D)")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Totalt Vinster", f"{total_gains_sek:,.2f} kr")
        c2.metric("Totalt Förluster", f"{total_losses_sek:,.2f} kr")
        c3.metric("Avdragsgill förlust (70%)", f"{deductible_loss:,.2f} kr")
        c4.metric("Kortskatt (30%)", f"{card_tax:,.2f} kr")

        # --- B. GNS-PLÅNBOK & VALUTASKATT ---
        wallet_events = []
        for c in cards:
            if c.get("Status") == "Såld" and c.get("Sell_Date") and c.get("Sell_USD"):
                try:
                    wallet_events.append({
                        "Datum": str(c["Sell_Date"]),
                        "Typ": "INFLÖDE",
                        "Beskrivning": f"Sålt: {c.get('Name', 'Kort')}",
                        "USD": float(c["Sell_USD"]),
                        "SEK": float(c.get("Sell_SEK", 0) or 0)
                    })
                except Exception:
                    pass

        for w in withdrawals:
            try:
                wallet_events.append({
                    "Datum": str(w["Datum"]),
                    "Typ": "UTFLÖDE",
                    "Beskrivning": "Uttag till bank",
                    "USD": float(w["USD"]),
                    "SEK": float(w["Erhållen_SEK"])
                })
            except Exception:
                pass

        wallet_events = sorted(
            wallet_events, 
            key=lambda x: (pd.to_datetime(x["Datum"]), 0 if x["Typ"] == "INFLÖDE" else 1)
        )

        usd_saldo = 0.0
        sek_omkostnad = 0.0
        valuta_vinster_sek = 0.0
        valuta_forluster_sek = 0.0
        total_valuta_usd = 0.0
        total_valuta_sell_sek = 0.0
        total_valuta_omkostnad_sek = 0.0

        for ev in wallet_events:
            if ev["Typ"] == "INFLÖDE":
                usd_saldo += ev["USD"]
                sek_omkostnad += ev["SEK"]
            elif ev["Typ"] == "UTFLÖDE":
                if usd_saldo > 0:
                    snittkurs = sek_omkostnad / usd_saldo
                    omkostnad_uttag = ev["USD"] * snittkurs
                    diff_valuta = ev["SEK"] - omkostnad_uttag
                    
                    total_valuta_usd += ev["USD"]
                    total_valuta_sell_sek += ev["SEK"]
                    total_valuta_omkostnad_sek += omkostnad_uttag

                    if diff_valuta >= 0:
                        valuta_vinster_sek += diff_valuta
                    else:
                        valuta_forluster_sek += abs(diff_valuta)

                    usd_saldo -= ev["USD"]
                    sek_omkostnad -= omkostnad_uttag

        k4_valuta_export_rows = []
        if total_valuta_usd > 0:
            k4_valuta_export_rows.append({
                "Antal / Belopp i USD": round(total_valuta_usd),
                "Beteckning / Valutakod": "USD",
                "Försäljningspris (SEK)": round(total_valuta_sell_sek),
                "Omkostnadsbelopp (SEK)": round(total_valuta_omkostnad_sek),
                "Vinst (SEK)": round(valuta_vinster_sek),
                "Förlust (SEK)": round(valuta_forluster_sek)
            })

        nuvarande_snittkurs = (sek_omkostnad / usd_saldo) if usd_saldo > 0 else 0.0

        valuta_deductible_loss = valuta_forluster_sek * 0.70
        valuta_taxable_base = max(0.0, valuta_vinster_sek - valuta_deductible_loss)
        valuta_tax = valuta_taxable_base * 0.30

        total_skatt = card_tax + valuta_tax
        brutto_resultat = (total_gains_sek - total_losses_sek) + (valuta_vinster_sek - valuta_forluster_sek)
        netto_vinst = brutto_resultat - total_skatt

        # --- C. TOTAL EKONOMI-KORT (PIKACHU STYLING) ---
        st.divider()
        
        st.markdown(f"""
        <div class="pikachu-card">
            <h2 style="margin:0; font-size:1.6rem; color:#FFDE00;">⚡ REN NETTOVINST: {netto_vinst:,.2f} SEK</h2>
            <p style="margin:6px 0 0 0; opacity:0.9;">Ditt faktiska resultat i fickan efter att all skatt på kort och valutakursförändringar är beräknad.</p>
        </div>
        """, unsafe_allow_html=True)

        n1, n2, n3 = st.columns(3)
        n1.metric("Netto Kortresultat", f"{(total_gains_sek - total_losses_sek):,.2f} kr")
        n2.metric("Netto Valutaresultat", f"{(valuta_vinster_sek - valuta_forluster_sek):,.2f} kr")
        n3.metric("Total Beräknad Skatt", f"-{total_skatt:,.2f} kr", delta_color="inverse")

        st.write("")
        p1, p2, p3 = st.columns(3)
        p1.metric("USD kvar i Courtyard Wallet", f"${usd_saldo:,.2f}")
        p2.metric("Inneliggande SEK-Omkostnad", f"{sek_omkostnad:,.2f} kr")
        p3.metric("Aktiv Snittkurs (GNS)", f"{nuvarande_snittkurs:.4f} kr/$")

        # --- D. DEKLARATIONSHJÄLP ---
        st.divider()
        st.subheader("📋 Siffror för Inkomstdeklarationen")
        st.caption("Färdigavrundade belopp att fylla i hos Skatteverket:")

        m_k4_vinst_kort = round(total_gains_sek)
        m_k4_forlust_kort = round(total_losses_sek)
        m_k4_vinst_valuta = round(valuta_vinster_sek)
        m_k4_forlust_valuta = round(valuta_forluster_sek)

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Punkt 7.5 (Kortvinst)", f"{m_k4_vinst_kort} kr")
        s2.metric("Punkt 8.4 (Kortförlust)", f"{m_k4_forlust_kort} kr")
        s3.metric("Punkt 7.2 (Valutavinst)", f"{m_k4_vinst_valuta} kr")
        s4.metric("Punkt 8.1 (Valutaförlust)", f"{m_k4_forlust_valuta} kr")

        with st.expander("📄 Visa exakta rader för K4-blanketten"):
            st.markdown("#### **Avsnitt D – Övriga tillgångar (Kort)**")
            if k4_card_export_rows:
                st.dataframe(pd.DataFrame(k4_card_export_rows), use_container_width=True)
            else:
                st.caption("Inga sålda kort registrerade ännu.")

            st.markdown("#### **Avsnitt C – Valuta (Uttag till bank)**")
            if k4_valuta_export_rows:
                st.dataframe(pd.DataFrame(k4_valuta_export_rows), use_container_width=True)
            else:
                st.caption("Inga bankuttag registrerade ännu.")

    else:
        st.info("Inga kort registrerade ännu. Gå till fliken 'Registrera Nytt Köp' för att börja!")
