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

# Función para optimizar la lectura (Caché para 200 usuarios)
@st.cache_data(ttl=600) # Se actualiza cada 10 min si hay cambios
def cargar_datos(ruta):
    if os.path.exists(ruta):
        # 1. Leer fecha de G2
        df_fecha = pd.read_excel(ruta, sheet_name="PRINCIPAL", header=None, nrows=2, usecols="G")
        fecha_g2 = df_fecha.iloc[1, 0]
        
        # 2. Leer datos principales
        df_raw = pd.read_excel(ruta, sheet_name="PRINCIPAL", header=None)
        fila_header = next(i for i, row in df_raw.iterrows() if "CÓDIGO" in row.values or "CODIGO" in row.values)
        
        df = pd.read_excel(ruta, sheet_name="PRINCIPAL", skiprows=fila_header)
        df.columns = df.columns.astype(str).str.strip()
        return df, fecha_g2
    return None, None

df, fecha_original = cargar_datos(NOMBRE_ARCHIVO)

if df is not None:
    # Cálculo de días
    dia_actual = fecha_original.day if isinstance(fecha_original, datetime) else 1
    dias_restantes = DIAS_TOTALES - dia_actual + 1
    
    # Identificar columnas
    col_cod = next((c for c in df.columns if c.upper() in ['CÓDIGO', 'CODIGO']), 'CÓDIGO')
    col_desc = next((c for c in df.columns if c.upper() in ['DESCRIPCIÓN', 'DESCRIPCION']), 'DESCRIPCIÓN')
    
    # Limpieza
    df = df.dropna(subset=[col_cod])
    df['Busqueda'] = df[col_cod].astype(str) + " - " + df[col_desc].astype(str)

    # --- INTERFAZ DE BÚSQUEDA ---
    entrada_usuario = st.text_input("🔍 Ingresa Código o Descripción del producto:")

    if entrada_usuario:
        coincidencias = df[df['Busqueda'].str.contains(entrada_usuario, case=False, na=False)]
        
        if len(coincidencias) == 0:
            st.warning("No se encontró el producto. Verifica el código.")
        elif len(coincidencias) > 1:
            seleccion = st.selectbox("Se encontraron varios productos. Selecciona el correcto:", coincidencias['Busqueda'])
            res = coincidencias[coincidencias['Busqueda'] == seleccion].iloc[0]
            listo = True
        else:
            res = coincidencias.iloc[0]
            listo = True

        if 'listo' in locals():
            # --- VALIDACIÓN VISUAL (Mejora solicitada) ---
            st.success(f"✅ **PRODUCTO IDENTIFICADO:**")
            st.subheader(f"{res[col_desc]}") # Muestra la descripción en grande
            st.caption(f"Código: {res[col_cod]}")
            
            # --- EXTRACCIÓN DE DATOS POR ÍNDICE ---
            plan_h = pd.to_numeric(res.iloc[7], errors='coerce')      # H
            avance_k = pd.to_numeric(res.iloc[10], errors='coerce')   # K
            porc_vta_m = pd.to_numeric(res.iloc[12], errors='coerce')# M
            vta_q = pd.to_numeric(res.iloc[16], errors='coerce')     # Q
            vta_r = pd.to_numeric(res.iloc[17], errors='coerce')     # R
            stock_s = pd.to_numeric(res.iloc[18], errors='coerce')   # S
            causa_bj = res.iloc[61]                                  # BJ

            if plan_h <= 0 or pd.isna(plan_h):
                st.warning("⚪ Este producto figura como descontinuado o sin plan de demanda.")
            else:
                # CÁLCULOS
                vta_diaria_teorica = plan_h / DIAS_TOTALES
                stock_min_req = vta_diaria_teorica * dias_restantes
                avance_total_kr = avance_k + avance_r
                suma_kq = avance_k + vta_q

                # --- MÉTRICAS ---
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Plan Demanda (H)", f"{int(plan_h):,}")
                    st.metric("Avance Vta. (K+R)", f"{int(avance_total_kr):,}")
                    # Mejora: Venta Diaria Teórica sin decimales y con miles
                    st.metric("Venta Diaria Teórica", f"{int(vta_diaria_teorica):,}")

                with col2:
                    st.metric("Stock CEDI (S)", f"{int(stock_s):,}")
                    st.metric("%V Mes Actual", f"{porc_vta_m:.2%}" if not pd.isna(porc_vta_m) else "0.00%")

                # --- LÓGICA DE QUIEBRE ---
                if stock_s < stock_min_req:
                    st.error(f"🚨 **QUIEBRE DE STOCK:** Faltan {int(stock_min_req - stock_s):,} unidades.")
                    
                    if suma_kq > plan_h:
                        st.info("⚠️ **Causa de agotado:** Sobreventa")
                    else:
                        st.info(f"🔍 **Diagnóstico (BJ):** {causa_bj}")
                else:
                    st.success("✅ **STOCK SUFICIENTE:** Hay cobertura para los días restantes.")

else:
    st.info("A la espera del archivo 'datos_stock.xlsx' en el repositorio.")
