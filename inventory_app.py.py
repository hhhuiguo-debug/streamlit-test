import streamlit as st
import pandas as pd
import io
import numpy as np
from datetime import datetime, timedelta
import holidays

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="Amazon 智能库存管理", layout="wide", page_icon="🐰")

# --- 2. 初始化会话状态 (用于控制页面切换) ---
if 'entered' not in st.session_state:
    st.session_state.entered = False

# --- 3. 核心算法函数 (保持逻辑严密) ---
def get_ai_prediction(region_name):
    today = datetime.now()
    month = today.month
    factor, reason = 1.0, "市场需求平稳"
    # 2026年3月特定逻辑
    if region_name == "欧洲站 (EU)" and month == 3:
        factor, reason = 1.15, "☘️ 欧洲春季及圣帕特里克节活动"
    elif region_name == "日本" and month == 3:
        factor, reason = 1.3, "🌸 日本樱花/开学季"
    elif region_name == "美国" and month == 3:
        factor, reason = 1.15, "☘️ 圣帕特里克节/春季促销"
    elif region_name == "英国" and month == 3:
        factor, reason = 1.12, "☘️ 英国春季促销期"
    return factor, reason

def style_specific_cells(df):
    style_df = pd.DataFrame('', index=df.index, columns=df.columns)
    red_style = 'background-color: #FF4B4B; color: white; font-weight: bold;'
    mask = (df['库销比'] < 2) & (df['近30天销量'] > 0)
    style_df.loc[mask, '品名'] = red_style
    style_df.loc[mask, '库销比'] = red_style
    return style_df

def read_file(file):
    if file is None: return None
    try:
        if file.name.endswith(('.xlsx', '.xls')):
            return pd.read_excel(file)
        content = file.read()
        file.seek(0)
        for enc in ['utf-8', 'gbk', 'utf-16']:
            try: return pd.read_csv(io.BytesIO(content), encoding=enc)
            except: continue
    except: pass
    return None

# ==========================================
# 页面渲染逻辑：封面 vs 主系统
# ==========================================

if not st.session_state.entered:
    # --- 方案 A：赛博乌萨奇·智能入口 ---
    st.markdown("""
        <style>
        .main-title {
            font-size: 3.5rem !important;
            font-weight: 800;
            background: -webkit-linear-gradient(#ff4b4b, #ffc107);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 0px;
        }
        .sub-quote {
            text-align: center;
            color: #888;
            font-style: italic;
            margin-bottom: 30px;
        }
        .stButton>button {
            background-color: #ff4b4b;
            color: white;
            border-radius: 20px;
            height: 3.5em;
            width: 100%;
            font-weight: bold;
            border: none;
            transition: 0.3s;
            box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3);
        }
        .stButton>button:hover {
            background-color: #ff3333;
            box-shadow: 0 6px 20px rgba(255, 75, 75, 0.5);
            transform: translateY(-2px);
        }
        </style>
    """, unsafe_allow_html=True)

    _, col_mid, _ = st.columns([1, 2, 1])
    
    with col_mid:
        st.write("#")
        st.write("#")
        st.markdown("<h1 style='text-align: center;'>🐰✨🔮</h1>", unsafe_allow_html=True)
        st.markdown("<div class='main-title'>Amazon 库存管理</div>", unsafe_allow_html=True)
        st.markdown("<p class='sub-quote'>“与其被动补货，不如先人一步进行库存管理。”</p>", unsafe_allow_html=True)
        
        with st.container():
            st.info("""
            **📢 实时情报：** - 2026 樱花季预测模型已就绪 🌸
            - 欧洲站圣帕特里克节权重已注入 ☘️
            - 库销比风险监控雷达：已开启 🚨
            """)

        st.write("#")
        if st.button("开启赛博预言 · 进入系统"):
            with st.spinner('正在同步全球节假日频率...'):
                st.session_state.entered = True
                st.rerun()
            
        st.write("#")
        st.markdown("---")
        st.markdown("""
            <div style='text-align: center; color: #555; font-size: 0.9em;'>
                <b>Version 2.6</b> | <span style='color: #ff4b4b;'>♥</span> Powered by GOC代运营
            </div>
        """, unsafe_allow_html=True)

else:
    # --- 方案 B：原本的主功能首页 ---
    if st.sidebar.button("← 退出罗盘"):
        st.session_state.entered = False
        st.rerun()

    st.title("🐰 Amazon 库存管理")
    st.write(f"🕒 **系统预测基准日：{datetime.now().strftime('%Y年%m月%d日')}**") 
    st.divider()

    # --- 侧边栏 ---
    st.sidebar.header("⚙️ 预测引擎设置")
    manual_mode = st.sidebar.checkbox("手动覆盖 AI 建议系数")
    global_manual_factor = st.sidebar.slider("手动系数", 0.5, 3.0, 1.0, 0.1) if manual_mode else 1.0

    # --- 上传区 ---
    col1, col2 = st.columns(2)
    with col1:
        inv_file = st.file_uploader("1. 载入：补货建议表", type=['csv', 'xlsx'])
    with col2:
        sales_file = st.file_uploader("2. 载入：产品表现表", type=['csv', 'xlsx'])

    if inv_file and sales_file:
        df_inv_raw = read_file(inv_file)
        df_sales_raw = read_file(sales_file)

        if df_inv_raw is not None and df_sales_raw is not None:
            try:
                # 1. 归类逻辑
                def unify_region(c):
                    c = str(c).upper()
                    eu_list = ['德国', '法国', '意大利', '西班牙', '荷兰', 'DE', 'FR', 'IT', 'ES', 'NL', 'GERMANY', 'FRANCE', 'ITALY', 'SPAIN', 'NETHERLANDS']
                    if any(k in c for k in eu_list): return "欧洲站 (EU)"
                    if "日本" in c or "JP" in c: return "日本"
                    if "美国" in c or "US" in c: return "美国"
                    if "英国" in c or "UK" in c or "GB" in c: return "英国"
                    return c

                # 2. 清洗数据
                df_sales = df_sales_raw[['SKU', '国家', '销量']].copy()
                df_sales['国家'] = df_sales['国家'].apply(unify_region)
                df_sales['销量'] = pd.to_numeric(df_sales['销量'], errors='coerce').fillna(0)
                df_sales = df_sales.groupby(['国家', 'SKU'], as_index=False).agg({'销量': 'sum'}).rename(columns={'销量': '近30天销量'})

                df_inv = df_inv_raw[['品名', 'SKU', '国家（地区）', 'FBA库存', '入库中', 'FBA在途']].copy()
                df_inv['国家'] = df_inv['国家（地区）'].apply(unify_region)
                for c in ['FBA库存', '入库中', 'FBA在途']:
                    df_inv[c] = pd.to_numeric(df_inv[c], errors='coerce').fillna(0)
                df_inv['在途总计'] = df_inv['入库中'] + df_inv['FBA在途']
                df_inv = df_inv.groupby(['国家', '品名', 'SKU'], as_index=False).agg({'FBA库存':'sum', '在途总计':'sum'})

                # 3. 合并计算
                final_df = pd.merge(df_inv, df_sales, on=['国家', 'SKU'], how='left').fillna(0)
                final_df[['增长系数', '预测依据']] = final_df.apply(lambda r: pd.Series((global_manual_factor, "手动") if manual_mode else get_ai_prediction(r['国家'])), axis=1)
                final_df['未来30天预估'] = (final_df['近30天销量'] * final_df['增长系数']).round(0).astype(int)
                final_df['库销比'] = np.where(final_df['近30天销量'] > 0, (final_df['FBA库存'] + final_df['在途总计']) / final_df['近30天销量'], 99.0)
                final_df['库销比'] = final_df['库销比'].round(1)

                # 4. 分国家展示
                regions = sorted(final_df['国家'].unique())
                tabs = st.tabs(regions)

                for i, reg in enumerate(regions):
                    with tabs[i]:
                        reg_df = final_df[final_df['国家'] == reg].copy()
                        reg_df = reg_df.sort_values(by=['库销比', '近30天销量'], ascending=[True, False])
                        show_cols = ['品名', 'SKU', 'FBA库存', '在途总计', '近30天销量', '增长系数', '未来30天预估', '库销比', '预测依据']
                        styled_df = reg_df[show_cols].style.apply(style_specific_cells, axis=None).format({'增长系数': "{:.2f}", '库销比': "{:.1f}"})
                        st.dataframe(styled_df, use_container_width=True)

                # 5. 导出
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    for reg in regions:
                        reg_df = final_df[final_df['国家'] == reg]
                        reg_df.to_excel(writer, sheet_name=str(reg)[:31], index=False)
                
                st.divider()
                st.download_button("📥 导出分析报告", output.getvalue(), f"Amazon_Inventory_Report_{datetime.now().strftime('%Y%m%d')}.xlsx")

            except Exception as e:
                st.error(f"处理数据时出错: {e}")
