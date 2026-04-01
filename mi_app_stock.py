import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuración de la página
st.set_page_config(page_title="Control de Stock Ventas", page_icon="📦", layout="wide")

# Título de la App
st.title("📊 Consulta de Stock y Disponibilidad")

# --- LÓGICA DE CARGA DE DATOS ---
NOMBRE_ARCHIVO = "datos_stock.xlsx"
DIAS_TOTALES = 30

@st.cache_data(ttl=600)
def cargar_datos(ruta):
    if os.path.exists(ruta):
        try:
            df_fecha = pd.read_excel(ruta, sheet_name="PRINCIPAL", header=None, nrows=2, usecols="G")
            fecha_g2 = df_fecha.iloc[1, 0]
            
            df_raw = pd.read_excel(ruta, sheet_name="PRINCIPAL", header=None)
            fila_header = next(i for i, row in df_raw.iterrows() if "CÓDIGO" in row.values or "CODIGO" in row.values)
            
            df = pd.read_excel(ruta, sheet_name="PRINCIPAL", skiprows=fila_header)
            df.columns = df.columns.astype(str).str.strip()
            return df, fecha_g2
        except Exception as e:
            st.error(f"Error técnico al leer el Excel: {e}")
            return None, None
    return None, None

df, fecha_original = cargar_datos(NOMBRE_ARCHIVO)

if df is not None:
    # Cálculo de días
    dia_actual = fecha_original.day if isinstance(fecha_original, datetime) else 1
    dias_restantes = DIAS_TOTALES - dia_actual + 1
    
    col_cod = next((c for c in df.columns if c.upper() in ['CÓDIGO', 'CODIGO']), 'CÓDIGO')
    col_desc = next((c for c in df.columns if c.upper() in ['DESCRIPCIÓN', 'DESCRIPCION']), 'DESCRIPCIÓN')
    
    df = df.dropna(subset=[col_cod])
    df['Busqueda'] = df[col_cod].astype(str) + " - " + df[col_desc].astype(str)

    # --- INTERFAZ DE BÚSQUEDA ---
    entrada_usuario = st.text_input("🔍 Ingresa Código o Descripción del producto:")

    if entrada_usuario:
        coincidencias = df[df['Busqueda'].str.contains(entrada_usuario, case=False, na=False)]
        
        if len(coincidencias) == 0:
            st.warning("No se encontró el producto. Verifica el código o nombre.")
        elif len(coincidencias) > 1:
            seleccion = st.selectbox("Se encontraron varios productos. Selecciona el correcto:", coincidencias['Busqueda'])
            res = coincidencias[coincidencias['Busqueda'] == seleccion].iloc[0]
            listo = True
        else:
            res = coincidencias.iloc[0]
            listo = True

        if 'listo' in locals():
            # --- 1. MOSTRAR DESCRIPCIÓN PARA VALIDAR (Mejora solicitada) ---
            st.success("✅ **PRODUCTO IDENTIFICADO:**")
            st.subheader(f"{res[col_desc]}") # Descripción en grande
            st.info(f"Código: {res[col_cod]}")
            
            # --- EXTRACCIÓN DE DATOS POR POSICIÓN (Índices actualizados) ---
            plan_h = pd.to_numeric(res.iloc[7], errors='coerce')      # H
            avance_k = pd.to_numeric(res.iloc[10], errors='coerce')   # K
            porc_vta_m = pd.to_numeric(res.iloc[12], errors='coerce')# M
            vta_q = pd.to_numeric(res.iloc[16], errors='coerce')     # Q
            vta_r = pd.to_numeric(res.iloc[17], errors='coerce')     # R
            stock_s = pd.to_numeric(res.iloc[18], errors='coerce')   # S
            causa_bj = res.iloc[61]                                  # BJ

            if pd.isna(plan_h) or plan_h <= 0:
                st.warning("⚪ Este producto figura como descontinuado o no tiene plan de demanda.")
            else:
                # --- CÁLCULOS ---
                # Venta Diaria Teórica (H / 30)
                vta_diaria_teorica = plan_h / DIAS_TOTALES
                # Avance Vta (K + R)
                avance_total_kr = (avance_k if not pd.isna(avance_k) else 0) + (avance_r if not pd.isna(avance_r) else 0)
                # Necesidad para días restantes
                stock_min_req = vta_diaria_teorica * dias_restantes
                # Sumatoria para diagnóstico (K + Q)
                suma_kq = (avance_k if not pd.isna(avance_k) else 0) + (vta_q if not pd.isna(vta_q) else 0)

                # --- MÉTRICAS VISUALES ---
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Plan Demanda (H)", f"{int(plan_h):,}")
                    st.metric("Avance Vta. (K+R)", f"{int(avance_total_kr):,}")
                    # Venta Diaria Teórica con miles y sin decimales
                    st.metric("Venta Diaria Teórica", f"{int(vta_diaria_teorica):,}")

                with c2:
                    st.metric("Stock CEDI (S)", f"{int(stock_s):,}" if not pd.isna(stock_s) else "0")
                    st.metric("%V Mes Actual (M)", f"{porc_vta_m:.2%}" if not pd.isna(porc_vta_m) else "0.00%")

                # --- LÓGICA DE QUIEBRE Y DIAGNÓSTICO ---
                if (stock_s if not pd.isna(stock_s) else 0) < stock_min_req:
                    faltante = stock_min_req - (stock_s if not pd.isna(stock_s) else 0)
                    st.error(f"🚨 **QUIEBRE DE STOCK:** Faltan aproximadamente {int(faltante):,} unidades para cubrir el mes.")
                    
                    # Diagnóstico de causa
                    if suma_kq > plan_h:
                        st.warning("🚩 **Causa de agotado:** Sobreventa")
                    else:
                        st.info(f"🔍 **Diagnóstico (BJ):** {causa_bj}")
                else:
                    st.success("✅ **STOCK SUFICIENTE:** Hay cobertura para los días restantes del mes.")

else:
    st.info("A la espera de que se cargue el archivo 'datos_stock.xlsx' en el repositorio.")
