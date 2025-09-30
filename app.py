import streamlit as st
import pandas as pd
import os
import subprocess
import shutil
import sys
from textwrap import dedent

st.set_page_config(page_title="EA FC Investment KI", layout="wide")
st.title("⚽ EA FC Investment KI Dashboard")
st.markdown("Empfohlene Spieler basierend auf Prognosen der KI")

def run_trainer():
    os.makedirs("output", exist_ok=True)

    candidates = [
        sys.executable,
        shutil.which("python3"),
        shutil.which("python"),
    ]
    cmd_base = next((c for c in candidates if c), None)
    if not cmd_base:
        raise RuntimeError("Kein Python-Interpreter gefunden.")

    proc = subprocess.run(
        [cmd_base, "eafc_invest.py"],
        capture_output=True, text=True
    )

    if proc.returncode != 0:
        with st.expander("Fehlerdetails anzeigen (Logs)"):
            st.code(dedent(f"""
                COMMAND: {cmd_base} eafc_invest.py
                RETURN CODE: {proc.returncode}

                --- STDOUT ---
                {proc.stdout}

                --- STDERR ---
                {proc.stderr}
            """))
        raise RuntimeError(f"Training fehlgeschlagen (Exit {proc.returncode}).")

try:
    if not os.path.exists("output/recommendations.csv"):
        st.info("Erzeuge Empfehlungen… (erstmaliger Start kann etwas dauern)")
        run_trainer()
except Exception as e:
    st.error(f"Fehler beim Generieren der Empfehlungen: {e}")
    st.stop()

if os.path.exists("output/recommendations.csv"):
    recs = pd.read_csv("output/recommendations.csv")
else:
    st.error("Keine Empfehlungen verfügbar.")
    st.stop()

st.dataframe(
    recs[["player_name","rating","league","nation","price","buy_below","expected_profit_coins"]],
    use_container_width=True
)

st.subheader("Spieler Karten")
for _, row in recs.iterrows():
    st.markdown(
        f"""
        <div style="border-radius:15px; background:linear-gradient(135deg,#2c2c54,#40407a);
                    padding:20px; margin:10px; color:white; font-family:sans-serif;">
            <h3>{row.get('player_name','?')} ({row.get('rating','?')})</h3>
            <p><b>Liga:</b> {row.get('league','?')} | <b>Nation:</b> {row.get('nation','?')}</p>
            <p><b>Aktueller Preis:</b> {int(row.get('price',0))} Coins</p>
            <p><b>Kaufen bis:</b> {int(row.get('buy_below',0))} Coins</p>
            <p><b>Erwarteter Gewinn:</b> {int(row.get('expected_profit_coins',0))} Coins</p>
        </div>
        """, unsafe_allow_html=True
    )
