import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuración de la página (Optimizado para móvil)
st.set_page_config(page_title="Control de Stock Ventas", page_icon="📦", layout="wide")

# 1. TÍTULO Y FECHA DEL REPORTE
st.title("📊 Consulta de Stock y Disponibilidad")

# --- CONFIGURACIÓN DE ARCHIVO ---
NOMBRE_ARCHIVO = "datos_stock.xlsx"
DIAS_TOTALES = 30

@st.cache_data(ttl=300)
def cargar_datos(ruta):
    if os.path.exists(ruta):
        try:
            # Leer fecha de la celda G2 (Columna G = Índice 6)
            df_fecha = pd.read_excel(ruta, sheet_name="PRINCIPAL", header=None, nrows=2, usecols="G")
            fecha_g2 = df_fecha.iloc[1, 0]
            
            # Buscar fila de encabezados
            df_raw = pd.read_excel(ruta, sheet_name="PRINCIPAL", header=None)
            fila_header = next(i for i, row in df_raw.iterrows() if "CÓDIGO" in row.values or "CODIGO" in row.values)
            
            # Cargar datos limpios
            df = pd.read_excel(ruta, sheet_name="PRINCIPAL", skiprows=fila_header)
            df.columns = df.columns.astype(str).str.strip()
            return df, fecha_g2
        except Exception as e:
            st.error(f"Error al leer el Excel: {e}")
            return None, None
    return None, None

df, fecha_original = cargar_datos(NOMBRE_ARCHIVO)

# MEJORA 2: Mostrar la fecha debajo del título
if fecha_original is not None:
    if isinstance(fecha_original, datetime):
        fecha_mostrar = fecha_original.strftime('%d/%m/%Y')
    else:
        fecha_mostrar = str(fecha_original)
    st.markdown(f"##### 📅 Fecha del reporte: {fecha_mostrar}")
    st.divider()

if df is not None:
    dia_actual = fecha_original.day if isinstance(fecha_original, datetime) else 1
    dias_restantes = DIAS_TOTALES - dia_actual + 1
    
    col_cod = next((c for c in df.columns if c.upper() in ['CÓDIGO', 'CODIGO']), 'CÓDIGO')
    col_desc = next((c for c in df.columns if c.upper() in ['DESCRIPCIÓN', 'DESCRIPCION']), 'DESCRIPCIÓN')
    
    df = df.dropna(subset=[col_cod])
    df['Busqueda'] = df[col_cod].astype(str) + " - " + df[col_desc].astype(str)

    # --- BUSCADOR ---
    entrada_usuario = st.text_input("🔍 Ingresa Código o Descripción del producto:")

    if entrada_usuario:
        coincidencias = df[df['Busqueda'].str.contains(entrada_usuario, case=False, na=False)]
        
        if len(coincidencias) == 0:
            st.warning("No se encontró el producto. Verifica la información.")
        elif len(coincidencias) > 1:
            seleccion = st.selectbox("Se encontraron varios. Elige el correcto:", coincidencias['Busqueda'])
            res = coincidencias[coincidencias['Busqueda'] == seleccion].iloc[0]
            listo = True
        else:
            res = coincidencias.iloc[0]
            listo = True

        if 'listo' in locals():
            st.success("✅ **PRODUCTO IDENTIFICADO:**")
            st.markdown(f"### {res[col_desc]}")
            st.caption(f"Código: {res[col_cod]}")
            
            # --- EXTRACCIÓN SEGURA ---
            def limpiar_num(valor):
                n = pd.to_numeric(valor, errors='coerce')
                return 0 if pd.isna(n) else n

            # H=7, K=10, M=12, Q=16, R=17, S=18, BJ=61
            plan_h = limpiar_num(res.iloc[7])
            avance_k = limpiar_num(res.iloc[10])
            porc_m = limpiar_num(res.iloc[12])
            vta_q = limpiar_num(res.iloc[16])
            vta_r = limpiar_num(res.iloc[17])
            stock_s = limpiar_num(res.iloc[18])
            
            # MEJORA 1: Extraer BJ y limpiar texto
            causa_bj = str(res.iloc[61]).strip() if not pd.isna(res.iloc[61]) else ""

            # Mostrar comentario de BJ siempre que tenga contenido relevante
            if causa_bj != "" and causa_bj.lower() != "nan" and causa_bj.lower() != "0":
                st.info(f"💬 **Comentario del Planificador:** {causa_bj}")

            if plan_h <= 0:
                st.warning("⚪ Producto descontinuado o sin plan de demanda registrado.")
            else:
                # --- CÁLCULOS ---
                # Venta Diaria Teórica: $$ \frac{Plan}{30} $$
                vta_diaria_teorica = plan_h / DIAS_TOTALES
                avance_total_kr = avance_k + vta_r
                stock_min_req = vta_diaria_teorica * dias_restantes
                suma_kq = avance_k + vta_q

                # --- MÉTRICAS ---
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Plan Demanda (H)", f"{int(plan_h):,}")
                    st.metric("Avance Vta. (K+R)", f"{int(avance_total_kr):,}")
                    st.metric("Venta Diaria Teórica", f"{int(vta_diaria_teorica):,}")

                with c2:
                    st.metric("Stock CEDI (S)", f"{int(stock_s):,}")
                    st.metric("%V Mes Actual (M)", f"{porc_m:.2%}")

                # --- LÓGICA DE QUIEBRE ---
                if stock_s < stock_min_req:
                    faltante = stock_min_req - stock_s
                    st.error(f"🚨 **QUIEBRE DE STOCK:** Faltan aprox. {int(faltante):,} unidades para cerrar el mes.")
                    
                    if suma_kq > plan_h:
                        st.warning("🚩 **Causa detectada por sistema:** Sobreventa")
                else:
                    st.success("✅ **STOCK SUFICIENTE:** Hay cobertura para los días restantes.")

else:
    st.info("Sube el archivo 'datos_stock.xlsx' a GitHub para activar la consulta.")
