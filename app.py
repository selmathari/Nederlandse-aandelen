from pathlib import Path
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Nederlandse aandelen", layout="wide")
st.title("🇳🇱 Nederlandse aandelen – Dashboard")
st.caption("Data: CSV’s in deze GitHub repo (gegenereerd vanuit Yahoo Finance / yfinance)")

DATA_DIR = Path("data")

@st.cache_data
def list_price_files():
    return sorted(DATA_DIR.glob("*_prices.csv"))

@st.cache_data
def load_prices(file_path: Path) -> pd.DataFrame:
    df = pd.read_csv(file_path)

    # yfinance export: meestal 'Date'
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
    # soms 'datetime' / 'Datetime'
    elif "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime")
    elif "Datetime" in df.columns:
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df = df.set_index("Datetime")

    return df

@st.cache_data
def load_summary() -> pd.DataFrame | None:
    fp = DATA_DIR / "summary_metrics.csv"
    if fp.exists():
        return pd.read_csv(fp, index_col=0)
    return None

files = list_price_files()
if not files:
    st.error("Geen *_prices.csv bestanden gevonden in de map /data.")
    st.stop()

names = [f.name.replace("_prices.csv", "") for f in files]
name_to_file = dict(zip(names, files))

# Sidebar
st.sidebar.header("Selectie")
chosen_name = st.sidebar.selectbox("Aandeel", names)

period = st.sidebar.selectbox("Periode", ["1mo", "3mo", "6mo", "1y", "5y", "max"], index=2)
days_map = {"1mo": 31, "3mo": 93, "6mo": 186, "1y": 366, "5y": 5 * 366}

df = load_prices(name_to_file[chosen_name])
if df.empty:
    st.warning("Dit bestand bevat geen data.")
    st.stop()

# kies juiste close-kolom
close_col = "Close" if "Close" in df.columns else None
if close_col is None:
    # fallback: pak eerste numerieke kolom
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            close_col = c
            break
if close_col is None:
    st.error("Geen koerskolom gevonden (verwacht 'Close').")
    st.stop()

df_view = df if period == "max" else df.tail(days_map[period])

# Metrics
last_close = float(df_view[close_col].iloc[-1])
prev_close = float(df_view[close_col].iloc[-2]) if len(df_view) > 1 else last_close
pct_1d = (last_close / prev_close - 1) * 100 if prev_close else 0.0

c1, c2, c3 = st.columns(3)
c1.metric("Laatste close", f"{last_close:.2f}")
c2.metric("1 dag (%)", f"{pct_1d:.2f}%")
c3.metric("Datapunten", f"{len(df_view)}")

# Koersgrafiek
st.subheader(f"Koers: {chosen_name}")
fig = plt.figure()
plt.plot(df_view.index, df_view[close_col])
plt.xlabel("Datum")
plt.ylabel("Close")
plt.grid(True)
st.pyplot(fig)

# Genormaliseerd vergelijken
st.subheader("Genormaliseerde performance (start = 100)")
fig2 = plt.figure(figsize=(10, 4))

for nm, fp in name_to_file.items():
    dfx = load_prices(fp)
    dfx = dfx if period == "max" else dfx.tail(days_map[period])
    if len(dfx) < 2:
        continue
    col = "Close" if "Close" in dfx.columns else close_col
    norm = dfx[col] / dfx[col].iloc[0] * 100
    plt.plot(dfx.index, norm, label=nm)

plt.xlabel("Datum")
plt.ylabel("Index")
plt.grid(True)
plt.legend()
st.pyplot(fig2)

# Rendement & volatiliteit (als je CSV hebt)
st.subheader("Overzicht: rendement & volatiliteit")
summary = load_summary()
if summary is not None:
    st.dataframe(summary, use_container_width=True)
else:
    st.info("summary_metrics.csv niet gevonden in /data (optioneel).")

# Correlatiematrix (op basis van returns uit CSV’s)
st.subheader("Correlatiematrix (dagelijkse returns)")
returns_df = pd.DataFrame()

for nm, fp in name_to_file.items():
    dfx = load_prices(fp)
    dfx = dfx if period == "max" else dfx.tail(days_map[period])
    if len(dfx) < 2:
        continue
    returns_df[nm] = dfx["Close"].pct_change()

returns_df = returns_df.dropna()

if len(returns_df.columns) >= 2 and len(returns_df) >= 5:
    corr = returns_df.corr()

    fig3 = plt.figure(figsize=(8, 6))
    plt.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    plt.colorbar(label="Correlatie")

    plt.xticks(range(len(corr.columns)), corr.columns, rotation=45)
    plt.yticks(range(len(corr.columns)), corr.columns)
    plt.title("Correlatiematrix – NL aandelen")
    plt.tight_layout()
    st.pyplot(fig3)

    with st.expander("Correlatie tabel"):
        st.dataframe(corr, use_container_width=True)
else:
    st.info("Te weinig data/kolommen om correlatie te tonen.")
