import streamlit as st
import pandas as pd
import json
import os
import requests
import base64
import mimetypes
from datetime import datetime, date

st.set_page_config(page_title="Courtyard K4-Räknare", layout="wide")

# ==========================================
# MOBIL- OCH PWA-ANPASSNING
# ==========================================
st.markdown("""
    <head>
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="K4-Räknare">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <link rel="apple-touch-icon" href="https://em-content.zobj.net/source/apple/391/joker_1f0cf.png">
    </head>
""", unsafe_allow_html=True)

st.title("🃏 Courtyard K4-Räknare")
st.caption("Manuell och exakt spårning av dina kort och plånbok för Skatteverket.")

# ==========================================
# 1. FIL- & DATAHANTERING
# ==========================================
DATA_FILE = "courtyard_cards_history.json"
WITHDRAWALS_FILE = "courtyard_withdrawals_history.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

if not os.path.exists(WITHDRAWALS_FILE):
    with open(WITHDRAWALS_FILE, "w") as f:
        json.dump([], f)

with open(DATA_FILE, "r") as f:
    cards = json.load(f)

with open(WITHDRAWALS_FILE, "r") as f:
    withdrawals = json.load(f)

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
            return ""
            
    return ""

@st.cache_data(ttl=86400)
def get_usd_sek_rate(fetch_date):
    if not fetch_date or pd.isna(fetch_date):
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
# 3. FLIKSTRUKTUR & KOLUMNKONFIGURATION
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 Översikt & Skatteunderlag", "➕ Registrera Nytt Köp", "🏧 Registrera Uttag (Bank)"])

shared_column_config = {
    "Bild": st.column_config.ImageColumn("Bild", width="small"),
    "Länk": st.column_config.LinkColumn("Länk", display_text="Öppna 🔗", width="small"),
    "Name": st.column_config.TextColumn("Namn", width="medium"),
    "Buy_Date": st.column_config.DateColumn("Köpdatum", width="small"),
    "Buy_USD": st.column_config.NumberColumn("Köp USD", format="$%.2f", width="small"),
    "Buy_Currency_Rate": st.column_config.NumberColumn("Köp Kurs", format="%.2f", width="small"),
    "Buy_SEK": st.column_config.NumberColumn("Köp SEK", format="%.2f SEK", width="small"),
    "Sell_Date": st.column_config.DateColumn("Säljdatum", width="small"),
    "Sell_USD": st.column_config.NumberColumn("Sälj USD", format="$%.2f", width="small"),
    "Sell_Currency_Rate": st.column_config.NumberColumn("Sälj Kurs", format="%.2f", width="small"),
    "Sell_SEK": st.column_config.NumberColumn("Sälj SEK", format="%.2f SEK", width="small"),
    "Status": st.column_config.TextColumn("Status", width="small"),
}

# --- FLIK 2: REGISTRERA NYTT KÖP ---
with tab2:
    st.subheader("➕ Lägg till nytt kort/paket")
    
    col_a, col_b = st.columns(2)
    with col_a:
        b_name = st.text_input("Kort / Paket Namn", placeholder="t.ex. 2025 Pokémon Eevee EX")
        b_date = st.date_input("Köpdatum", value=date.today())
        
        auto_rate = get_usd_sek_rate(b_date)
        b_rate = st.number_input("USD/SEK Kurs (Automatisk från ECB)", value=auto_rate, step=0.01)
        b_usd = st.number_input("Inköpspris (USD)", min_value=0.0, step=1.0, value=50.0)
        st.write(f"**Beräknat inköpspris i SEK:** `{round(b_usd * b_rate, 2)} SEK`")

    with col_b:
        card_url = st.text_input("Sida på Courtyard (Valfritt)", placeholder="https://courtyard.io/card/...")
        
        st.write("**📷 Bild på kortet:**")
        local_path = st.text_input(
            "Klistra in sökvägen till bilden på datorn (Ctrl+V)", 
            placeholder=r"D:\Users\marcu\Desktop\Skärmbild 2026-08-09 215606.png"
        )
        image_url = st.text_input("Eller klistra in en Bild-URL (valfritt)", placeholder="https://...")

    if st.button("💾 Spara Köp", type="primary"):
        if b_name and b_usd > 0:
            img_data = ""
            
            if local_path:
                img_data = format_image_source(local_path)
            elif image_url:
                img_data = image_url

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
            with open(DATA_FILE, "w") as f:
                json.dump(cards, f, indent=4)
            st.success(f"Lade till {b_name}!")
            st.rerun()
        else:
            st.error("Fyll i namn och inköpspris.")

# --- FLIK 3: REGISTRERA UTTAG TILL BANK ---
with tab3:
    st.subheader("🏧 Registrera Uttag till Bank")
    st.caption("Registrera när du tar ut USD/USDC från Courtyard till ditt svenska bankkonto eller plånbok.")
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        u_date = st.date_input("Uttagsdatum", value=date.today())
        u_usd = st.number_input("Antal USD du tog ut ($)", min_value=0.01, step=10.0, value=50.0)
    with col_u2:
        u_sek = st.number_input("Totalt erhållit belopp på banken (SEK)", min_value=0.0, step=100.0, value=500.0)
        
    if st.button("💾 Spara Uttag", type="primary"):
        if u_usd > 0 and u_sek > 0:
            new_withdrawal = {
                "Datum": str(u_date),
                "USD": float(u_usd),
                "Erhållen_SEK": float(u_sek)
            }
            withdrawals.append(new_withdrawal)
            with open(WITHDRAWALS_FILE, "w") as f:
                json.dump(withdrawals, f, indent=4)
            st.success("Uttag registrerat!")
            st.rerun()
        else:
            st.error("Ange ett giltigt USD-belopp och erhållit SEK-belopp.")

    if withdrawals:
        st.divider()
        st.subheader("📜 Registrerade Uttag")
        df_w = pd.DataFrame(withdrawals)
        st.dataframe(df_w, use_container_width=True)

# --- FLIK 1: ÖVERSIKT & SKATT ---
with tab1:
    if cards:
        if "edit_mode" not in st.session_state:
            st.session_state.edit_mode = False

        col_head, col_btn = st.columns([4, 1])
        with col_head:
            st.subheader("📜 Komplett Översikt")
        with col_btn:
            if st.session_state.edit_mode:
                if st.button("💾 Spara & Lås tabell", type="primary", use_container_width=True):
                    st.session_state.edit_mode = False
                    st.rerun()
            else:
                if st.button("✏️ Aktivera Redigering", use_container_width=True):
                    st.session_state.edit_mode = True
                    st.rerun()

        cleaned_cards = []
        for c in cards:
            c_copy = c.copy()
            if c_copy.get("Bild") and not str(c_copy["Bild"]).startswith("data:") and not str(c_copy["Bild"]).startswith("http"):
                c_copy["Bild"] = format_image_source(c_copy["Bild"])
            cleaned_cards.append(c_copy)

        df = pd.DataFrame(cleaned_cards)

        cols_order = ["Bild", "Länk", "Name", "Buy_Date", "Buy_USD", "Buy_Currency_Rate", "Buy_SEK", "Sell_Date", "Sell_USD", "Sell_Currency_Rate", "Sell_SEK", "Status"]
        for c in cols_order:
            if c not in df.columns:
                df[c] = None
        
        df = df[cols_order]

        df["Buy_Date"] = pd.to_datetime(df["Buy_Date"], errors="coerce").dt.date
        df["Sell_Date"] = pd.to_datetime(df["Sell_Date"], errors="coerce").dt.date

        if st.session_state.edit_mode:
            st.info("💡 **Redigeringsläge aktivt:** Ändra datum eller priser. Valutakurser och SEK-belopp räknas om automatiskt när du sparar!")
            
            edited_df = st.data_editor(
                df,
                column_config=shared_column_config,
                num_rows="dynamic",
                use_container_width=True,
                key="table_editor"
            )

            updated_data = edited_df.to_dict(orient="records")
            for c in updated_data:
                try:
                    if pd.notna(c.get("Buy_Date")) and c.get("Buy_Date"):
                        c["Buy_Date"] = str(c["Buy_Date"])
                        c["Buy_Currency_Rate"] = get_usd_sek_rate(c["Buy_Date"])
                    else:
                        c["Buy_Date"] = ""

                    if c.get("Buy_USD") and c.get("Buy_Currency_Rate"):
                        c["Buy_SEK"] = round(float(c["Buy_USD"]) * float(c["Buy_Currency_Rate"]), 2)
                    
                    if c.get("Sell_USD") is not None and str(c.get("Sell_USD")).strip() != "" and float(c.get("Sell_USD") or 0) > 0:
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

            with open(DATA_FILE, "w") as f:
                json.dump(updated_data, f, indent=4)
        else:
            st.caption("Klicka på 🗑️ till vänster för att radera en rad direkt.")
            
            for idx, row in df.iterrows():
                col_del, col_data = st.columns([0.3, 9.7])
                with col_del:
                    if st.button("🗑️", key=f"del_{idx}", help="Radera denna rad"):
                        cards.pop(idx)
                        with open(DATA_FILE, "w") as f:
                            json.dump(cards, f, indent=4)
                        st.rerun()
                with col_data:
                    row_df = pd.DataFrame([row])
                    st.dataframe(
                        row_df,
                        column_config=shared_column_config,
                        hide_index=True,
                        use_container_width=True
                    )

        # --- A. KORT-SKATTEBERÄKNING (K4 AVSNITT D) ---
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
        st.subheader("📋 Underlag för Skatteverket (Bilaga K4 - Avsnitt D: Kort)")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Totalt Vinster (Kort)", f"{total_gains_sek:.2f} SEK")
        c2.metric("Totalt Förluster (Kort)", f"{total_losses_sek:.2f} SEK")
        c3.metric("Avdragsgill förlust (70%)", f"{deductible_loss:.2f} SEK")
        c4.metric("Kortskatt att betala (30%)", f"{card_tax:.2f} SEK")

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

        st.divider()
        st.subheader("💰 Total Ekonomi & Ren Nettovinst")

        n1, n2, n3, n4 = st.columns(4)
        n1.metric("Netto Kortresultat", f"{(total_gains_sek - total_losses_sek):.2f} SEK")
        n2.metric("Netto Valutaresultat", f"{(valuta_vinster_sek - valuta_forluster_sek):.2f} SEK")
        n3.metric("Total Beräknad Skatt", f"-{total_skatt:.2f} SEK", delta_color="inverse")
        n4.metric("💰 REN NETTOVINST", f"{netto_vinst:.2f} SEK")

        st.write("")
        p1, p2, p3 = st.columns(3)
        p1.metric("USD kvar på kontot", f"${usd_saldo:,.2f}")
        p2.metric("Inneliggande SEK-Omkostnad", f"{sek_omkostnad:,.2f} SEK")
        p3.metric("Aktiv Snittkurs (GNS)", f"{nuvarande_snittkurs:.4f} SEK/USD")

        # --- C. EXPORT & SKATTEVERKET FÄRDIG KOPIA ---
        st.divider()
        st.subheader("📄 Snabbkopia för Skatteverket (Inkomstdeklaration 1 & K4)")
        st.caption("Alla belopp nedan är avrundade till hela kronor enligt Skatteverkets regler.")

        m_k4_vinst_kort = round(total_gains_sek)
        m_k4_forlust_kort = round(total_losses_sek)
        m_k4_vinst_valuta = round(valuta_vinster_sek)
        m_k4_forlust_valuta = round(valuta_forluster_sek)

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Punkt 7.5 (Kortvinst)", f"{m_k4_vinst_kort} kr")
        s2.metric("Punkt 8.4 (Kortförlust)", f"{m_k4_forlust_kort} kr")
        s3.metric("Punkt 7.2 (Valutavinst)", f"{m_k4_vinst_valuta} kr")
        s4.metric("Punkt 8.1 (Valutaförlust)", f"{m_k4_forlust_valuta} kr")

        with st.expander("📋 Visa exakt radutskrift för K4-blanketten"):
            st.markdown("#### **Avsnitt D – Övriga tillgångar (Kort)**")
            if k4_card_export_rows:
                st.dataframe(pd.DataFrame(k4_card_export_rows), use_container_width=True)
            else:
                st.caption("Inga sålda kort ännu.")

            st.markdown("#### **Avsnitt C – Valuta (Uttag till bank)**")
            if k4_valuta_export_rows:
                st.dataframe(pd.DataFrame(k4_valuta_export_rows), use_container_width=True)
            else:
                st.caption("Inga bankuttag gjorda ännu.")

    else:
        st.info("Inga kort registrerade ännu. Gå till fliken 'Registrera Nytt Köp' för att börja!")