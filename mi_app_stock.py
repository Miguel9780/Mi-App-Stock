import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuración de la interfaz
st.set_page_config(page_title="Control de Stock Ventas", page_icon="📦", layout="wide")

# Título principal
st.title("📊 Consulta de Stock y Disponibilidad")

# --- PARÁMETROS DEL SISTEMA ---
NOMBRE_ARCHIVO = "datos_stock.xlsx"
DIAS_TOTALES = 30

@st.cache_data(ttl=300)
def cargar_datos(ruta):
    """Carga y procesa el archivo Excel desde la raíz del proyecto."""
    if os.path.exists(ruta):
        try:
            # Lectura de la fecha en G2 (Fila 2, Columna G)
            df_fecha = pd.read_excel(ruta, sheet_name="PRINCIPAL", header=None, nrows=2, usecols="G")
            fecha_g2 = df_fecha.iloc[1, 0]
            
            # Localización de encabezados buscando la palabra 'CÓDIGO'
            df_raw = pd.read_excel(ruta, sheet_name="PRINCIPAL", header=None)
            fila_header = next(i for i, row in df_raw.iterrows() if "CÓDIGO" in row.values or "CODIGO" in row.values)
            
            # Carga de la tabla principal
            df = pd.read_excel(ruta, sheet_name="PRINCIPAL", skiprows=fila_header)
            df.columns = df.columns.astype(str).str.strip()
            return df, fecha_g2
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            return None, None
    return None, None

# Ejecución de carga
df, fecha_original = cargar_datos(NOMBRE_ARCHIVO)

# MEJORA: Fecha del reporte debajo del título
if fecha_original is not None:
    if isinstance(fecha_original, datetime):
        fecha_texto = fecha_original.strftime('%d/%m/%Y')
    else:
        fecha_texto = str(fecha_original)
    st.markdown(f"##### 📅 Fecha del reporte: {fecha_texto}")
    st.divider()

if df is not None:
    # Cálculo de días restantes basado en la fecha del reporte
    dia_actual = fecha_original.day if isinstance(fecha_original, datetime) else 1
    dias_restantes = DIAS_TOTALES - dia_actual + 1
    
    # Identificación dinámica de columnas de búsqueda
    col_cod = next((c for c in df.columns if c.upper() in ['CÓDIGO', 'CODIGO']), 'CÓDIGO')
    col_desc = next((c for c in df.columns if c.upper() in ['DESCRIPCIÓN', 'DESCRIPCION']), 'DESCRIPCIÓN')
    
    # Preparación de la base para búsqueda
    df = df.dropna(subset=[col_cod])
    df['Busqueda'] = df[col_cod].astype(str) + " - " + df[col_desc].astype(str)

    # Input del usuario
    entrada_usuario = st.text_input("🔍 Ingresa Código o Descripción del producto:")

    if entrada_usuario:
        coincidencias = df[df['Busqueda'].str.contains(entrada_usuario, case=False, na=False)]
        
        if len(coincidencias) == 0:
            st.warning("Producto no encontrado.")
        elif len(coincidencias) > 1:
            seleccion = st.selectbox("Múltiples resultados encontrados. Elige uno:", coincidencias['Busqueda'])
            res = coincidencias[coincidencias['Busqueda'] == seleccion].iloc[0]
            listo = True
        else:
            res = coincidencias.iloc[0]
            listo = True

        if 'listo' in locals():
            # Validación visual inmediata
            st.success("✅ **PRODUCTO IDENTIFICADO:**")
            st.markdown(f"### {res[col_desc]}")
            st.caption(f"Código: {res[col_cod]}")
            
            # Extracción segura de valores numéricos
            def a_numero(valor):
                n = pd.to_numeric(valor, errors='coerce')
                return 0 if pd.isna(n) else n

            # Índices: H=7, K=10, M=12, Q=16, R=17, S=18, BJ=61
            plan_h = a_numero(res.iloc[7])
            avance_k = a_numero(res.iloc[10])
            porc_m = a_numero(res.iloc[12])
            vta_q = a_numero(res.iloc[16])
            vta_r = a_numero(res.iloc[17])
            stock_s = a_numero(res.iloc[18])
            
            # El comentario se extrae aquí pero se muestra al final
            comentario_bj = str(res.iloc[61]).strip() if not pd.isna(res.iloc[61]) else ""

            if plan_h <= 0:
                st.warning("⚪ Producto sin plan de demanda activo.")
            else:
                # Cálculos de negocio
                vta_diaria_teorica = plan_h / DIAS_TOTALES
                avance_total_kr = avance_k + vta_r
                stock_min_necesario = vta_diaria_teorica * dias_restantes
                validacion_sobreventa_kq = avance_k + vta_q

                # Visualización de Métricas en columnas
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Plan Demanda (H)", f"{int(plan_h):,}")
                    st.metric("Avance Vta. (K+R)", f"{int(avance_total_kr):,}")
                    st.metric("Venta Diaria Teórica", f"{int(vta_diaria_teorica):,}")

                with c2:
                    st.metric("Stock CEDI (S)", f"{int(stock_s):,}")
                    st.metric("%V Mes Actual (M)", f"{porc_m:.2%}")

                # Diagnóstico de Stock
                if stock_s < stock_min_necesario:
                    faltante = stock_min_necesario - stock_s
                    st.error(f"🚨 **QUIEBRE DE STOCK:** Faltan aprox. {int(faltante):,} unidades.")
                    
                    if validacion_sobreventa_kq > plan_h:
                        st.warning("🚩 **Causa detectada:** Sobreventa")
                else:
                    st.success("✅ **STOCK SUFICIENTE:** Cobertura adecuada para el cierre de mes.")

            # MEJORA: Comentario del Planificador siempre al final
            if comentario_bj not in ["", "nan", "0", "None"]:
                st.divider()
                st.info(f"💬 **Comentario del Planificador:** {comentario_bj}")

else:
    st.info("Por favor, asegúrate de que el archivo 'datos_stock.xlsx' esté en el repositorio de GitHub.")
