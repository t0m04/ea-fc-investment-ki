import streamlit as st
import pandas as pd
import os
import subprocess

st.set_page_config(page_title="EA FC Investment KI", layout="wide")
st.title("⚽ EA FC Investment KI Dashboard")
st.markdown("Empfohlene Spieler basierend auf Prognosen der KI")

# === Empfehlungen erzeugen, falls nicht vorhanden ===
try:
    if not os.path.exists("output/recommendations.csv"):
        os.makedirs("output", exist_ok=True)
        subprocess.run(["python","eafc_invest.py"], check=True)
except Exception as e:
    st.error(f"Fehler beim Generieren der Empfehlungen: {e}")
    st.stop()

# === Daten laden ===
if os.path.exists("output/recommendations.csv"):
    recs = pd.read_csv("output/recommendations.csv")
else:
    st.error("Keine Empfehlungen verfügbar.")
    st.stop()

# === Tabellenansicht ===
st.dataframe(recs[["player_name","rating","league","nation","price","buy_below","expected_profit_coins"]],
             use_container_width=True)

# === Kartenansicht ===
st.subheader("Spieler Karten")
for _, row in recs.iterrows():
    st.markdown(
        f"""
        <div style="border-radius:15px; background:linear-gradient(135deg,#2c2c54,#40407a);
                    padding:20px; margin:10px; color:white; font-family:sans-serif;">
            <h3>{row['player_name']} ({row['rating']})</h3>
            <p><b>Liga:</b> {row['league']} | <b>Nation:</b> {row['nation']}</p>
            <p><b>Aktueller Preis:</b> {row['price']} Coins</p>
            <p><b>Kaufen bis:</b> {row['buy_below']} Coins</p>
            <p><b>Erwarteter Gewinn:</b> {row['expected_profit_coins']} Coins</p>
        </div>
        """, unsafe_allow_html=True
    )
