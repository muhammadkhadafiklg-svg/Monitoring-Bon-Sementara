"""
DASHBOARD MONITORING BON SEMENTARA
Sumber data : tab "Bon" di Google Sheet (diterbitkan sebagai CSV lewat "Publish to web").
Secret      : BON_CSV_URL  (isi di Streamlit Cloud > App settings > Secrets)
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Monitoring Bon Sementara", page_icon="🧾",
                   layout="wide", initial_sidebar_state="collapsed")

TZ = ZoneInfo("Asia/Jakarta")
BATAS_JAM = 24                 # bon dicairkan yang belum direalisasi lebih dari ini = gantung
NAMA_STORE = {}                # opsional, contoh: {"A361": "NAMA STORE A361"}

KOLOM = ["ID", "TglAjuan", "Store", "NIP", "Nama", "Keperluan", "Nominal", "Status", "Approver",
         "TglApprove", "CatatanMgr", "Cashier", "TglCair", "TglRealisasi", "NominalRealisasi",
         "Sisa", "CatatanRealisasi", "FotoID", "TglSelesai"]
KOLOM_TGL = ["TglAjuan", "TglApprove", "TglCair", "TglRealisasi", "TglSelesai"]

st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"], #MainMenu, footer, header {display:none !important}
.block-container {padding-top:1.4rem; max-width:1280px}
.judul {font-size:27px; font-weight:700; color:#0f172a; margin:0}
.sub {font-size:14px; color:#334155; margin:2px 0 14px}
.kartu {background:#fff; border:1px solid #cbd5e1; border-left:5px solid #1e3a8a; border-radius:6px; padding:12px 16px; margin-bottom:12px}
.kartu .l {font-size:13px; font-weight:600; color:#334155}
.kartu .v {font-size:25px; font-weight:700; color:#0f172a; line-height:1.25}
.kartu .n {font-size:12px; color:#334155}
.kartu.merah {border-left-color:#b91c1c}
.kartu.merah .v {color:#b91c1c}
.bagian {font-size:17px; font-weight:700; color:#0f172a; margin:22px 0 8px}
.aman {background:#ecfdf3; border:1px solid #86efac; color:#14532d; border-radius:6px; padding:10px 14px; font-weight:600}
.foot {text-align:center; color:#334155; font-size:13px; margin:38px 0 8px; padding-top:12px; border-top:1px solid #cbd5e1}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- pembaca data
@st.cache_data(ttl=60, show_spinner="Memuat data bon...")
def muat(url: str) -> pd.DataFrame:
    return pd.read_csv(url, dtype=str, keep_default_na=False)


def tgl(s: pd.Series) -> pd.Series:
    """Baca tanggal dari CSV; otomatis menebak dd/mm/yyyy atau mm/dd/yyyy."""
    s = s.astype(str).str.strip().replace("", pd.NA)
    m = s.dropna().str.extract(r"^(\d{1,2})/(\d{1,2})/\d{4}")
    if m.dropna().empty:
        return pd.to_datetime(s, errors="coerce", format="mixed")
    a = pd.to_numeric(m[0], errors="coerce")
    b = pd.to_numeric(m[1], errors="coerce")
    dayfirst = bool((a > 12).any()) or not bool((b > 12).any())
    return pd.to_datetime(s, errors="coerce", dayfirst=dayfirst, format="mixed")


def angka(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[^\d\-]", "", regex=True), errors="coerce").fillna(0)


def rp(n) -> str:
    return "Rp {:,.0f}".format(n).replace(",", ".")


def olah(raw: pd.DataFrame) -> pd.DataFrame:
    hilang = [k for k in KOLOM if k not in raw.columns]
    if hilang:
        st.error("Kolom tab Bon tidak lengkap: " + ", ".join(hilang) +
                 ". Pastikan yang diterbitkan adalah tab Bon versi terbaru.")
        st.stop()
    df = raw.copy()
    df = df[df["ID"].str.strip() != ""]
    for k in KOLOM_TGL:
        df[k] = tgl(df[k])
    for k in ["Nominal", "NominalRealisasi", "Sisa"]:
        df[k] = angka(df[k])
    df["Store"] = df["Store"].str.strip().str.upper()
    df["Bulan"] = df["TglAjuan"].dt.strftime("%Y-%m")
    now = datetime.now(TZ).replace(tzinfo=None)
    sel = (df["Status"] == "Dicairkan") & df["TglCair"].notna()
    df["LamaJam"] = 0
    df.loc[sel, "LamaJam"] = ((now - df.loc[sel, "TglCair"]).dt.total_seconds() // 3600).astype(int)
    df["Gantung"] = sel & (df["LamaJam"] >= BATAS_JAM)
    return df.sort_values("TglAjuan", ascending=False)


def tampil(df: pd.DataFrame, kolom: dict, rupiah=(), tanggal=()) -> pd.DataFrame:
    o = pd.DataFrame(index=df.index)
    for k, label in kolom.items():
        if k in rupiah:
            o[label] = df[k].map(rp)
        elif k in tanggal:
            o[label] = df[k].dt.strftime("%d/%m/%Y %H:%M").fillna("")
        else:
            o[label] = df[k]
    return o


def kartu(label, nilai, catatan="", merah=False):
    st.markdown(f'<div class="kartu{" merah" if merah else ""}"><div class="l">{label}</div>'
                f'<div class="v">{nilai}</div><div class="n">{catatan}&nbsp;</div></div>',
                unsafe_allow_html=True)


# ---------------------------------------------------------------- halaman
url = st.secrets.get("BON_CSV_URL", "") if hasattr(st, "secrets") else ""
if not url:
    st.error("BON_CSV_URL belum diisi di Secrets. Lihat panduan pemasangan.")
    st.stop()

try:
    data = olah(muat(url))
except Exception as e:  # noqa: BLE001
    st.error(f"Data tidak bisa dibaca dari Google Sheet: {e}")
    st.stop()

h1, h2 = st.columns([5, 1])
with h1:
    st.markdown('<p class="judul">MONITORING BON SEMENTARA</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub">Data diperbarui otomatis tiap 1 menit. Dimuat pukul '
                f'{datetime.now(TZ).strftime("%H:%M:%S")} WIB.</p>', unsafe_allow_html=True)
with h2:
    if st.button("Muat ulang", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

bulan_ada = sorted([b for b in data["Bulan"].dropna().unique()], reverse=True)
bulan_ini = datetime.now(TZ).strftime("%Y-%m")
if bulan_ini not in bulan_ada:
    bulan_ada.insert(0, bulan_ini)
f1, f2, f3, f4 = st.columns(4)
periode = f1.selectbox("Periode", ["SEMUA PERIODE"] + bulan_ada, index=1)
daftar_store = sorted(data["Store"].unique())
store = f2.selectbox("Store", ["SEMUA STORE"] + daftar_store,
                     format_func=lambda x: f"{x} - {NAMA_STORE[x]}" if x in NAMA_STORE else x)
status = f3.selectbox("Status", ["SEMUA STATUS", "Diajukan", "Disetujui", "Dicairkan",
                                 "Direalisasi", "Selesai", "Ditolak"])
cari = f4.text_input("Cari ID / nama / NIP")

dasar = data if store == "SEMUA STORE" else data[data["Store"] == store]
if cari.strip():
    q = cari.strip().lower()
    dasar = dasar[dasar[["ID", "Nama", "NIP", "Keperluan"]].agg(" ".join, axis=1).str.lower().str.contains(q, regex=False)]
per = dasar if periode == "SEMUA PERIODE" else dasar[dasar["Bulan"] == periode]

# ---- ringkasan
cair = per[per["Status"].isin(["Dicairkan", "Direalisasi", "Selesai"])]
blm = per[per["Status"] == "Dicairkan"]
gantung = dasar[dasar["Gantung"]]
c = st.columns(5)
with c[0]: kartu("JUMLAH BON", f"{len(per):,}".replace(",", "."), "pada periode terpilih")
with c[1]: kartu("TOTAL DIAJUKAN", rp(per["Nominal"].sum()))
with c[2]: kartu("TOTAL DICAIRKAN", rp(cair["Nominal"].sum()), f"{len(cair)} bon")
with c[3]: kartu("BELUM DIREALISASI", rp(blm["Nominal"].sum()), f"{len(blm)} bon")
with c[4]: kartu(f"GANTUNG > {BATAS_JAM} JAM", f"{len(gantung)}", "semua periode", merah=len(gantung) > 0)
c = st.columns(4)
with c[0]: kartu("MENUNGGU APPROVAL MANAGER", int((per["Status"] == "Diajukan").sum()))
with c[1]: kartu("MENUNGGU PENCAIRAN CASHIER", int((per["Status"] == "Disetujui").sum()))
with c[2]: kartu("MENUNGGU VERIFIKASI CASHIER", int((per["Status"] == "Direalisasi").sum()))
with c[3]: kartu("SELESAI", int((per["Status"] == "Selesai").sum()))

# ---- bon gantung
st.markdown(f'<div class="bagian">BON GANTUNG (BELUM DIREALISASI LEBIH DARI {BATAS_JAM} JAM)</div>', unsafe_allow_html=True)
if gantung.empty:
    st.markdown(f'<div class="aman">Tidak ada bon yang melewati {BATAS_JAM} jam.</div>', unsafe_allow_html=True)
else:
    g = gantung.sort_values("LamaJam", ascending=False)
    st.dataframe(tampil(g, {"Store": "Store", "ID": "ID Bon", "NIP": "NIP", "Nama": "Nama Staff",
                            "Keperluan": "Keperluan", "Nominal": "Nominal", "Cashier": "Dicairkan Oleh",
                            "TglCair": "Waktu Cair", "LamaJam": "Lama (Jam)"},
                           rupiah=("Nominal",), tanggal=("TglCair",)),
                 use_container_width=True, hide_index=True)

# ---- ringkasan per store
st.markdown('<div class="bagian">RINGKASAN PER STORE</div>', unsafe_allow_html=True)
if per.empty:
    st.write("Belum ada data pada periode ini.")
else:
    rk = per.groupby("Store").agg(
        Jumlah=("ID", "count"),
        Diajukan=("Nominal", "sum"),
        Selesai=("Status", lambda x: int((x == "Selesai").sum())),
    )
    rk["Dicairkan"] = cair.groupby("Store")["Nominal"].sum()
    rk["Belum"] = blm.groupby("Store")["Nominal"].sum()
    rk["Gantung"] = gantung.groupby("Store").size()
    rk = rk.fillna(0).reset_index().sort_values(["Gantung", "Belum"], ascending=False)
    out = pd.DataFrame({
        "Store": rk["Store"],
        "Nama Store": rk["Store"].map(NAMA_STORE).fillna(""),
        "Jumlah Bon": rk["Jumlah"].astype(int),
        "Total Diajukan": rk["Diajukan"].map(rp),
        "Total Dicairkan": rk["Dicairkan"].map(rp),
        "Belum Direalisasi": rk["Belum"].map(rp),
        "Bon Gantung": rk["Gantung"].astype(int),
        "Selesai": rk["Selesai"].astype(int),
    })
    if not NAMA_STORE:
        out = out.drop(columns=["Nama Store"])
    st.dataframe(out, use_container_width=True, hide_index=True)

# ---- daftar bon
st.markdown('<div class="bagian">DAFTAR BON (TERBARU DI ATAS)</div>', unsafe_allow_html=True)
det = per if status == "SEMUA STATUS" else per[per["Status"] == status]
if det.empty:
    st.write("Tidak ada bon sesuai filter.")
else:
    t = tampil(det, {"ID": "ID Bon", "TglAjuan": "Tgl Ajuan", "Store": "Store", "NIP": "NIP",
                     "Nama": "Nama Staff", "Keperluan": "Keperluan", "Nominal": "Nominal",
                     "Status": "Status", "Approver": "Disetujui Oleh", "Cashier": "Dicairkan Oleh",
                     "TglCair": "Waktu Cair", "TglRealisasi": "Waktu Realisasi",
                     "NominalRealisasi": "Terpakai", "Sisa": "Sisa/(Kurang)", "TglSelesai": "Selesai"},
               rupiah=("Nominal", "NominalRealisasi", "Sisa"),
               tanggal=("TglAjuan", "TglCair", "TglRealisasi", "TglSelesai"))
    belum_real = det["TglRealisasi"].isna()
    t.loc[belum_real, ["Terpakai", "Sisa/(Kurang)"]] = ""
    t["Foto"] = det["FotoID"].map(lambda x: "Ada" if str(x).strip() else "-")
    st.dataframe(t, use_container_width=True, hide_index=True)
    st.download_button("Unduh CSV", det.drop(columns=["FotoID"]).to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"bon_sementara_{periode}.csv", mime="text/csv")

st.markdown('<div class="foot">Powered and developed by M Khadafi</div>', unsafe_allow_html=True)
