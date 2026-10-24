"""
DASHBOARD MONITORING BON SEMENTARA
Sumber data bon   : tab "Bon" (Publish to web, format CSV)  -> secret BON_CSV_URL
Sumber master store: Google Sheet Kode Store / Nama Store / NAMA FRA / NAMA REGIONAL
                     (dibaca otomatis; opsional secret MASTER_CSV_URL atau MASTER_GID)
"""
import io
import urllib.request
from datetime import datetime
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

st.set_page_config(page_title="Monitoring Bon Sementara", page_icon="🧾",
                   layout="wide", initial_sidebar_state="collapsed")

TZ = ZoneInfo("Asia/Jakarta")
BATAS_JAM = 24
MASTER_ID = "1vcQ8iIARrUS_L1mXcXFu3d6DWWZgqBESBXSm5FsFRKc"

KOLOM = ["ID", "TglAjuan", "Store", "NIP", "Nama", "Keperluan", "Nominal", "Status", "Approver",
         "TglApprove", "CatatanMgr", "Cashier", "TglCair", "TglRealisasi", "NominalRealisasi",
         "Sisa", "CatatanRealisasi", "FotoID", "TglSelesai"]
KOLOM_TGL = ["TglAjuan", "TglApprove", "TglCair", "TglRealisasi", "TglSelesai"]
NAVY = colors.HexColor("#1e3a8a")
MERAH_CSS = "background-color:#fee2e2;color:#7f1d1d;font-weight:600"
KUNING_CSS = "background-color:#fef3c7;color:#78350f;font-weight:600"
HIJAU_CSS = "background-color:#dcfce7;color:#14532d"

st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"], #MainMenu, footer, header {display:none !important}
.block-container {padding-top:1rem; max-width:1320px}
.topbar {background:#1e3a8a; padding:12px 18px; border-radius:6px; margin-bottom:12px}
.topbar .t {font-size:19px; font-weight:700; letter-spacing:.4px; color:#fff}
.topbar .s {font-size:12px; color:#dbe4ff}
.kpi {background:#fff; border:1px solid #d5dbe5; border-top:3px solid #1e3a8a; border-radius:4px; padding:6px 10px; margin-bottom:8px}
.kpi .l {font-size:10.5px; font-weight:700; color:#475569; letter-spacing:.4px}
.kpi .v {font-size:17px; font-weight:700; color:#0f172a; line-height:1.3}
.kpi .n {font-size:11px; color:#475569}
.kpi.m {border-top-color:#b91c1c; background:#fef2f2}
.kpi.m .v {color:#b91c1c}
.strip {display:flex; flex-wrap:wrap; gap:8px; margin:2px 0 10px}
.strip span {background:#fff; border:1px solid #d5dbe5; border-radius:4px; padding:4px 10px; font-size:12px; color:#334155; font-weight:600}
.strip b {color:#0f172a; margin-left:4px}
.alarm {background:#fef2f2; border:1px solid #fca5a5; border-left:5px solid #b91c1c; color:#7f1d1d; border-radius:4px; padding:9px 14px; font-size:14px; margin:4px 0 10px}
.aman {background:#ecfdf3; border:1px solid #86efac; color:#14532d; border-radius:4px; padding:8px 14px; font-weight:600; font-size:14px}
.bagian {font-size:14px; font-weight:700; color:#0f172a; letter-spacing:.4px; margin:18px 0 6px; padding-bottom:4px; border-bottom:2px solid #1e3a8a}
.legend {font-size:12px; color:#334155; margin:4px 0 6px}
.legend i {display:inline-block; width:11px; height:11px; border-radius:2px; vertical-align:-1px; margin:0 4px 0 8px}
.foot {text-align:center; color:#334155; font-size:12px; margin:30px 0 6px; padding-top:10px; border-top:1px solid #cbd5e1}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- pengambil data
def rahasia(k, d=""):
    try:
        return str(st.secrets.get(k, d))
    except Exception:  # noqa: BLE001
        return d


def perbaiki_url(u: str) -> str:
    u = u.strip()
    if "/edit" in u or "/export" in u or "/gviz" in u:
        raise ValueError("Link bon harus link Publish to web (tab Bon, format CSV).")
    u = u.replace("/pubhtml", "/pub").replace("output=html", "output=csv")
    if "output=" not in u:
        u += ("&" if "?" in u else "?") + "output=csv"
    return u


def ambil_csv(url: str) -> pd.DataFrame:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        teks = r.read().decode("utf-8-sig", errors="replace")
    if teks.lstrip()[:1] == "<":
        raise ValueError("Link mengembalikan halaman web, bukan CSV. Periksa pengaturan berbagi/publikasi.")
    return pd.read_csv(io.StringIO(teks), dtype=str, keep_default_na=False)


@st.cache_data(ttl=60, show_spinner="Memuat data bon...")
def muat_bon(url: str) -> pd.DataFrame:
    return ambil_csv(perbaiki_url(url))


@st.cache_data(ttl=600, show_spinner=False)
def muat_master(url: str) -> pd.DataFrame:
    return ambil_csv(url)


def arsip_ids() -> dict:
    """Secret ARSIP_IDS berbentuk: 2026=ID_FILE_ARSIP,2027=ID_FILE_ARSIP"""
    out = {}
    for bagian in rahasia("ARSIP_IDS").split(","):
        if "=" in bagian:
            th, sid = bagian.split("=", 1)
            out[th.strip()] = sid.strip()
    return out


@st.cache_data(ttl=300, show_spinner=False)
def muat_arsip(sid: str, bln: str) -> pd.DataFrame:
    return ambil_csv(f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&sheet={bln}")


def url_master() -> str:
    u = rahasia("MASTER_CSV_URL")
    if u:
        return perbaiki_url(u) if "/pub" in u else u
    gid = rahasia("MASTER_GID")
    return f"https://docs.google.com/spreadsheets/d/{MASTER_ID}/export?format=csv" + (f"&gid={gid}" if gid else "")


def olah_master(m: pd.DataFrame) -> pd.DataFrame:
    kol = list(m.columns)

    def cari(*kunci):
        for k in kunci:
            for c in kol:
                if k in c.lower():
                    return c
        return None

    c_kode = cari("kode") or kol[0]
    c_nama, c_fra, c_reg = cari("nama store", "nama toko", "toko"), cari("fra"), cari("regional", "region")
    o = pd.DataFrame({
        "Store": m[c_kode].str.strip().str.upper(),
        "NamaStore": m[c_nama].str.strip() if c_nama else "",
        "FRA": m[c_fra].str.strip() if c_fra else "",
        "Regional": m[c_reg].str.strip() if c_reg else "",
    })
    return o[o["Store"] != ""].drop_duplicates("Store")


def tgl(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().replace("", pd.NA)
    m = s.dropna().str.extract(r"^(\d{1,2})/(\d{1,2})/\d{4}")
    if m.dropna().empty:
        return pd.to_datetime(s, errors="coerce", format="mixed")
    a, b = pd.to_numeric(m[0], errors="coerce"), pd.to_numeric(m[1], errors="coerce")
    dayfirst = bool((a > 12).any()) or not bool((b > 12).any())
    return pd.to_datetime(s, errors="coerce", dayfirst=dayfirst, format="mixed")


def angka(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[^\d\-]", "", regex=True), errors="coerce").fillna(0)


def rp(n) -> str:
    return "Rp {:,.0f}".format(n).replace(",", ".")


def fmt_tgl(d) -> str:
    return d.strftime("%d/%m/%Y %H:%M") if pd.notna(d) else ""


def olah(raw: pd.DataFrame) -> pd.DataFrame:
    hilang = [k for k in KOLOM if k not in raw.columns]
    if hilang:
        st.error("Kolom tab Bon tidak lengkap: " + ", ".join(hilang))
        st.stop()
    df = raw[raw["ID"].str.strip() != ""].copy()
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
    # realisasi yang selesai lebih dari 24 jam setelah dicairkan (melanggar WI)
    ada = df["TglCair"].notna() & df["TglRealisasi"].notna()
    detik = (df["TglRealisasi"] - df["TglCair"]).dt.total_seconds()
    df["LamaReal"] = 0
    df.loc[ada, "LamaReal"] = (detik[ada] // 3600).astype(int)
    df["Terlambat"] = ada & (detik > BATAS_JAM * 3600)
    df = df.sort_values("TglAjuan", ascending=False)
    # cocokkan kode store dengan master (nama store, FRA, regional)
    try:
        df = df.merge(olah_master(muat_master(url_master())), on="Store", how="left")
    except Exception as e:  # noqa: BLE001
        st.warning(f"Master store belum bisa dibaca ({e}). Nama store, FRA, dan regional dikosongkan.")
    for k in ("NamaStore", "FRA", "Regional"):
        if k not in df:
            df[k] = ""
        df[k] = df[k].fillna("")
    df["LabelStore"] = [f"{s} - {n}" if n else s for s, n in zip(df["Store"], df["NamaStore"])]
    return df.reset_index(drop=True)


def tanda(r) -> str:
    if r["Gantung"]:
        return f"GANTUNG {r['LamaJam']} JAM"
    if r["Status"] == "Dicairkan":
        return f"Belum realisasi ({r['LamaJam']} jam)"
    if r["Terlambat"]:
        return f"Terlambat realisasi ({r['LamaReal']} jam)"
    return ""


# ---------------------------------------------------------------- PDF
@st.cache_data(ttl=300, show_spinner=False)
def buat_pdf(info: str, ringkas: list, gantung: pd.DataFrame, rk: pd.DataFrame, det: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=13 * mm, bottomMargin=15 * mm, title="Monitoring Bon Sementara",
                            author="M Khadafi")
    ss = getSampleStyleSheet()
    judul = ParagraphStyle("j", parent=ss["Title"], fontSize=16, alignment=0, textColor=NAVY, spaceAfter=2)
    kecil = ParagraphStyle("k", parent=ss["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#334155"))
    sel = ParagraphStyle("s", parent=ss["Normal"], fontSize=7.5, leading=9)
    selh = ParagraphStyle("h", parent=sel, fontName="Helvetica-Bold", textColor=colors.white)
    bag = ParagraphStyle("b", parent=ss["Heading3"], fontSize=10.5, textColor=NAVY, spaceBefore=10, spaceAfter=4)

    def P(t, stl=sel):
        return Paragraph(escape(str(t)).replace("\n", "<br/>"), stl)

    def tabel(kepala, baris, lebar, warna=None):
        data = [[P(h, selh) for h in kepala]] + [[P(c) for c in r] for r in baris]
        t = Table(data, colWidths=[w * mm for w in lebar], repeatRows=1)
        gaya = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
        for i, w in enumerate(warna or [], start=1):
            if w == "merah":
                gaya.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fee2e2")))
            elif w == "kuning":
                gaya.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fef3c7")))
            elif w == "hijau":
                gaya.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#dcfce7")))
        t.setStyle(TableStyle(gaya))
        return t

    def kaki(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#334155"))
        canvas.drawCentredString(landscape(A4)[0] / 2, 8 * mm, "Powered and developed by M Khadafi")
        canvas.drawRightString(landscape(A4)[0] - 12 * mm, 8 * mm, f"Halaman {d.page}")
        canvas.restoreState()

    el = [Paragraph("MONITORING BON SEMENTARA", judul), Paragraph(escape(info), kecil), Spacer(1, 6),
          tabel([r[0] for r in ringkas], [[r[1] for r in ringkas]], [273 / len(ringkas)] * len(ringkas))]

    if len(gantung):
        el.append(Paragraph(f"BON GANTUNG (BELUM DIREALISASI LEBIH DARI {BATAS_JAM} JAM)", bag))
        rows = [[r.LabelStore + ("\nFRA: " + r.FRA if r.FRA else "") + (" | Reg: " + r.Regional if r.Regional else ""),
                 r.ID, f"{r.NIP} - {r.Nama}", r.Keperluan, rp(r.Nominal), fmt_tgl(r.TglCair), f"{r.LamaJam} jam"]
                for r in gantung.itertuples()]
        el.append(tabel(["Store", "ID Bon", "Staff", "Keperluan", "Nominal", "Waktu Cair", "Lama"], rows,
                        [62, 24, 42, 60, 26, 33, 26], ["merah"] * len(rows)))

    if len(rk):
        el.append(Paragraph("RINGKASAN PER STORE", bag))
        rows = [[r.LabelStore, r.FRA, r.Regional, int(r.Jumlah), rp(r.Diajukan), rp(r.Dicairkan), rp(r.Belum),
                 int(r.Gantung), int(r.Selesai)] for r in rk.itertuples()]
        el.append(tabel(["Store", "FRA", "Regional", "Jumlah", "Total Diajukan", "Total Dicairkan",
                         "Belum Direalisasi", "Gantung", "Selesai"], rows, [66, 36, 36, 16, 29, 29, 29, 16, 16],
                        ["merah" if r.Gantung > 0 else None for r in rk.itertuples()]))

    el.append(Paragraph("DAFTAR BON", bag))
    batas = 1500
    dd = det.head(batas)
    rows = [[r.ID, fmt_tgl(r.TglAjuan), r.LabelStore + ("\nFRA: " + r.FRA if r.FRA else ""), f"{r.NIP} - {r.Nama}",
             r.Keperluan, rp(r.Nominal), r.Status, tanda({"Gantung": r.Gantung, "LamaJam": r.LamaJam, "Status": r.Status, "Terlambat": r.Terlambat, "LamaReal": r.LamaReal})]
            for r in dd.itertuples()]
    warna = ["merah" if r.Gantung else ("hijau" if r.Status == "Dicairkan" else ("kuning" if r.Terlambat else None)) for r in dd.itertuples()]
    el.append(tabel(["ID Bon", "Tgl Ajuan", "Store", "Staff", "Keperluan", "Nominal", "Status", "Tanda"], rows,
                    [25, 25, 54, 40, 50, 24, 22, 33], warna))
    if len(det) > batas:
        el.append(Paragraph(f"Hanya {batas} baris pertama yang dicetak dari total {len(det)} baris.", kecil))
    el.append(Spacer(1, 4))
    el.append(Paragraph("Merah = gantung lebih dari 24 jam. Hijau = sudah dicairkan, belum direalisasi (masih dalam 24 jam). Kuning = realisasi selesai lebih dari 24 jam (tidak sesuai WI).", kecil))
    doc.build(el, onFirstPage=kaki, onLaterPages=kaki)
    return buf.getvalue()


# ---------------------------------------------------------------- tampilan
def tampil(df, kolom, rupiah=(), tanggal=()):
    o = pd.DataFrame(index=df.index)
    for k, label in kolom.items():
        if k in rupiah:
            o[label] = df[k].map(rp)
        elif k in tanggal:
            o[label] = df[k].map(fmt_tgl)
        else:
            o[label] = df[k]
    return o


def kpi(label, nilai, catatan="", merah=False):
    st.markdown(f'<div class="kpi{" m" if merah else ""}"><div class="l">{label}</div><div class="v">{nilai}</div>'
                f'<div class="n">{catatan}&nbsp;</div></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- halaman
url = rahasia("BON_CSV_URL")
if not url:
    st.error("BON_CSV_URL belum diisi di Secrets. Lihat panduan pemasangan.")
    st.stop()
sekarang = datetime.now(TZ)
h1, h2, h3, h4 = st.columns([5, 1.1, 1.1, 1.1])
with h1:
    st.markdown(f'<div class="topbar"><div class="t">MONITORING BON SEMENTARA</div>'
                f'<div class="s">Diperbarui otomatis tiap 1 menit. Dimuat {sekarang.strftime("%d/%m/%Y %H:%M:%S")} WIB</div></div>',
                unsafe_allow_html=True)
with h2:
    if st.button("Muat ulang", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
slot_pdf, slot_csv = h3.empty(), h4.empty()

bulan_ini = sekarang.strftime("%Y-%m")
bulan_opsi, y_, m_ = [], sekarang.year, sekarang.month
for _ in range(12):
    bulan_opsi.append(f"{y_}-{m_:02d}")
    m_ -= 1
    if m_ == 0:
        y_, m_ = y_ - 1, 12
f = st.columns(4)
periode = f[0].selectbox("Periode", ["SEMUA PERIODE"] + bulan_opsi, index=1,
                         help="SEMUA PERIODE = 12 bulan terakhir ditambah bon yang masih aktif.")
try:
    raws, ids = [muat_bon(url)], arsip_ids()
    for b_ in (bulan_opsi if periode == "SEMUA PERIODE" else [periode]):
        sid = ids.get(b_[:4])
        if not sid:
            continue
        try:
            raws.append(muat_arsip(sid, b_))
        except Exception:  # noqa: BLE001
            pass  # tab arsip bulan itu belum ada
    data = olah(pd.concat(raws, ignore_index=True).drop_duplicates("ID", keep="first"))
except Exception as e:  # noqa: BLE001
    st.error(f"Data tidak bisa dibaca dari Google Sheet: {e}")
    st.stop()
if not arsip_ids() and (periode == "SEMUA PERIODE" or periode != bulan_ini):
    st.info("Riwayat yang sudah diarsipkan baru tampil setelah ARSIP_IDS diisi di Secrets.")
reg = f[1].selectbox("Regional", ["SEMUA REGIONAL"] + sorted(x for x in data["Regional"].unique() if x))
d0 = data if reg == "SEMUA REGIONAL" else data[data["Regional"] == reg]
fra = f[2].selectbox("FRA", ["SEMUA FRA"] + sorted(x for x in d0["FRA"].unique() if x))
d0 = d0 if fra == "SEMUA FRA" else d0[d0["FRA"] == fra]
lbl = d0.drop_duplicates("Store").set_index("Store")["LabelStore"].to_dict()
store = f[3].selectbox("Store", ["SEMUA STORE"] + sorted(lbl), format_func=lambda x: lbl.get(x, x))
f2 = st.columns(4)
status = f2[0].selectbox("Status", ["SEMUA STATUS", "Diajukan", "Disetujui", "Dicairkan",
                                    "Direalisasi", "Selesai", "Ditolak"])
cari = f2[1].text_input("Cari ID / nama / NIP")

dasar = d0 if store == "SEMUA STORE" else d0[d0["Store"] == store]
if cari.strip():
    q = cari.strip().lower()
    dasar = dasar[dasar[["ID", "Nama", "NIP", "Keperluan"]].agg(" ".join, axis=1).str.lower().str.contains(q, regex=False)]
per = dasar if periode == "SEMUA PERIODE" else dasar[dasar["Bulan"] == periode]
cair = per[per["Status"].isin(["Dicairkan", "Direalisasi", "Selesai"])]
blm = per[per["Status"] == "Dicairkan"]
gantung = dasar[dasar["Gantung"]].sort_values("LamaJam", ascending=False)

# ---- peringatan dan ringkasan
if len(gantung):
    st.markdown(f'<div class="alarm"><b>PERHATIAN:</b> {len(gantung)} bon gantung lebih dari {BATAS_JAM} jam, '
                f'total {rp(gantung["Nominal"].sum())}. Mohon segera ditindaklanjuti.</div>', unsafe_allow_html=True)
k = st.columns(5)
with k[0]: kpi("JUMLAH BON", f"{len(per):,}".replace(",", "."), "periode terpilih")
with k[1]: kpi("TOTAL DIAJUKAN", rp(per["Nominal"].sum()))
with k[2]: kpi("TOTAL DICAIRKAN", rp(cair["Nominal"].sum()), f"{len(cair)} bon")
with k[3]: kpi("BELUM DIREALISASI", rp(blm["Nominal"].sum()), f"{len(blm)} bon")
with k[4]: kpi(f"GANTUNG &gt; {BATAS_JAM} JAM", len(gantung), "semua periode", merah=len(gantung) > 0)
n = per["Status"].value_counts()
st.markdown('<div class="strip">' + "".join(f"<span>{t}<b>{int(n.get(s, 0))}</b></span>" for t, s in [
    ("MENUNGGU APPROVAL", "Diajukan"), ("MENUNGGU PENCAIRAN", "Disetujui"),
    ("MENUNGGU VERIFIKASI", "Direalisasi"), ("SELESAI", "Selesai"), ("DITOLAK", "Ditolak")]) + f"<span>REALISASI TERLAMBAT<b>{int(per['Terlambat'].sum())}</b></span></div>",
    unsafe_allow_html=True)

# ---- bon gantung
st.markdown(f'<div class="bagian">BON GANTUNG (BELUM DIREALISASI LEBIH DARI {BATAS_JAM} JAM)</div>', unsafe_allow_html=True)
if gantung.empty:
    st.markdown(f'<div class="aman">Tidak ada bon yang melewati {BATAS_JAM} jam.</div>', unsafe_allow_html=True)
else:
    tg = tampil(gantung, {"LabelStore": "Store", "FRA": "FRA", "Regional": "Regional", "ID": "ID Bon", "NIP": "NIP",
                          "Nama": "Nama Staff", "Keperluan": "Keperluan", "Nominal": "Nominal",
                          "Cashier": "Dicairkan Oleh", "TglCair": "Waktu Cair"}, rupiah=("Nominal",), tanggal=("TglCair",))
    tg["Lama"] = gantung["LamaJam"].map(lambda x: f"{x} jam")
    st.dataframe(tg.style.apply(lambda r: [MERAH_CSS] * len(r), axis=1), use_container_width=True, hide_index=True)

# ---- ringkasan per store
st.markdown('<div class="bagian">RINGKASAN PER STORE</div>', unsafe_allow_html=True)
if per.empty:
    rk = pd.DataFrame(columns=["LabelStore", "FRA", "Regional", "Jumlah", "Diajukan", "Dicairkan", "Belum", "Gantung", "Selesai"])
    st.write("Belum ada data pada periode ini.")
else:
    rk = per.groupby("Store").agg(Jumlah=("ID", "count"), Diajukan=("Nominal", "sum"),
                                  Selesai=("Status", lambda x: int((x == "Selesai").sum())))
    rk["Dicairkan"] = cair.groupby("Store")["Nominal"].sum()
    rk["Belum"] = blm.groupby("Store")["Nominal"].sum()
    rk["Gantung"] = gantung.groupby("Store").size()
    rk = rk.fillna(0).join(data.drop_duplicates("Store").set_index("Store")[["LabelStore", "FRA", "Regional"]])
    rk = rk.sort_values(["Gantung", "Belum"], ascending=False).reset_index(drop=True)
    tr = pd.DataFrame({"Store": rk["LabelStore"], "FRA": rk["FRA"], "Regional": rk["Regional"],
                       "Jumlah Bon": rk["Jumlah"].astype(int), "Total Diajukan": rk["Diajukan"].map(rp),
                       "Total Dicairkan": rk["Dicairkan"].map(rp), "Belum Direalisasi": rk["Belum"].map(rp),
                       "Bon Gantung": rk["Gantung"].astype(int), "Selesai": rk["Selesai"].astype(int)})
    st.dataframe(tr.style.apply(lambda r: [MERAH_CSS if rk.loc[r.name, "Gantung"] > 0 else ""] * len(r), axis=1),
                 use_container_width=True, hide_index=True)

# ---- daftar bon
st.markdown('<div class="bagian">DAFTAR BON (TERBARU DI ATAS)</div>', unsafe_allow_html=True)
st.markdown('<div class="legend"><i style="background:#fecaca"></i>Merah: gantung lebih dari 24 jam'
            '<i style="background:#bbf7d0"></i>Hijau: sudah dicairkan, belum direalisasi (masih dalam 24 jam)'
            '<i style="background:#fde68a"></i>Kuning: realisasi lebih dari 24 jam (tidak sesuai WI)</div>',
            unsafe_allow_html=True)
det = per if status == "SEMUA STATUS" else per[per["Status"] == status]
if det.empty:
    st.write("Tidak ada bon sesuai filter.")
else:
    t = tampil(det, {"ID": "ID Bon", "TglAjuan": "Tgl Ajuan", "LabelStore": "Store", "FRA": "FRA", "Regional": "Regional",
                     "NIP": "NIP", "Nama": "Nama Staff", "Keperluan": "Keperluan", "Nominal": "Nominal", "Status": "Status"},
               rupiah=("Nominal",), tanggal=("TglAjuan",))
    t["Tanda"] = det.apply(tanda, axis=1)
    ext = tampil(det, {"Approver": "Disetujui Oleh", "Cashier": "Dicairkan Oleh", "TglCair": "Waktu Cair",
                       "TglRealisasi": "Waktu Realisasi", "NominalRealisasi": "Terpakai", "Sisa": "Sisa/(Kurang)",
                       "TglSelesai": "Selesai"}, rupiah=("NominalRealisasi", "Sisa"),
                 tanggal=("TglCair", "TglRealisasi", "TglSelesai"))
    ext.loc[det["TglRealisasi"].isna(), ["Terpakai", "Sisa/(Kurang)"]] = ""
    t = pd.concat([t, ext], axis=1)
    t["Foto"] = det["FotoID"].map(lambda x: "Ada" if str(x).strip() else "-")
    warna = pd.Series(["m" if g else ("h" if s == "Dicairkan" else ("k" if tl else "")) for g, s, tl in zip(det["Gantung"], det["Status"], det["Terlambat"])], index=det.index)
    css = {"m": MERAH_CSS, "h": HIJAU_CSS, "k": KUNING_CSS, "": ""}
    st.dataframe(t.style.apply(lambda r: [css[warna[r.name]]] * len(r), axis=1), use_container_width=True, hide_index=True)

# ---- ekspor (PDF dan CSV)
info = (f"Periode: {periode} | Regional: {reg} | FRA: {fra} | Store: {lbl.get(store, store)} | Status: {status}"
        f"{' | Pencarian: ' + cari.strip() if cari.strip() else ''} | Dicetak {sekarang.strftime('%d/%m/%Y %H:%M')} WIB")
ringkas = [("JUMLAH BON", len(per)), ("TOTAL DIAJUKAN", rp(per["Nominal"].sum())),
           ("TOTAL DICAIRKAN", rp(cair["Nominal"].sum())), ("BELUM DIREALISASI", rp(blm["Nominal"].sum())),
           (f"GANTUNG > {BATAS_JAM} JAM", len(gantung)), ("MENUNGGU APPROVAL", int(n.get("Diajukan", 0))),
           ("MENUNGGU PENCAIRAN", int(n.get("Disetujui", 0))), ("MENUNGGU VERIFIKASI", int(n.get("Direalisasi", 0))),
           ("SELESAI", int(n.get("Selesai", 0)))]
nama_file = f"monitoring_bon_{periode}_{sekarang.strftime('%Y%m%d_%H%M')}"
try:
    pdf = buat_pdf(info, ringkas, gantung, rk, det)
    slot_pdf.download_button("Unduh PDF", pdf, file_name=nama_file + ".pdf", mime="application/pdf",
                             use_container_width=True)
except Exception as e:  # noqa: BLE001
    slot_pdf.button("PDF gagal", disabled=True, help=str(e), use_container_width=True)
slot_csv.download_button("Unduh CSV", det.drop(columns=["FotoID"]).to_csv(index=False).encode("utf-8-sig"),
                         file_name=nama_file + ".csv", mime="text/csv", use_container_width=True)

st.markdown('<div class="foot">Powered and developed by M Khadafi</div>', unsafe_allow_html=True)
