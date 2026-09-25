"""
=======================================================================
DASHBOARD TOKO PERTIWI — nama file tetap dashboard_v5.py (logika v13)
=======================================================================
Perubahan v13 (25 Sep 2026):
- 5 tab analisa baru: Pembeli Besar, Diskon & Harga, Brand, Stok & Katalog,
  Staf & Hari (sumber: view v_tp_* baru di Supabase)
- Deteksi hari "parsial" (data hari terakhir belum lengkap) di hero & grafik
- Badge kesegaran data pakai jam WIB (bukan jam server UTC)
- Catatan umur data ("data baru X hari") di hero
- Password TIDAK lagi ditulis di kode (repo publik) — lokal dibaca dari
  config_supabase.py (LOGIN_EMAIL, LOGIN_PASSWORD)
- Satu view gagal dimuat tidak lagi membuat seluruh dashboard error

Perubahan dari v4:
- Ada halaman login (email + password) sebelum dashboard bisa dilihat
- Kredensial Supabase & login dibaca dari st.secrets (kalau di-deploy ke
  Streamlit Cloud) ATAU dari config_supabase.py (kalau dijalankan lokal)
  — jadi file yang SAMA bisa dipakai di dua tempat tanpa diubah.

CARA JALANKAN LOKAL (masih sama seperti sebelumnya):
    py -m streamlit run dashboard_v5.py

CARA DEPLOY KE WEB: ikuti instruksi yang diberikan terpisah.
=======================================================================
"""

import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import hashlib
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import quote

st.set_page_config(page_title="Toko Pertiwi — Sales & Promosi", layout="wide", page_icon="🧱")

# ----------------------------------------------------------------
# KONFIGURASI — coba st.secrets dulu (utk versi web/deploy),
# kalau tidak ada baru pakai config_supabase.py (utk lokal)
# ----------------------------------------------------------------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_SERVICE_ROLE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    LOGIN_EMAIL = st.secrets["LOGIN_EMAIL"]
    LOGIN_PASSWORD = st.secrets["LOGIN_PASSWORD"]
except Exception:
    import config_supabase as _cfg
    SUPABASE_URL = _cfg.SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY = _cfg.SUPABASE_SERVICE_ROLE_KEY
    LOGIN_EMAIL = getattr(_cfg, "LOGIN_EMAIL", "")
    LOGIN_PASSWORD = getattr(_cfg, "LOGIN_PASSWORD", "")
    if not LOGIN_EMAIL or not LOGIN_PASSWORD:
        st.error("LOGIN_EMAIL / LOGIN_PASSWORD belum diisi di config_supabase.py (untuk jalan lokal).")
        st.stop()

# ======================================================================
# TEMA — palet terang, aksen "blueprint & safety tape"
# ======================================================================
BG = "#F4F6F8"
PANEL = "#FFFFFF"
BORDER = "#DDE2E8"
TEXT = "#1F242B"
TEXT_MUTED = "#5B6470"
BLUE = "#1D7FA8"
AMBER = "#C97D0E"
TEAL = "#237A61"
RUST = "#BD432B"
VIOLET = "#6355C7"
GREY = "#8A93A0"

CHART_COLORWAY = [BLUE, AMBER, TEAL, RUST, VIOLET, GREY]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"], p, div, span, label {{ font-family: 'IBM Plex Sans', sans-serif; }}
h1, h2, h3 {{ font-family: 'Space Grotesk', sans-serif; }}

[data-testid="stAppViewContainer"] {{ background: {BG}; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid {BORDER}; }}
[data-testid="stSidebar"] * {{ color: {TEXT_MUTED}; }}

[data-testid="stMetric"] {{
    background: {PANEL}; border: 1px solid {BORDER}; border-left: 3px solid {BLUE};
    padding: 14px 18px; border-radius: 6px;
}}
[data-testid="stMetricValue"] {{ font-family: 'Space Grotesk', sans-serif; color: {TEXT}; }}
[data-testid="stMetricLabel"] {{ color: {TEXT_MUTED}; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {BORDER}; }}
.stTabs [data-baseweb="tab"] {{ background: transparent; color: {TEXT_MUTED}; font-weight: 500; padding: 10px 18px; }}
.stTabs [aria-selected="true"] {{ color: {BLUE} !important; border-bottom: 2px solid {BLUE} !important; }}

[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 6px; }}

.tp-head {{ border-left: 3px solid var(--tp-accent, {BLUE}); padding: 4px 0 4px 14px; margin: 10px 0 4px 0; }}
.tp-head h3 {{ margin: 0; font-size: 1.08rem; color: {TEXT}; }}
.tp-head p {{ margin: 2px 0 0 0; color: {TEXT_MUTED}; font-size: 0.87rem; }}

.tp-explain {{ color: {TEXT_MUTED}; font-size: 0.88rem; line-height: 1.5; margin: 4px 0 12px 0; max-width: 780px; }}

.tp-hero {{ display: flex; gap: 36px; align-items: baseline; padding: 6px 0 18px 0; flex-wrap: wrap; }}
.tp-hero-num {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 2.6rem; color: {BLUE}; line-height: 1; }}
.tp-hero-lbl {{ color: {TEXT_MUTED}; font-size: 0.85rem; margin-top: 4px; }}
.tp-hero-sub {{ font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 1.5rem; color: {TEXT}; }}

.tp-insight {{
    background: #FFF8EC; border-left: 3px solid {AMBER};
    padding: 12px 16px; border-radius: 6px; margin: 8px 0 18px 0;
    color: {TEXT}; font-size: 0.92rem; line-height: 1.55;
}}
.tp-insight b {{ color: {AMBER}; }}
</style>
""", unsafe_allow_html=True)


# ======================================================================
# LOGIN GATE — token disimpan di URL (query param), bertahan walau hard-refresh
# ======================================================================
def make_auth_token():
    raw = f"{LOGIN_EMAIL.strip().lower()}:{LOGIN_PASSWORD}:toko-pertiwi-salt-v1"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# Cek token di URL SEBELUM menampilkan form login
if not st.session_state.get("tp_logged_in"):
    if st.query_params.get("auth") == make_auth_token():
        st.session_state["tp_logged_in"] = True


def login_screen():
    st.markdown(f"""
    <div style="max-width:380px; margin: 60px auto 0 auto; text-align:center;">
        <div style="font-family:'Space Grotesk',sans-serif; font-size:1.6rem; font-weight:700; color:{TEXT};">🧱 Toko Pertiwi</div>
        <div style="color:{TEXT_MUTED}; font-size:0.9rem; margin-top:4px;">Masuk untuk mengakses dashboard Sales & Promosi</div>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Masuk", use_container_width=True)
        if submitted:
            if email.strip().lower() == LOGIN_EMAIL.strip().lower() and password == LOGIN_PASSWORD:
                st.session_state["tp_logged_in"] = True
                st.query_params["auth"] = make_auth_token()
                st.rerun()
            else:
                st.error("Email atau password salah.")
        st.caption("Setelah masuk, jangan hapus bagian '?auth=...' di alamat browser — itu yang membuat login bertahan walau di-refresh.")


if not st.session_state.get("tp_logged_in"):
    login_screen()
    st.stop()


# ----------------------------------------------------------------
# Helper format angka gaya Indonesia
# ----------------------------------------------------------------
def id_num(x, decimals=0):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "-"
    s = f"{x:,.{decimals}f}"
    integer_part, _, decimal_part = s.partition(".")
    integer_part = integer_part.replace(",", ".")
    return f"{integer_part},{decimal_part}" if decimals > 0 else integer_part


def id_rp(x, decimals=0):
    return f"Rp {id_num(x, decimals)}"


def id_rp_short(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "-"
    if abs(x) >= 1_000_000_000:
        return f"Rp {id_num(x/1_000_000_000, 1)} M"
    if abs(x) >= 1_000_000:
        return f"Rp {id_num(x/1_000_000, 1)} jt"
    if abs(x) >= 1_000:
        return f"Rp {id_num(x/1_000, 0)} rb"
    return id_rp(x)


def id_pct(x, decimals=1):
    return f"{id_num(x, decimals)}%"


def head(title: str, caption: str = "", accent: str = BLUE):
    cap_html = f"<p>{caption}</p>" if caption else ""
    st.markdown(f'<div class="tp-head" style="--tp-accent:{accent}"><h3>{title}</h3>{cap_html}</div>', unsafe_allow_html=True)


def explain(html: str):
    st.markdown(f'<div class="tp-explain">{html}</div>', unsafe_allow_html=True)


def insight(html: str):
    st.markdown(f'<div class="tp-insight">💡 {html}</div>', unsafe_allow_html=True)


def style_fig(fig, height=380):
    fig.update_layout(
        paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        font=dict(family="IBM Plex Sans, sans-serif", color=TEXT, size=13),
        colorway=CHART_COLORWAY, margin=dict(l=10, r=10, t=30, b=10), height=height,
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    return fig


def styled_table(df, currency_cols=None, number_cols=None, pct_cols=None, color_col=None, invert_color=False):
    if df.empty:
        return df
    fmt = {}
    for c in (currency_cols or []):
        if c in df.columns:
            fmt[c] = lambda v: id_rp(v)
    for c in (number_cols or []):
        if c in df.columns:
            fmt[c] = lambda v: id_num(v)
    for c in (pct_cols or []):
        if c in df.columns:
            fmt[c] = lambda v: id_pct(v)
    styler = df.style.format(fmt)
    if color_col and color_col in df.columns:
        def _c(v):
            try:
                v = float(v)
            except (TypeError, ValueError):
                return ""
            positif_warna = RUST if invert_color else TEAL
            negatif_warna = TEAL if invert_color else RUST
            if v > 0:
                return f"color: {positif_warna}; font-weight: 600;"
            if v < 0:
                return f"color: {negatif_warna}; font-weight: 600;"
            return ""
        styler = styler.map(_c, subset=[color_col])
    return styler


@st.cache_data(ttl=300)
def sb(view: str, query: str = "") -> pd.DataFrame:
    url = f"{SUPABASE_URL}/rest/v1/{view}?{query}"
    resp = requests.get(url, headers={
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }, timeout=30)
    resp.raise_for_status()
    return pd.DataFrame(resp.json())


def sbs(view: str, query: str = "") -> pd.DataFrame:
    """Versi aman dari sb(): kalau satu view gagal, tampilkan pesan kecil, dashboard tetap jalan."""
    try:
        return sb(view, query)
    except Exception as e:  # noqa: BLE001
        st.caption(f"⚠️ Data `{view}` belum bisa dimuat ({type(e).__name__}). Coba tombol Refresh; kalau tetap, cek view di Supabase.")
        return pd.DataFrame()


def sb_all(view: str, query: str = "", page: int = 1000, max_pages: int = 20) -> pd.DataFrame:
    """Ambil semua baris walau > 1000 (batas default Supabase per request)."""
    parts = []
    for i in range(max_pages):
        q = f"{query}&limit={page}&offset={i * page}" if query else f"limit={page}&offset={i * page}"
        part = sbs(view, q)
        if part.empty:
            break
        parts.append(part)
        if len(part) < page:
            break
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def num(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Ubah kolom angka dari API (kadang string) jadi float."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def today_wib() -> date:
    try:
        return datetime.now(ZoneInfo("Asia/Jakarta")).date()
    except Exception:  # server tanpa data zona waktu -> pakai UTC+7 manual
        return (datetime.utcnow() + timedelta(hours=7)).date()


# ======================================================================
# HERO
# ======================================================================
daily = sb("v_tp_sales_daily", "order=tanggal.asc")
data_window = sbs("v_tp_data_window")

# ---- Deteksi hari terakhir "parsial" (faktur < 50% median 7 hari sebelumnya) ----
partial_day = None
if len(daily) >= 4:
    _d = num(daily.copy(), ["jumlah_faktur"])
    _last = _d.iloc[-1]
    _ref = _d.iloc[-8:-1]["jumlah_faktur"].median()
    if _ref and _last["jumlah_faktur"] < 0.5 * _ref:
        partial_day = {"tanggal": _last["tanggal"], "faktur": int(_last["jumlah_faktur"]), "ref": _ref}
weekly = sb("v_tp_sales_weekly", "order=minggu_mulai.asc")
dow = sb("v_tp_sales_by_dow", "order=urutan_hari.asc")

col_title, col_refresh, col_logout = st.columns([4, 1, 1])
with col_title:
    st.markdown("## Toko Pertiwi")
    st.caption("Sales & Promosi — data langsung dari Supabase, ter-update otomatis tiap hari")
with col_refresh:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()
with col_logout:
    if st.button("🚪 Keluar"):
        st.session_state["tp_logged_in"] = False
        if "auth" in st.query_params:
            del st.query_params["auth"]
        st.rerun()

if not daily.empty:
    total_omzet = daily["omzet"].astype(float).sum()
    total_faktur = int(daily["jumlah_faktur"].astype(int).sum())
    rentang = f"{daily['tanggal'].min()} — {daily['tanggal'].max()}"

    st.markdown(f"""
    <div class="tp-hero">
        <div><div class="tp-hero-num">{id_rp_short(total_omzet)}</div><div class="tp-hero-lbl">Total omzet tercatat</div></div>
        <div><div class="tp-hero-sub">{id_num(total_faktur)}</div><div class="tp-hero-lbl">Total faktur</div></div>
        <div><div class="tp-hero-sub">{id_rp_short(total_omzet/max(len(daily),1))}</div><div class="tp-hero-lbl">Rata-rata omzet/hari</div></div>
        <div><div class="tp-hero-sub" style="font-size:1.1rem;color:{TEXT_MUTED}">{rentang}</div><div class="tp-hero-lbl">Rentang data</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Badge kesehatan sinkronisasi data ----
    try:
        last_date = datetime.strptime(daily["tanggal"].max(), "%Y-%m-%d").date()
        days_stale = (today_wib() - last_date).days
    except (TypeError, ValueError):
        days_stale = None

    if days_stale is not None:
        if days_stale <= 1:
            b_color, b_bg, b_text = TEAL, "#EAF6F1", f"✅ Data up to date — transaksi terakhir {last_date}"
        elif days_stale <= 3:
            b_color, b_bg, b_text = AMBER, "#FFF8EC", f"⚠️ Data telat {days_stale} hari — transaksi terakhir {last_date}, cek sinkronisasi"
        else:
            b_color, b_bg, b_text = RUST, "#FCEDEA", f"🔴 Sinkronisasi kemungkinan macet — data terakhir {days_stale} hari lalu ({last_date})"
        st.markdown(
            f'<div style="display:inline-block; background:{b_bg}; border:1px solid {b_color}; color:{b_color}; '
            f'padding:5px 14px; border-radius:20px; font-size:0.82rem; font-weight:600; margin-bottom:10px;">{b_text}</div>',
            unsafe_allow_html=True,
        )

    if partial_day:
        st.markdown(
            f'<div style="display:inline-block; background:#FFF8EC; border:1px solid {AMBER}; color:{AMBER}; '
            f'padding:5px 14px; border-radius:20px; font-size:0.82rem; font-weight:600; margin:0 0 10px 8px;">'
            f'⏳ {partial_day["tanggal"]} kemungkinan belum lengkap — baru {partial_day["faktur"]} faktur '
            f'(biasanya ±{id_num(partial_day["ref"])}). Jangan dibaca sebagai penurunan.</div>',
            unsafe_allow_html=True,
        )

    if not data_window.empty:
        _hari = pd.to_numeric(data_window.iloc[0].get("hari_transaksi"), errors="coerce")
        if pd.notna(_hari) and _hari < 60:
            _hari = int(_hari)
            st.caption(f"📏 Data baru mencakup {_hari} hari transaksi. Pola harian/mingguan & kesimpulan 'barang tidak laku' "
                       "masih indikatif — makin bisa dipercaya setelah ±8–12 minggu data.")

st.markdown(f'<hr style="border-color:{BORDER}; margin:0 0 18px 0;">', unsafe_allow_html=True)

(tab_ringkasan, tab_ranking, tab_promosi, tab_segmen, tab_besar, tab_diskon,
 tab_brand, tab_stok, tab_staf, tab_kualitas) = st.tabs([
    "Ringkasan & Tren", "Ranking Barang/Kategori", "Promosi & Bundling",
    "Segmentasi Transaksi", "Pembeli Besar", "Diskon & Harga", "Brand",
    "Stok & Katalog", "Staf & Hari", "Kualitas Data",
])

# ==================================================================
# TAB 1: RINGKASAN & TREN
# ==================================================================
with tab_ringkasan:
    head("Tren omzet harian", "Tiap titik = total penjualan 1 hari", BLUE)
    explain("Grafik ini menjawab pertanyaan paling dasar: <b>apakah toko sedang naik, turun, atau stabil?</b> "
            "Naik-turun harian itu wajar (efek akhir pekan, tanggal muda/tua) — yang perlu diwaspadai adalah kalau garis ini "
            "menurun terus selama beberapa hari berturut-turut, bukan cuma satu hari sepi.")
    if not daily.empty:
        fig = px.area(daily, x="tanggal", y="omzet")
        fig.update_traces(line_color=BLUE, fillcolor="rgba(29,127,168,0.12)")
        fig.update_yaxes(tickformat=",.0f")
        if partial_day:
            fig.add_annotation(x=partial_day["tanggal"], y=float(daily.iloc[-1]["omzet"]), text="belum lengkap",
                               showarrow=True, arrowhead=2, arrowcolor=AMBER, font=dict(color=AMBER, size=11), ay=-40)
        st.plotly_chart(style_fig(fig, 320), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        head("Tren mingguan", "Rata-kan noise harian, lihat arah sebenarnya", AMBER)
        explain("Kalau tren harian terlalu naik-turun untuk disimpulkan, lihat versi mingguan ini — "
                "lebih jelas terlihat apakah minggu ini benar-benar lebih baik/buruk dari minggu lalu.")
        if not weekly.empty:
            fig2 = px.bar(weekly, x="minggu_mulai", y="omzet")
            fig2.update_traces(marker_color=AMBER)
            fig2.update_yaxes(tickformat=",.0f")
            st.plotly_chart(style_fig(fig2, 300), use_container_width=True)

    with col_b:
        head("Pola hari dalam seminggu", "Bentuk kelopak = performa hari itu", VIOLET)
        explain("Tiap 'kelopak' mewakili satu hari (Senin di atas, berputar searah jarum jam). "
                "Kelopak yang pendek = hari yang secara konsisten sepi — kandidat waktu terbaik untuk promosi, "
                "karena mendorong hari yang sudah ramai biasanya kurang efektif dibanding mengisi hari yang kosong.")
        if not dow.empty:
            fig3 = go.Figure(go.Barpolar(
                r=dow["total_omzet"].astype(float), theta=dow["hari"],
                marker_color=dow["total_omzet"].astype(float),
                marker_colorscale=[[0, "#EDEFF2"], [1, VIOLET]],
                marker_line_color=BORDER, marker_line_width=1,
            ))
            fig3.update_layout(polar=dict(bgcolor=PANEL,
                               radialaxis=dict(showticklabels=False, gridcolor=BORDER),
                               angularaxis=dict(gridcolor=BORDER, color=TEXT_MUTED)))
            st.plotly_chart(style_fig(fig3, 320), use_container_width=True)
            termurah = dow.loc[dow["total_omzet"].astype(float).idxmin(), "hari"]
            teramai = dow.loc[dow["total_omzet"].astype(float).idxmax(), "hari"]
            insight(f"<b>{teramai}</b> adalah hari paling ramai, <b>{termurah}</b> paling sepi. "
                    f"Kalau mau coba promosi flash-sale, jadwalkan di hari {termurah} — bukan di hari yang sudah ramai secara alami.")

# ==================================================================
# TAB 2: RANKING BARANG & KATEGORI
# ==================================================================
with tab_ranking:
    cat = sb("v_tp_sales_by_category", "order=omzet.desc")
    abc = sb("v_tp_abc_analysis", "order=rank_omzet.asc")
    eff = sb("v_tp_category_efficiency", "order=omzet_per_sku.asc")

    head("Peta kategori", "Ukuran kotak = besarnya omzet kategori itu", BLUE)
    explain("Bayangkan ini denah toko dilihat dari atas: kotak paling besar adalah kategori yang paling banyak "
            "menyumbang omzet. Kalau suatu saat kotak besar ini tiba-tiba mengecil dibanding kunjungan sebelumnya, "
            "itu sinyal untuk dicek — kehabisan stok? Ada kompetitor baru di kategori itu?")
    if not cat.empty:
        fig = px.treemap(cat.head(30), path=["kategori"], values="omzet",
                          color="omzet", color_continuous_scale=[[0, "#DCEAF1"], [1, BLUE]])
        fig.update_traces(textfont_size=13, marker_line_color=PANEL, marker_line_width=2,
                           texttemplate="%{label}<br>" + "Rp%{value:,.0f}")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(style_fig(fig, 420), use_container_width=True)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        head("Klasifikasi ABC (Pareto)", "Barang mana yang WAJIB selalu ada stoknya", TEAL)
        explain("Prinsip klasik toko retail: biasanya sebagian kecil barang menyumbang sebagian besar omzet. "
                "<b>Kelas A</b> adalah barang-barang itu — kalau salah satunya kehabisan stok, dampaknya langsung "
                "terasa di omzet harian. <b>Kelas C</b> sebaliknya: banyak jenis barang, tapi kontribusinya kecil-kecil — "
                "kandidat untuk dikurangi variannya atau dihabiskan lewat diskon.")
        if not abc.empty:
            summary = abc.groupby("kelas_abc").agg(jumlah_sku=("kode_barang", "count"), total_omzet=("omzet", "sum")).reset_index()
            fig = go.Figure(go.Pie(labels=summary["kelas_abc"], values=summary["total_omzet"], hole=0.62,
                                    marker=dict(colors=[TEAL, AMBER, GREY])))
            total_all = summary["total_omzet"].sum()
            fig.add_annotation(text=id_rp_short(total_all), x=0.5, y=0.52, showarrow=False,
                                font=dict(size=20, color=TEXT, family="Space Grotesk"))
            fig.add_annotation(text="total omzet", x=0.5, y=0.42, showarrow=False, font=dict(size=11, color=TEXT_MUTED))
            st.plotly_chart(style_fig(fig, 300), use_container_width=True)
            st.dataframe(styled_table(summary, currency_cols=["total_omzet"], number_cols=["jumlah_sku"]),
                         use_container_width=True, hide_index=True)

    with col_b:
        head("Efisiensi kategori", "Omzet per SKU — kategori 'gemuk' vs efisien", RUST)
        explain("Ini membandingkan omzet yang dihasilkan per varian barang. Kategori dengan garis merah punya "
                "banyak varian tapi masing-masing kontribusinya kecil — itu berarti modal & rak toko terpakai untuk "
                "sesuatu yang perputarannya lambat. Kategori efisien sebaliknya: sedikit varian, tapi masing-masing laris.")
        if not eff.empty:
            eff_show = eff[eff["status_efisiensi"] != "Normal"].head(12)
            fig = px.bar(eff_show.sort_values("omzet_per_sku"), x="omzet_per_sku", y="kategori", orientation="h",
                         color="status_efisiensi",
                         color_discrete_map={"Kurang Efisien (byk SKU, omzet/SKU rendah)": RUST, "Sangat Efisien": TEAL})
            fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title="Omzet per SKU (Rp)")
            fig.update_xaxes(tickformat=",.0f")
            st.plotly_chart(style_fig(fig, 380), use_container_width=True)

    with st.expander("📋 Lihat detail ABC per barang (semua SKU)"):
        if not abc.empty:
            st.dataframe(styled_table(abc, currency_cols=["omzet"], number_cols=["rank_omzet", "total_sku"],
                                       pct_cols=["persen_kumulatif", "persen_sku_kumulatif"]),
                         use_container_width=True, hide_index=True)

    head("Ranking lengkap kategori", "", GREY)
    if not cat.empty:
        st.dataframe(styled_table(cat, currency_cols=["omzet", "rata2_omzet_per_hari"], number_cols=["jumlah_sku_aktif", "total_qty"]),
                     use_container_width=True, hide_index=True)

# ==================================================================
# TAB 3: PROMOSI & BUNDLING
# ==================================================================
with tab_promosi:
    basket_pairs = sb("v_tp_basket_pairs", "order=jumlah_faktur_bersama.desc&limit=15")
    cat_cooc = sb("v_tp_category_cooccurrence", "order=jumlah_faktur_bersama.desc&limit=12")
    basket_size = sb("v_tp_basket_size")
    momentum = sb("v_tp_category_momentum", "order=perubahan_persen.asc")
    new_items = sb("v_tp_new_item_performance", "order=jumlah_transaksi.desc")

    head("Ukuran belanja per struk", "Peluang cross-sell paling langsung", AMBER)
    explain("Tiap struk dikelompokkan berdasarkan berapa jenis barang yang dibeli sekaligus. "
            "Bandingkan grafik kiri (jumlah struk) dengan grafik kanan (nilai rata-rata) — kalau mayoritas struk "
            "ada di kelompok '1 barang' tapi nilainya jauh lebih kecil dari kelompok '2-3 barang', itu artinya "
            "cuma dengan menawarkan SATU barang tambahan ke pembeli, nilai transaksi bisa naik signifikan.")
    if not basket_size.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(basket_size, x="kelompok_ukuran", y="jumlah_faktur", text="persen_faktur")
            fig.update_traces(marker_color=AMBER, texttemplate="%{text}%", textposition="outside")
            fig.update_layout(yaxis_title="Jumlah faktur", xaxis_title=None)
            st.plotly_chart(style_fig(fig, 300), use_container_width=True)
        with c2:
            fig2 = px.bar(basket_size, x="kelompok_ukuran", y="rata2_nilai_faktur")
            fig2.update_traces(marker_color=TEAL)
            fig2.update_layout(yaxis_title="Rata-rata Rp/faktur", xaxis_title=None)
            fig2.update_yaxes(tickformat=",.0f")
            st.plotly_chart(style_fig(fig2, 300), use_container_width=True)
        satu = basket_size[basket_size["kelompok_ukuran"] == "1 barang"]
        dua_tiga = basket_size[basket_size["kelompok_ukuran"] == "2-3 barang"]
        if not satu.empty and not dua_tiga.empty:
            insight(f"<b>{id_pct(satu.iloc[0]['persen_faktur'])} struk cuma beli 1 barang</b> (rata-rata {id_rp(satu.iloc[0]['rata2_nilai_faktur'])}), "
                    f"padahal struk 2-3 barang rata-rata sudah {id_rp(dua_tiga.iloc[0]['rata2_nilai_faktur'])} — "
                    "hampir tiga kali lipat. Latih kasir menawarkan satu barang pelengkap yang relevan (lihat tabel di bawah) sebelum transaksi selesai.")

    col_a, col_b = st.columns(2)
    with col_a:
        head("Barang sering dibeli bersamaan", "Dasar ide bundling per-barang", BLUE)
        explain("Kalau dua kode barang sering muncul di faktur yang sama, itu artinya pelanggan memang butuh keduanya "
                "sekaligus (misal fitting pipa + lem-nya). Pajang berdekatan di rak, atau tawarkan sebagai paket.")
        if not basket_pairs.empty:
            fig = px.bar(basket_pairs.sort_values("jumlah_faktur_bersama"), x="jumlah_faktur_bersama", y="kode_a",
                         orientation="h", hover_data=["kode_b"])
            fig.update_traces(marker_color=BLUE)
            fig.update_layout(yaxis_title=None, xaxis_title="Jumlah faktur bersama")
            st.plotly_chart(style_fig(fig, 380), use_container_width=True)
    with col_b:
        head("Kategori sering dibeli bersamaan", "Dasar ide paket lintas kategori", VIOLET)
        explain("Versi lebih luas dari tabel kiri — kalau dua KATEGORI (bukan cuma dua barang spesifik) sering "
                "muncul bersamaan, itu bisa jadi dasar paket promosi yang lebih besar, misal 'paket mulai renovasi'.")
        if not cat_cooc.empty:
            st.dataframe(styled_table(cat_cooc, number_cols=["jumlah_faktur_bersama"]),
                         use_container_width=True, hide_index=True, height=380)

    head("Kategori besar tapi melambat", "Prioritas promosi #1 — bukan yang memang tak laku", RUST)
    explain("Ini beda dari 'barang tidak laku' biasa. Ini kategori yang TERBUKTI besar (total omzet tinggi) tapi "
            "arahnya sedang menurun dibanding awal periode. Kategori seperti ini paling layak diselidiki dan "
            "didorong lewat promosi — karena pasarnya sudah terbukti ada, cuma sedang melemah.")
    if not momentum.empty:
        sig = momentum[momentum["total_omzet"].astype(float) > 2_000_000].copy()
        if not sig.empty:
            st.dataframe(styled_table(sig, currency_cols=["omzet_paruh_awal", "omzet_paruh_akhir", "total_omzet"],
                                       pct_cols=["perubahan_persen"], color_col="perubahan_persen"),
                         use_container_width=True, hide_index=True)
        st.caption("Berbasis perbandingan paruh-awal vs paruh-akhir periode data yang ada — akan lebih akurat setelah beberapa minggu.")

    head("Performa barang baru", "Pertama terjual dalam 7 hari terakhir data", TEAL)
    explain("Barang yang baru muncul di data dan sudah punya beberapa transaksi berarti langsung diterima pasar — "
            "pertimbangkan tambah stoknya. Yang cuma terjual sekali dan tidak berulang, masih terlalu dini disimpulkan.")
    if not new_items.empty:
        st.dataframe(styled_table(new_items, currency_cols=["omzet"], number_cols=["jumlah_transaksi", "total_qty", "umur_hari_dlm_data"]),
                     use_container_width=True, hide_index=True)
    else:
        st.caption("Belum ada barang baru terdeteksi di jendela data saat ini.")

# ==================================================================
# TAB 4: SEGMENTASI TRANSAKSI
# ==================================================================
with tab_segmen:
    segs = sb("v_tp_transaction_segments")
    named = sb("v_tp_named_customer_summary", "order=total_belanja.desc")

    head("Segmentasi nilai transaksi", "Top 10% faktur vs sisanya", AMBER)
    explain("Semua faktur dikelompokkan jadi 3 berdasarkan besar-kecilnya nilai: 'Borongan/Proyek' (10% faktur "
            "dengan nilai terbesar), 'Menengah', dan 'Retail Kecil'. Ini menjawab pertanyaan penting: apakah omzet "
            "toko ditopang oleh banyak pembeli kecil, atau segelintir pembeli besar?")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if not segs.empty:
            fig = go.Figure(go.Pie(labels=segs["segmen"], values=segs["total_omzet"], hole=0.55,
                                    marker=dict(colors=[AMBER, BLUE, GREY])))
            st.plotly_chart(style_fig(fig, 340), use_container_width=True)
    with col_b:
        if not segs.empty:
            st.dataframe(styled_table(segs, currency_cols=["rata2_nilai_faktur", "total_omzet"],
                                       number_cols=["jumlah_faktur"], pct_cols=["persen_dari_omzet"]),
                         use_container_width=True, hide_index=True)
    top10 = segs[segs["segmen"].str.contains("Borongan", na=False)] if not segs.empty else pd.DataFrame()
    if not top10.empty:
        insight(f"<b>{id_pct(top10.iloc[0]['persen_dari_omzet'])} omzet</b> berasal dari cuma {id_num(top10.iloc[0]['jumlah_faktur'])} faktur "
                "'Borongan/Proyek'. Ini artinya kesehatan omzet toko lebih ditentukan oleh menjaga hubungan baik dengan "
                "segelintir pembeli besar ini, dibanding mengejar volume pembeli retail harian.")

    head("Pelanggan bernama", "Di luar Tunai POS / Pelanggan Umum", TEAL)
    explain("Mayoritas transaksi toko tidak tercatat atas nama siapa pun (pembeli tunai/walk-in). Daftar di bawah "
            "adalah pengecualian — pelanggan yang identitasnya tercatat di Accurate, biasanya karena mereka pembeli "
            "rutin atau punya hubungan bisnis (B2B). Layak dipertimbangkan untuk program relasi/kredit khusus.")
    if not named.empty:
        st.dataframe(styled_table(named, currency_cols=["total_belanja", "rata2_per_faktur"], number_cols=["jumlah_faktur"]),
                     use_container_width=True, hide_index=True)
    else:
        st.caption("Belum ada pelanggan bernama di data saat ini.")

# ==================================================================
# TAB: PEMBELI BESAR (Pareto faktur)
# ==================================================================
with tab_besar:
    bands = num(sbs("v_tp_invoice_size_bands", "order=band.asc"),
                ["faktur", "pct_faktur", "omzet", "pct_omzet", "rata2_faktur", "rata2_baris", "rata2_segmen"])
    curve = num(sb_all("v_tp_invoice_pareto", "select=persentil_faktur,kumulatif_omzet_pct&order=peringkat.asc,no_faktur.asc"),
                ["persentil_faktur", "kumulatif_omzet_pct"])
    top_inv = num(sbs("v_tp_invoice_pareto",
                      "select=no_faktur,tanggal,penginput,baris,segmen_dibeli,omzet,diskon_rp&order=peringkat.asc&limit=25"),
                  ["baris", "segmen_dibeli", "omzet", "diskon_rp"])

    head("Omzet ditopang siapa?", "Porsi jumlah faktur vs porsi omzet, per besar nilai faktur", AMBER)
    explain("Bandingkan dua batang di tiap kelompok. Kalau batang <b>omzet</b> jauh lebih tinggi dari batang "
            "<b>jumlah faktur</b>, berarti kelompok itu sedikit orangnya tapi besar pengaruhnya ke uang toko.")
    if not bands.empty:
        long = bands.melt(id_vars="band", value_vars=["pct_faktur", "pct_omzet"], var_name="ukuran", value_name="persen")
        long["ukuran"] = long["ukuran"].map({"pct_faktur": "% jumlah faktur", "pct_omzet": "% omzet"})
        fig = px.bar(long, x="band", y="persen", color="ukuran", barmode="group", text="persen",
                     color_discrete_map={"% jumlah faktur": GREY, "% omzet": AMBER})
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(xaxis_title="Nilai faktur", yaxis_title="%", legend_title=None)
        st.plotly_chart(style_fig(fig, 340), use_container_width=True)

        besar = bands[bands["band"].str.startswith(("4.", "5."))]
        kecil = bands[bands["band"].str.startswith("1.")]
        if not besar.empty and not kecil.empty:
            insight(f"Faktur ≥ Rp1 juta cuma <b>{id_num(besar['faktur'].sum())} faktur ({id_pct(besar['pct_faktur'].sum())})</b>, "
                    f"tapi menyumbang <b>{id_pct(besar['pct_omzet'].sum())} omzet</b>. Sebaliknya "
                    f"{id_pct(kecil['pct_faktur'].sum())} faktur di bawah Rp100rb hanya {id_pct(kecil['pct_omzet'].sum())} omzet. "
                    "Nama pelanggan di faktur hampir selalu kosong — jadi toko <b>belum tahu siapa pembeli besar ini</b> "
                    "dan apakah mereka kembali. Usulan: wajibkan kasir mencatat nama + no. HP untuk setiap faktur ≥ Rp1 juta.")
        st.dataframe(styled_table(bands, currency_cols=["omzet", "rata2_faktur"], number_cols=["faktur"],
                                  pct_cols=["pct_faktur", "pct_omzet"]), use_container_width=True, hide_index=True)

    col_a, col_b = st.columns([1.1, 1])
    with col_a:
        head("Kurva Pareto faktur", "Faktur diurutkan dari terbesar", BLUE)
        explain("Sumbu bawah = persen faktur (terbesar dulu), sumbu kiri = persen omzet yang sudah terkumpul. "
                "Makin cepat kurva naik ke atas, makin omzet bergantung pada segelintir transaksi.")
        if not curve.empty:
            fig = px.line(curve, x="persentil_faktur", y="kumulatif_omzet_pct")
            fig.update_traces(line_color=BLUE, line_width=3)
            fig.update_layout(xaxis_title="% faktur (terbesar dulu)", yaxis_title="% omzet kumulatif")
            st.plotly_chart(style_fig(fig, 320), use_container_width=True)
            p10 = curve[curve["persentil_faktur"] <= 10]["kumulatif_omzet_pct"].max()
            if pd.notna(p10):
                insight(f"<b>10% faktur terbesar = {id_pct(p10)} omzet.</b>")
    with col_b:
        head("25 faktur terbesar", "Kandidat pembeli proyek untuk ditelusuri namanya", TEAL)
        if not top_inv.empty:
            st.dataframe(styled_table(top_inv, currency_cols=["omzet", "diskon_rp"], number_cols=["baris", "segmen_dibeli"]),
                         use_container_width=True, hide_index=True, height=360)

# ==================================================================
# TAB: DISKON & HARGA
# ==================================================================
with tab_diskon:
    d_cat = num(sbs("v_tp_discount_by_category", "order=diskon_rp.desc"),
                ["baris_total", "baris_diskon", "pct_baris_diskon", "faktur_diskon", "gross", "diskon_rp",
                 "diskon_efektif_pct_rata2", "jumlah_variasi_pct"])
    d_week = num(sbs("v_tp_discount_weekly", "order=minggu.asc"),
                 ["baris", "baris_diskon", "pct_baris_diskon", "diskon_rp", "diskon_per_omzet_pct"])
    d_lines = num(sbs("v_tp_discount_lines", "order=diskon_rp.desc&limit=300"),
                  ["qty", "unit_price", "gross", "diskon_rp", "diskon_efektif_pct", "netto"])
    leak_sum = num(sbs("v_tp_price_leakage_summary", "order=minggu.asc"),
                   ["baris", "sku", "selisih_rp", "selisih_rp_qty_normal"])
    leak = num(sbs("v_tp_price_leakage", "konteks_volume=like.Qty*&band=not.like.4*&order=selisih_rp.desc&limit=100"),
               ["qty", "harga_modus", "harga_transaksi", "dibawah_modus_pct", "selisih_rp", "median_qty_grup"])

    head("Diskon yang diberikan kasir", "Diskon per baris barang yang tercatat di Accurate", RUST)
    explain("Yang dihitung di sini adalah diskon yang <b>diketik di faktur</b> (persen atau rupiah). Tawar-menawar yang "
            "langsung mengubah harga satuan tanpa kolom diskon TIDAK masuk sini — itu ada di bagian 'harga di bawah kebiasaan' di bawah.")
    if not d_cat.empty:
        total_d = d_cat["diskon_rp"].sum()
        omzet_total = float(daily["omzet"].astype(float).sum()) if not daily.empty else 0
        m1, m2, m3 = st.columns(3)
        m1.metric("Total diskon tercatat", id_rp_short(total_d))
        m2.metric("Porsi dari omzet", id_pct(100 * total_d / omzet_total if omzet_total else 0, 2))
        m3.metric("Baris berdiskon", id_num(d_cat["baris_diskon"].sum()))

        tidak_konsisten = d_cat[d_cat["jumlah_variasi_pct"] > 1]
        top = d_cat.iloc[0]
        teks = (f"Diskon terbesar ada di <b>{top['kategori']}</b> ({id_rp_short(top['diskon_rp'])}, "
                f"{id_pct(100 * top['diskon_rp'] / total_d if total_d else 0)} dari semua diskon). ")
        if not tidak_konsisten.empty:
            contoh = tidak_konsisten.iloc[0]
            teks += (f"Ada <b>{len(tidak_konsisten)} kategori dengan persen diskon berbeda-beda</b> — misalnya "
                     f"{contoh['kategori']}: {contoh['variasi_pct']}% oleh {contoh['pemberi_diskon']}. "
                     "Besarnya kecil, masalahnya konsistensi: tanpa aturan tertulis, harga bergantung pada siapa yang melayani.")
        insight(teks)

        col_a, col_b = st.columns([1.2, 1])
        with col_a:
            st.dataframe(styled_table(d_cat[["kategori", "brand", "baris_diskon", "pct_baris_diskon", "diskon_rp",
                                             "diskon_efektif_pct_rata2", "variasi_pct", "pemberi_diskon"]],
                                      currency_cols=["diskon_rp"], number_cols=["baris_diskon"],
                                      pct_cols=["pct_baris_diskon", "diskon_efektif_pct_rata2"]),
                         use_container_width=True, hide_index=True, height=320)
        with col_b:
            if not d_week.empty:
                fig = px.bar(d_week, x="minggu", y="diskon_rp", text="pct_baris_diskon")
                fig.update_traces(marker_color=RUST, texttemplate="%{text:.1f}% baris", textposition="outside")
                fig.update_layout(xaxis_title="Minggu mulai", yaxis_title="Diskon (Rp)")
                fig.update_yaxes(tickformat=",.0f")
                st.plotly_chart(style_fig(fig, 320), use_container_width=True)
        with st.expander("📋 Semua baris berdiskon (untuk dicek ke kasir)"):
            if not d_lines.empty:
                st.dataframe(styled_table(d_lines, currency_cols=["unit_price", "gross", "diskon_rp", "netto"],
                                          number_cols=["qty"], pct_cols=["diskon_efektif_pct"]),
                             use_container_width=True, hide_index=True)
    else:
        st.caption("Belum ada diskon tercatat.")

    head("Harga di bawah kebiasaan", "Harga satuan lebih rendah dari harga yang paling sering dipakai (barang + satuan sama)", AMBER)
    explain("Tiap transaksi dibandingkan dengan harga yang paling sering dipakai untuk barang+satuan yang sama (minimal 5 transaksi). "
            "<b>Tidak semua ini kebocoran.</b> Pembelian jumlah besar (≥3× jumlah biasa) kemungkinan sengaja diberi harga grosir, "
            "jadi dipisahkan. Yang perlu dicek adalah yang <b>jumlahnya normal tapi harganya turun</b>. "
            "Selisih >50% tidak dihitung di sini karena lebih mungkin salah pilih satuan (lihat tab Kualitas Data).")
    if not leak_sum.empty:
        ls = leak_sum[~leak_sum["band"].str.startswith("4.")]
        total_all = ls["selisih_rp"].sum()
        total_normal = ls["selisih_rp_qty_normal"].sum()
        m1, m2 = st.columns(2)
        m1.metric("Selisih qty normal (perlu dicek)", id_rp_short(total_normal))
        m2.metric("Selisih pembelian besar (kemungkinan grosir)", id_rp_short(total_all - total_normal))
        insight(f"Batas atas kebocoran harga ≈ <b>{id_rp_short(total_normal)}</b> selama periode data. "
                "Angka ini baru bisa dipastikan kalau toko punya daftar harga grosir tertulis sebagai pembanding.")
        fig = px.bar(ls, x="minggu", y="selisih_rp_qty_normal", color="band",
                     color_discrete_sequence=[GREY, AMBER, RUST])
        fig.update_layout(xaxis_title="Minggu mulai", yaxis_title="Selisih qty normal (Rp)", legend_title=None)
        fig.update_yaxes(tickformat=",.0f")
        st.plotly_chart(style_fig(fig, 300), use_container_width=True)
    if not leak.empty:
        with st.expander("📋 100 transaksi qty normal dengan selisih terbesar"):
            st.dataframe(styled_table(leak[["tanggal", "no_faktur", "penginput", "nama_barang", "unit", "qty", "median_qty_grup",
                                            "harga_modus", "harga_transaksi", "dibawah_modus_pct", "selisih_rp"]],
                                      currency_cols=["harga_modus", "harga_transaksi", "selisih_rp"],
                                      number_cols=["qty", "median_qty_grup"], pct_cols=["dibawah_modus_pct"]),
                         use_container_width=True, hide_index=True)

# ==================================================================
# TAB: BRAND
# ==================================================================
with tab_brand:
    brand = num(sbs("v_tp_brand_share", "order=omzet.desc"),
                ["faktur", "sku", "omzet", "share_total_pct", "share_dalam_segmen_pct", "diskon_rp", "pct_baris_diskon"])
    head("Brand dalam tiap segmen", "Siapa yang menguasai rak di tiap kelompok barang", VIOLET)
    explain("Field brand di Accurate kosong, jadi brand <b>ditebak dari nama barang/kategori</b> (mis. 'RUCIKA', 'TIGA RODA'). "
            "Bagian '(tidak terdeteksi)' = barang yang namanya tidak memuat brand yang dikenali. "
            "Brand yang menguasai satu segmen adalah bahan negosiasi ke distributor — sekaligus risiko kalau pasokannya terganggu.")
    if not brand.empty:
        seg_tot = brand.groupby("segmen", as_index=False)["omzet"].sum().sort_values("omzet", ascending=False)
        pilih_seg = st.selectbox("Pilih segmen:", seg_tot["segmen"].tolist(), key="pilih_segmen_brand")
        b = brand[brand["segmen"] == pilih_seg].sort_values("omzet", ascending=True)
        col_a, col_b = st.columns([1.2, 1])
        with col_a:
            fig = px.bar(b, x="share_dalam_segmen_pct", y="brand", orientation="h", text="share_dalam_segmen_pct")
            fig.update_traces(marker_color=VIOLET, texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(xaxis_title="% omzet dalam segmen", yaxis_title=None)
            st.plotly_chart(style_fig(fig, 360), use_container_width=True)
        with col_b:
            st.dataframe(styled_table(b.sort_values("omzet", ascending=False)[
                ["brand", "omzet", "share_dalam_segmen_pct", "share_total_pct", "faktur", "sku", "pct_baris_diskon"]],
                currency_cols=["omzet"], number_cols=["faktur", "sku"],
                pct_cols=["share_dalam_segmen_pct", "share_total_pct", "pct_baris_diskon"]),
                use_container_width=True, hide_index=True, height=360)
        dom = brand[(brand["brand"] != "(tidak terdeteksi)") & (brand["share_dalam_segmen_pct"] >= 50)]
        if not dom.empty:
            r = dom.sort_values("omzet", ascending=False).iloc[0]
            total_disk = brand["diskon_rp"].sum()
            porsi_disk = 100 * brand.loc[brand["brand"] == r["brand"], "diskon_rp"].sum() / total_disk if total_disk else 0
            teks = (f"<b>{r['brand']}</b> menguasai <b>{id_pct(r['share_dalam_segmen_pct'])}</b> segmen {r['segmen']} "
                    f"({id_pct(r['share_total_pct'])} dari total omzet toko). ")
            if porsi_disk >= 50:
                teks += (f"Brand ini juga menyerap <b>{id_pct(porsi_disk)} dari seluruh diskon</b> toko — pertanyaan kuncinya: "
                         "berapa diskon yang toko sendiri terima dari distributornya? Kalau mirip, margin bisa sangat tipis.")
            else:
                teks += "Posisi dominan ini bisa jadi bahan negosiasi harga beli ke distributor."
            insight(teks)

        head("Porsi omzet per segmen", "", GREY)
        fig = px.bar(seg_tot, x="segmen", y="omzet")
        fig.update_traces(marker_color=GREY)
        fig.update_layout(xaxis_title=None, yaxis_title="Omzet (Rp)")
        fig.update_yaxes(tickformat=",.0f")
        st.plotly_chart(style_fig(fig, 300), use_container_width=True)

# ==================================================================
# TAB: STOK & KATALOG
# ==================================================================
with tab_stok:
    must = num(sbs("v_tp_must_have_sku", "order=hari_terjual.desc,omzet.desc"),
               ["hari_terjual", "faktur", "qty", "omzet", "hari_transaksi", "pct_hari_terjual", "stok_master"])
    sleep_cat = num(sbs("v_tp_sleeping_sku_by_category", "order=sku_belum_terjual.desc"),
                    ["sku_master", "sku_terjual", "sku_belum_terjual", "pct_belum_terjual",
                     "sku_tidur_dgn_stok_positif", "omzet_kategori"])

    head("Barang yang wajib selalu ada", "Terjual di sebagian besar hari toko buka", TEAL)
    explain("<b>Kelas A</b> = terjual di ≥50% hari toko buka, <b>Kelas B</b> = 25–50% hari. Kalau barang kelas A kosong, "
            "pembeli hampir pasti datang dan pulang tanpa beli. Kolom stok diambil dari master Accurate, yang "
            "<b>belum bisa dipercaya</b> (saldo awal & pembelian belum dicatat) — jadi daftar ini paling berguna sebagai "
            "<b>urutan prioritas stock opname</b>: hitung fisik barang-barang ini dulu.")
    if not must.empty:
        a = must[must["kelas"].str.startswith("A")]
        omzet_total = float(daily["omzet"].astype(float).sum()) if not daily.empty else 0
        m1, m2, m3 = st.columns(3)
        m1.metric("SKU kelas A", id_num(len(a)))
        m2.metric("Omzet kelas A", id_rp_short(a["omzet"].sum()),
                  f"{id_pct(100 * a['omzet'].sum() / omzet_total if omzet_total else 0)} dari total")
        m3.metric("Kelas A dgn stok master ≤ 0", id_num(a["catatan_stok"].notna().sum()))
        insight(f"Hanya <b>{id_num(len(a))} SKU</b> tapi menyumbang <b>{id_rp_short(a['omzet'].sum())}</b>. "
                "Kalau stock opname dilakukan bertahap, mulai dari daftar ini — usaha kecil, risiko kehabisan barang terbesar tertutup.")
        kelas = st.radio("Tampilkan:", ["A. Wajib ada", "B. Sering", "Semua"], horizontal=True, key="kelas_must")
        show = must if kelas == "Semua" else must[must["kelas"].str.startswith(kelas[0])]
        st.dataframe(styled_table(show[["kelas", "nama_barang", "kategori", "hari_terjual", "hari_transaksi",
                                        "pct_hari_terjual", "qty", "omzet", "stok_master", "unit_master", "terakhir_terjual"]],
                                  currency_cols=["omzet"], number_cols=["hari_terjual", "hari_transaksi", "qty", "stok_master"],
                                  pct_cols=["pct_hari_terjual"]),
                     use_container_width=True, hide_index=True)

    head("Katalog yang belum pernah terjual", "SKU di master Accurate tanpa satu pun transaksi sejak go-live", GREY)
    explain("Ini <b>bukan</b> daftar 'stok mati'. Hampir semua SKU di sini stoknya 0 di sistem — artinya masalahnya "
            "<b>katalog master yang terlalu gemuk</b> (ratusan varian motif/ukuran), bukan uang yang tertahan di gudang. "
            "Uang tertahan baru bisa diukur setelah saldo stok di Accurate dibenahi. Jangan hapus SKU berdasarkan tabel ini "
            "sebelum data mencakup minimal ±3 bulan — banyak barang bangunan memang lambat tapi tetap dibutuhkan.")
    if not sleep_cat.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("SKU di master", id_num(sleep_cat["sku_master"].sum()))
        m2.metric("Belum pernah terjual", id_num(sleep_cat["sku_belum_terjual"].sum()),
                  f"{id_pct(100 * sleep_cat['sku_belum_terjual'].sum() / max(sleep_cat['sku_master'].sum(), 1))}")
        m3.metric("…yang stok sistemnya > 0", id_num(sleep_cat["sku_tidur_dgn_stok_positif"].sum()))
        top = sleep_cat.head(15).sort_values("sku_belum_terjual")
        fig = go.Figure()
        fig.add_bar(y=top["kategori"], x=top["sku_terjual"], orientation="h", name="Pernah terjual", marker_color=TEAL)
        fig.add_bar(y=top["kategori"], x=top["sku_belum_terjual"], orientation="h", name="Belum terjual", marker_color="#D5DAE0")
        fig.update_layout(barmode="stack", xaxis_title="Jumlah SKU", yaxis_title=None, legend_title=None)
        st.plotly_chart(style_fig(fig, 460), use_container_width=True)
        with st.expander("📋 Lihat daftar SKU belum terjual per kategori"):
            kat = st.selectbox("Kategori:", sleep_cat["kategori"].dropna().tolist(), key="kat_sleep")
            if kat:
                det = num(sbs("v_tp_sleeping_sku_detail", f"kategori=eq.{quote(str(kat))}&order=nama.asc&limit=500"),
                          ["stok", "cost", "harga_jual"])
                if not det.empty:
                    st.dataframe(styled_table(det, currency_cols=["cost", "harga_jual"], number_cols=["stok"]),
                                 use_container_width=True, hide_index=True)

# ==================================================================
# TAB: STAF & HARI
# ==================================================================
with tab_staf:
    wl = num(sbs("v_tp_staff_workload_dow", "order=dow.asc"),
             ["dow", "hari_buka_toko", "hari_aktif", "faktur", "faktur_per_hari_aktif", "faktur_toko_per_hari",
              "porsi_faktur_pct", "omzet"])
    prof = num(sbs("v_tp_staff_profile", "order=faktur.desc"),
               ["hari_aktif", "faktur", "omzet", "rata2_faktur", "median_faktur", "rata2_baris_per_faktur",
                "rata2_segmen_per_faktur", "pct_faktur_diatas_1jt", "diskon_rp", "pct_baris_diskon", "potensi_salah_unit"])

    head("Beban kerja per hari", "Rata-rata faktur per hari buka, dan siapa yang menginput", BLUE)
    explain("Bahan untuk menyusun jadwal jaga: hari yang paling ramai butuh orang paling banyak. "
            "Catatan: tiap hari baru punya 3–4 contoh, jadi selisih kecil antar-hari masih bisa kebetulan.")
    if not wl.empty:
        toko = wl.groupby(["dow", "hari"], as_index=False).agg(faktur_toko_per_hari=("faktur_toko_per_hari", "max"),
                                                               hari_buka=("hari_buka_toko", "max")).sort_values("dow")
        col_a, col_b = st.columns([1, 1.2])
        with col_a:
            fig = px.bar(toko, x="hari", y="faktur_toko_per_hari", text="faktur_toko_per_hari")
            fig.update_traces(marker_color=BLUE, texttemplate="%{text:.0f}", textposition="outside")
            fig.update_layout(xaxis_title=None, yaxis_title="Faktur / hari buka")
            st.plotly_chart(style_fig(fig, 320), use_container_width=True)
            ramai = toko.loc[toko["faktur_toko_per_hari"].idxmax()]
            sepi = toko.loc[toko["faktur_toko_per_hari"].idxmin()]
            insight(f"<b>{ramai['hari']}</b> paling ramai (±{id_num(ramai['faktur_toko_per_hari'])} faktur/hari), "
                    f"<b>{sepi['hari']}</b> paling sepi (±{id_num(sepi['faktur_toko_per_hari'])}). "
                    f"Kalau ada staf paruh waktu, prioritaskan jadwalnya di {ramai['hari']}.")
        with col_b:
            pv = wl.pivot_table(index="penginput", columns="hari", values="hari_aktif", aggfunc="sum").fillna(0)
            order = [h for h in ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"] if h in pv.columns]
            pv = pv[order]
            hb = toko.set_index("hari")["hari_buka"]
            fig = px.imshow(pv, text_auto=True, aspect="auto", color_continuous_scale=[[0, "#EDEFF2"], [1, BLUE]])
            fig.update_layout(coloraxis_showscale=False, xaxis_title=None, yaxis_title=None,
                              title=dict(text="Jumlah hari aktif menginput (dari " +
                                         ", ".join(f"{h[:3]} {int(hb.get(h, 0))}" for h in order) + " hari buka)",
                                         font=dict(size=12, color=TEXT_MUTED)))
            st.plotly_chart(style_fig(fig, 320), use_container_width=True)

    head("Profil penginput", "Untuk bahan pelatihan, bukan penilaian kinerja", GREY)
    explain("Perbedaan rata-rata nilai faktur antar staf bisa karena <b>siapa yang kebetulan melayani pembeli proyek</b>, "
            "bukan karena kemampuan menjual. Yang paling bisa langsung ditindaklanjuti adalah kolom "
            "<b>potensi salah satuan</b> — itu kebutuhan pelatihan input, dan dampaknya ke stok nyata.")
    if not prof.empty:
        prof["salah_unit_per_100_faktur"] = (100 * prof["potensi_salah_unit"] / prof["faktur"].where(prof["faktur"] > 0)).round(1)
        with st.expander("👤 Tampilkan profil per penginput"):
            st.dataframe(styled_table(prof[["penginput", "hari_aktif", "faktur", "median_faktur", "rata2_faktur",
                                            "rata2_baris_per_faktur", "pct_faktur_diatas_1jt", "segmen_utama",
                                            "pct_baris_diskon", "diskon_rp", "potensi_salah_unit", "salah_unit_per_100_faktur"]],
                                      currency_cols=["median_faktur", "rata2_faktur", "diskon_rp"],
                                      number_cols=["hari_aktif", "faktur", "potensi_salah_unit"],
                                      pct_cols=["pct_faktur_diatas_1jt", "pct_baris_diskon"]),
                         use_container_width=True, hide_index=True)

# ==================================================================
# TAB 5: KUALITAS DATA
# ==================================================================
with tab_kualitas:
    st.markdown(
        f'<div class="tp-insight" style="border-left-color:{GREY}">🔍 Tab ini memantau kesehatan data, bukan performa bisnis — '
        "baris di sini kemungkinan besar salah input, dicek dulu sebelum dijadikan dasar keputusan.</div>",
        unsafe_allow_html=True,
    )

    price_var = sb("v_tp_item_price_variance", "order=rentang_persen.desc&limit=25")
    recency = sb("v_tp_item_recency", "order=hari_sejak_terakhir_terjual.desc&limit=20")
    unit_errors = sb("v_tp_potential_unit_errors", "order=potensi_selisih_rp.desc&limit=100")

    head("⚠️ Potensi salah satuan yang berdampak ke uang", "Transaksi yang harganya menyimpang jauh dari pola biasa", RUST)
    explain(
        "Tiap transaksi dibandingkan dengan harga yang <b>paling sering dipakai</b> untuk kombinasi barang+satuan yang sama. "
        "Kalau menyimpang jauh, ditampilkan di sini beserta perkiraan selisih uangnya. "
        "<b>PENTING — ini bisa berarti dua hal berbeda, harus dicek manual ke penginputnya:</b><br>"
        "① <b>Uang benar-benar kurang/lebih diterima</b> — kasir memang mengenakan harga yang salah ke pembeli.<br>"
        "② <b>Uang sudah benar, cuma label satuan yang salah dipilih di sistem</b> — misalnya bermaksud jual 15 SAK dengan harga SAK yang benar, "
        "tapi di sistem ke-pilih satuan 'KG'. Uang yang diterima kemungkinan tetap benar, tapi <b>stok jadi salah tercatat</b> "
        "(sistem mengurangi 15 KG dari stok, padahal fisik yang keluar 15 SAK = 750 KG) — ini tetap perlu dibenahi meski bukan soal uang."
    )
    if not unit_errors.empty:
        st.dataframe(
            styled_table(
                unit_errors[["no_faktur", "tanggal", "penginput", "kode_barang", "nama_barang", "unit",
                             "harga_modus", "harga_transaksi_ini", "qty", "uang_tercatat",
                             "uang_seharusnya_jika_ikut_modus", "potensi_selisih_rp"]],
                currency_cols=["harga_modus", "harga_transaksi_ini", "uang_tercatat",
                               "uang_seharusnya_jika_ikut_modus", "potensi_selisih_rp"],
                number_cols=["qty"], color_col="potensi_selisih_rp", invert_color=True,
            ),
            use_container_width=True, hide_index=True,
        )
        total_selisih = unit_errors["potensi_selisih_rp"].astype(float).sum()
        n_kurang = (unit_errors["potensi_selisih_rp"].astype(float) > 0).sum()
        n_lebih = (unit_errors["potensi_selisih_rp"].astype(float) < 0).sum()
        insight(f"Dari {len(unit_errors)} transaksi mencurigakan: <b>{n_kurang} berpotensi uang kurang tercatat</b>, "
                f"<b>{n_lebih} berpotensi lebih</b> (bersih {id_rp(total_selisih)}). "
                "Cek dulu langsung ke faktur aslinya di Accurate dan tanya penginputnya sebelum menyimpulkan ini kerugian nyata — "
                "kemungkinan besar sebagian besar cuma salah label satuan, bukan salah kasih harga ke pembeli.")
    else:
        st.caption("Belum ada transaksi yang menyimpang cukup jauh untuk ditandai.")

    head("Variasi harga jual (SKU + satuan yang sama)", "", GREY)
    explain("Barang dengan rentang harga sangat lebar (>90%) di satuan yang SAMA biasanya bukan diskon nyata — "
            "sering kali kasir salah pilih satuan (misal pilih 'per KG' padahal maksudnya 'per SAK'). "
            "Tapi hati-hati: kalau harga yang sama dipakai KONSISTEN oleh banyak kasir di banyak tanggal, itu justru "
            "kebijakan harga yang disengaja (mis. jual eceran per-KG memang lebih mahal per-satuan berat dibanding beli per-SAK utuh) — "
            "bukan kesalahan. Yang perlu dicek adalah baris yang MENYIMPANG dari pola mayoritasnya.")
    if not price_var.empty:
        st.dataframe(styled_table(price_var, currency_cols=["harga_terendah", "harga_tertinggi", "harga_rata2"],
                                   number_cols=["jumlah_baris_transaksi", "jumlah_harga_berbeda"], pct_cols=["rentang_persen"]),
                     use_container_width=True, hide_index=True)

        st.markdown("**🔍 Telusuri per barang — lihat faktur, tanggal, dan penginputnya**")
        price_var_disp = price_var.copy()
        price_var_disp["_label"] = price_var_disp["kode_barang"] + " — " + price_var_disp["nama_barang"].fillna("") + " (" + price_var_disp["unit"] + ")"
        label_to_pair = dict(zip(price_var_disp["_label"], zip(price_var_disp["kode_barang"], price_var_disp["unit"])))
        pilihan = st.selectbox("Pilih barang untuk ditelusuri:", price_var_disp["_label"].tolist(), key="pilih_price_var")
        if pilihan:
            kode_pilih, unit_pilih = label_to_pair[pilihan]
            detail = sb("v_tp_item_price_variance_detail",
                        f"kode_barang=eq.{quote(str(kode_pilih))}&unit=eq.{quote(str(unit_pilih))}&order=unit_price.asc")
            if not detail.empty:
                st.dataframe(
                    styled_table(detail[["no_faktur", "tanggal", "penginput", "qty", "unit_price", "total_price"]],
                                 currency_cols=["unit_price", "total_price"], number_cols=["qty"]),
                    use_container_width=True, hide_index=True,
                )
                explain("Baris paling atas/bawah (harga paling beda dari mayoritas) adalah kandidat pertama untuk dicek ke penginputnya — "
                        "tanyakan apakah waktu itu memang bermaksud jual di satuan tersebut atau salah pilih di kasir.")

    head("Barang paling lama tidak terjual", "", GREY)
    explain("PERINGATAN: data baru mencakup periode pendek (mulai 31 Agustus 2026). 'Lama tidak terjual' di sini "
            "bisa berarti barang itu cuma terjual sekali di awal periode data — BUKAN berarti barang itu benar-benar "
            "mati total. Indikator ini akan jauh lebih bisa dipercaya begitu data terkumpul beberapa bulan.")
    if not recency.empty:
        st.dataframe(styled_table(recency, number_cols=["total_qty_alltime", "hari_sejak_terakhir_terjual"]),
                     use_container_width=True, hide_index=True)

# ======================================================================
# SIDEBAR
# ======================================================================
st.sidebar.markdown("### 🧱 Toko Pertiwi")
st.sidebar.caption("Sumber: Supabase, auto-sync tiap malam ±21:00 WIB. Cache 5 menit.")
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Catatan kualitas data**
- `harga_jual` master TIDAK reliable — semua analisa pakai harga transaksi riil
- HPP baru ada di sebagian kecil SKU — margin belum representatif
- Field satuan (`unit`) kadang salah input kasir
- Rentang data masih pendek — tren akan makin tajam seiring waktu
- Nama pelanggan kosong di hampir semua faktur — pembeli besar belum bisa dikenali
- Stok master belum andal (saldo awal & pembelian belum dicatat di Accurate)
- Brand dideteksi dari nama barang (field brand Accurate kosong)
""")
