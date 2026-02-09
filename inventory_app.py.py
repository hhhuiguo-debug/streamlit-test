import streamlit as st
import pandas as pd
import io
import numpy as np

st.set_page_config(page_title="Amazon 库存管理", layout="wide")
st.title("乌萨奇的二手商店")

# --- 参数配置 ---
growth_factor = st.sidebar.slider("未来 30 天预测增长系数", 0.5, 2.0, 1.0, 0.1)

col1, col2 = st.columns(2)
with col1:
    inv_file = st.file_uploader("1. 上传：补货建议表 (含 FBA 库存/在途)", type=['csv', 'xlsx'])
with col2:
    sales_file = st.file_uploader("2. 上传：产品表现 ASIN 表 (含 30 天销量)", type=['csv', 'xlsx'])

def read_file(file):
    if file is None: return None
    if file.name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(file)
    content = file.read()
    file.seek(0)
    for enc in ['utf-8', 'gbk', 'utf-16']:
        try:
            return pd.read_csv(io.BytesIO(content), encoding=enc)
        except: continue
    return None

# --- 新增：表格着色逻辑 ---
def highlight_low_ratio(row):
    """
    针对库销比 < 2 的行进行高亮：红底、黄字、加粗
    """
    # 设定样式：背景红色，文字黄色，加粗
    highlight = 'background-color: #FF0000; color: #FFFF00; font-weight: bold;'
    default = ''
    
    # 判断条件：库销比 < 2 (且销量大于0，避免标记无销量的死库存)
    if row['库销比'] < 2 and row['过去30天总销量'] > 0:
        return [highlight] * len(row)
    return [default] * len(row)

if inv_file and sales_file:
    df_inv_raw = read_file(inv_file)
    df_sales_raw = read_file(sales_file)

    if df_inv_raw is not None and df_sales_raw is not None:
        try:
            # --- 步骤 1: 销量表清洗 ---
            sales_cols = ['品名', 'SKU', '国家', '销量']
            df_sales = df_sales_raw[sales_cols].copy()
            df_sales['销量'] = pd.to_numeric(df_sales['销量'], errors='coerce').fillna(0)
            
            df_sales_grouped = df_sales.groupby(['国家', 'SKU'], as_index=False).agg({
                '销量': 'sum'
            }).rename(columns={'销量': '过去30天总销量'})

            # --- 步骤 2: 库存表清洗 ---
            inv_target = ['品名', 'SKU', '国家（地区）', 'FBA库存', '入库中', 'FBA在途']
            df_inv = df_inv_raw[inv_target].copy()
            
            for c in ['FBA库存', '入库中', 'FBA在途']:
                df_inv[c] = pd.to_numeric(df_inv[c], errors='coerce').fillna(0)
            
            df_inv['在途总计'] = df_inv['入库中'] + df_inv['FBA在途']
            
            df_inv_grouped = df_inv.groupby(['国家（地区）', '品名', 'SKU'], as_index=False).agg({
                'FBA库存': 'sum',
                '在途总计': 'sum'
            }).rename(columns={'国家（地区）': '国家'})

            # --- 步骤 3: 双表合并 ---
            final_df = pd.merge(df_inv_grouped, df_sales_grouped, on=['国家', 'SKU'], how='left')
            final_df['过去30天总销量'] = final_df['过去30天总销量'].fillna(0)
            
            # --- 步骤 4: 计算预测值 & 库销比 ---
            # 1. 计算未来销量并取整
            final_df['未来30天预估销量'] = (final_df['过去30天总销量'] * growth_factor).round(0).astype(int)
            
            # 2. 计算库销比 = (FBA库存 + 在途总计) / 过去30天销量
            # 使用 np.where 处理销量为 0 的情况，避免出现 inf (无穷大)
            final_df['库销比'] = np.where(
                final_df['过去30天总销量'] > 0,
                (final_df['FBA库存'] + final_df['在途总计']) / final_df['过去30天总销量'],
                99.0 # 无销量时设为一个较大的值
            )
            # 保留一位小数
            final_df['库销比'] = final_df['库销比'].astype(float).round(1)

            # 3. 将其余数值列全部取整
            int_cols = ['FBA库存', '在途总计', '过去30天总销量', '未来30天预估销量']
            final_df[int_cols] = final_df[int_cols].astype(int)

            # 最终排序与展示列
            display_cols = ['国家', '品名', 'SKU', 'FBA库存', '在途总计', '过去30天总销量', '未来30天预估销量', '库销比']
            final_df = final_df[display_cols].sort_values(by=['库销比', '过去30天总销量'], ascending=[True, False])

            st.success(f"✅ 数据整合成功！已标记库销比风险项。")

            # --- 步骤 5: 应用样式渲染 ---
            # 使用 Styler 对象进行渲染
            styled_df = final_df.style.apply(highlight_low_ratio, axis=1).format({
                '库销比': "{:.1f}" # 强制显示一位小数
            })
            
            st.dataframe(styled_df, use_container_width=True)

            # 下载
            output = io.BytesIO()
            final_df.to_excel(output, index=False)
            st.download_button("📥 下载整合分析报告", output.getvalue(), "Amazon_Inventory_Sales_Summary.xlsx")

        except Exception as e:
            st.error(f"❌ 运行错误: {e}")