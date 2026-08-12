# --- FLIK 1: ÖVERSIKT & SKATT ---
with tab1:
    if cards or deposits or withdrawals:
        if "edit_mode" not in st.session_state:
            st.session_state.edit_mode = False

        col_head, col_btn = st.columns([4, 1])
        with col_head:
            st.subheader("📜 Samling & Innehav")
        with col_btn:
            if st.session_state.is_admin and not st.session_state.edit_mode:
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

        if st.session_state.is_admin and st.session_state.edit_mode:
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
                with st.spinner("Uppdaterar valutakurser och sparar till GitHub..."):
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
            if st.session_state.is_admin:
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
            else:
                st.dataframe(
                    df,
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

        for c in cards:
            if c.get("Status") == "Såld":
                try:
                    buy_sek = float(c.get("Buy_SEK", 0) or 0)
                    sell_sek = float(c.get("Sell_SEK", 0) or 0)
                    diff = sell_sek - buy_sek
                    
                    total_sell_sek += sell_sek
                    total_buy_sek += buy_sek
                    
                    if diff >= 0:
                        total_gains_sek += diff
                    else:
                        total_losses_sek += abs(diff)
                except (ValueError, TypeError):
                    continue

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

        for d in deposits:
            try:
                wallet_events.append({
                    "Datum": str(d["Datum"]), "Typ": "INFLÖDE", "Beskrivning": "Insättning från bank",
                    "USD": float(d["USD"]), "SEK": float(d["Betalt_SEK"])
                })
            except Exception:
                pass

        for c in cards:
            if c.get("Buy_USD") and float(c.get("Buy_USD") or 0) > 0:
                try:
                    wallet_events.append({
                        "Datum": str(c["Buy_Date"]), "Typ": "UTFLÖDE", "Beskrivning": f"Köp: {c.get('Name', 'Kort')}",
                        "USD": float(c["Buy_USD"]), "SEK": float(c.get("Buy_SEK", 0) or 0)
                    })
                except Exception:
                    pass

            if c.get("Status") == "Såld" and c.get("Sell_Date") and c.get("Sell_USD"):
                try:
                    wallet_events.append({
                        "Datum": str(c["Sell_Date"]), "Typ": "INFLÖDE", "Beskrivning": f"Sålt: {c.get('Name', 'Kort')}",
                        "USD": float(c["Sell_USD"]), "SEK": float(c.get("Sell_SEK", 0) or 0)
                    })
                except Exception:
                    pass

        for w in withdrawals:
            try:
                wallet_events.append({
                    "Datum": str(w["Datum"]), "Typ": "UTFLÖDE", "Beskrivning": "Uttag till bank",
                    "USD": float(w["USD"]), "SEK": float(w["Erhållen_SEK"])
                })
            except Exception:
                pass

        wallet_events = sorted(wallet_events, key=lambda x: (pd.to_datetime(x["Datum"]), 0 if x["Typ"] == "INFLÖDE" else 1))

        usd_saldo = 0.0
        sek_omkostnad = 0.0
        valuta_vinster_sek = 0.0
        valuta_forluster_sek = 0.0

        for ev in wallet_events:
            if ev["Typ"] == "INFLÖDE":
                usd_saldo += ev["USD"]
                sek_omkostnad += ev["SEK"]
            elif ev["Typ"] == "UTFLÖDE":
                if usd_saldo > 0:
                    snittkurs = sek_omkostnad / usd_saldo
                    omkostnad_uttag = ev["USD"] * snittkurs
                    
                    if "Uttag till bank" in ev["Beskrivning"]:
                        diff_valuta = ev["SEK"] - omkostnad_uttag
                        if diff_valuta >= 0:
                            valuta_vinster_sek += diff_valuta
                        else:
                            valuta_forluster_sek += abs(diff_valuta)

                    usd_saldo -= ev["USD"]
                    sek_omkostnad -= omkostnad_uttag
                else:
                    usd_saldo -= ev["USD"]

        nuvarande_snittkurs = (sek_omkostnad / usd_saldo) if usd_saldo > 0 else 0.0
        valuta_deductible_loss = valuta_forluster_sek * 0.70
        valuta_taxable_base = max(0.0, valuta_vinster_sek - valuta_deductible_loss)
        valuta_tax = valuta_taxable_base * 0.30

        # --- AVSNITT FÖR VALUTASKATT (ÅTERSTÄLLT HÄR) ---
        st.divider()
        st.markdown("### 💱 Skatt på Valuta / USDC-uttag (Bilaga K4 - Avsnitt C)")

        v1, v2, v3, v4 = st.columns(4)
        v1.metric("Valutavinster", f"{valuta_vinster_sek:,.2f} kr")
        v2.metric("Valutaförluster", f"{valuta_forluster_sek:,.2f} kr")
        v3.metric("Avdragsgill valutaförlust (70%)", f"{valuta_deductible_loss:,.2f} kr")
        v4.metric("Valutaskatt (30%)", f"{valuta_tax:,.2f} kr")

        # --- SAMMANSTÄLLNING OCH DASHBOARD ---
        total_skatt = card_tax + valuta_tax
        brutto_resultat = (total_gains_sek - total_losses_sek) + (valuta_vinster_sek - valuta_forluster_sek)
        netto_vinst = brutto_resultat - total_skatt

        # MARKNADSVÄRDE HÄMTNING
        def get_courtyard_market_value(url):
            if not url or "courtyard.io" not in str(url):
                return 0.0
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                resp = requests.get(url, headers=headers, timeout=4)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    text = soup.get_text()
                    match = re.search(r"Market Value:?\s*\$([\d\.]+)", text, re.IGNORECASE)
                    if match:
                        return float(match.group(1))
            except Exception:
                pass
            return 0.0

        unsold_cards_market_usd = 0.0
        for c in cards:
            if c.get("Status") != "Såld":
                m_val = c.get("Market_USD")
                if not m_val and c.get("Länk"):
                    m_val = get_courtyard_market_value(c.get("Länk"))
                if not m_val:
                    m_val = float(c.get("Buy_USD", 0) or 0)
                unsold_cards_market_usd += float(m_val)

        today_rate = get_usd_sek_rate(date.today())
        total_deposited_sek = sum(float(d.get("Betalt_SEK", 0) or 0) for d in deposits)
        total_withdrawn_sek = sum(float(w.get("Erhållen_SEK", 0) or 0) for w in withdrawals)
        total_assets_sek = (usd_saldo + unsold_cards_market_usd) * today_rate

        # PIKACHU TOTALÖVERSIKT
        st.divider()
        st.markdown("""
        <div class="pikachu-card">
            <h3 style="margin-top:0; color:#FFDE00 !important;">⚡ Pikachu Totalöversikt</h3>
            <p>Sammanställning av dina innehav, saldon och total skattesituation.</p>
        </div>
        """, unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Wallet USD-Saldo", f"${usd_saldo:,.2f}", f"Snittkurs: {nuvarande_snittkurs:.2f} SEK")
        m2.metric("Osålda Kort (Marknad)", f"${unsold_cards_market_usd:,.2f}")
        m3.metric("Totalt Innehav (SEK)", f"{total_assets_sek:,.2f} kr", f"Dagens kurs: {today_rate:.2f}")
        m4.metric("Total Beräknad Skatt", f"{total_skatt:,.2f} kr")

        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Totalt Insatt (Bank)", f"{total_deposited_sek:,.2f} kr")
        m6.metric("Totalt Uttaget (Bank)", f"{total_withdrawn_sek:,.2f} kr")
        m7.metric("Bruttoresultat", f"{brutto_resultat:,.2f} kr")
        m8.metric("Nettoresultat (efter skatt)", f"{netto_vinst:,.2f} kr")
