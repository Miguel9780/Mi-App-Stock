import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Control de Stock", page_icon="📦", layout="wide")
st.title("📊 Consulta de Stock en Tiempo Real")

# --- LÓGICA: Leer directamente de GitHub ---
# Asegúrate de subir tu Excel con este nombre exacto
NOMBRE_ARCHIVO = "datos_stock.xlsx"
DIAS_TOTALES = 30

if os.path.exists(NOMBRE_ARCHIVO):
    try:
        # 1️⃣ EXTRAER FECHA (Celda G2 -> Columna 7, Fila 2)
        df_fecha = pd.read_excel(NOMBRE_ARCHIVO, sheet_name="PRINCIPAL", header=None, nrows=2, usecols="G")
        fecha_g2 = df_fecha.iloc[1, 0]
        dia_actual = fecha_g2.day if isinstance(fecha_g2, datetime) else 1
        
        dias_restantes = DIAS_TOTALES - dia_actual + 1
        
        # 2️⃣ PROCESAR DATOS (Búsqueda de fila de encabezados)
        df_raw = pd.read_excel(NOMBRE_ARCHIVO, sheet_name="PRINCIPAL", header=None)
        # Buscamos la fila que contenga la palabra 'CÓDIGO' en cualquier celda
        fila_encabezado = next(i for i, row in df_raw.iterrows() if "CÓDIGO" in row.values or "CODIGO" in row.values)
        
        # Leemos los datos completos
        df = pd.read_excel(NOMBRE_ARCHIVO, sheet_name="PRINCIPAL", skiprows=fila_encabezado)
        df.columns = df.columns.astype(str).str.strip() # Limpieza básica de nombres
        
        # Mapeo posicional directo por índice de columna de Excel (A=0, B=1...)
        # Para garantizar que lea la columna correcta sin importar el nombre
        # H=7, K=10, M=12, Q=16, R=17, S=18, BJ=61
        col_cod = next((c for c in df.columns if c.upper() in ['CÓDIGO', 'CODIGO']), 'CÓDIGO')
        col_desc = next((c for c in df.columns if c.upper() in ['DESCRIPCIÓN', 'DESCRIPCION']), 'DESCRIPCIÓN')
        
        # 3️⃣ BUSCADOR DINÁMICO (Optimizado para móvil)
        # Limpiamos filas que no tengan un código válido
        df = df.dropna(subset=[col_cod])
        # Creamos columna de búsqueda combinada
        df['Busqueda'] = df[col_cod].astype(str) + " - " + df[col_desc].astype(str)
        
        entrada_usuario = st.text_input("Escribe el CÓDIGO o la DESCRIPCIÓN del producto:")

        if entrada_usuario:
            # Filtramos las coincidencias que contengan el texto del usuario
            coincidencias = df[df['Busqueda'].str.contains(entrada_usuario, case=False, na=False)]
            
            if len(coincidencias) == 0:
                st.warning("No se encontraron productos con ese nombre o código.")
            elif len(coincidencias) > 1:
                # Si hay múltiples coincidencias, pedimos al usuario elegir una
                seleccion = st.selectbox("Se encontraron varios resultados. Elige uno:", coincidencias['Busqueda'])
                # Obtenemos los datos de la fila seleccionada
                res = coincidencias[coincidencias['Busqueda'] == seleccion].iloc[0]
                mostrar_analisis = True
            else:
                # Si solo hay una, la seleccionamos automáticamente
                res = coincidencias.iloc[0]
                mostrar_analisis = True
            
            # --- SECCIÓN DE ANÁLISIS ---
            if 'mostrar_analisis' in locals():
                # Extracción y conversión de datos críticos por índice
                try:
                    plan_mes_h = pd.to_numeric(res.iloc[7], errors='coerce') # Col H
                    avance_k = pd.to_numeric(res.iloc[10], errors='coerce') # Col K
                    otra_vta_q = pd.to_numeric(res.iloc[16], errors='coerce') # Col Q
                    avance_r = pd.to_numeric(res.iloc[17], errors='coerce') # Col R
                    stock_cedi_s = pd.to_numeric(res.iloc[18], errors='coerce') # Col S
                    porc_vta_m = pd.to_numeric(res.iloc[12], errors='coerce') # Col M
                    texto_causa_bj = res.iloc[61] # Col BJ (No numérico)
                except Exception as ex:
                    st.error(f"Error al extraer los datos de las columnas críticas: {ex}")
                    mostrar_analisis = False

                if mostrar_analisis:
                    if plan_mes_h <= 0 or pd.isna(plan_mes_h):
                        st.warning(f"⚪ {res[col_desc]}: Producto descontinuado o sin plan.")
                    else:
                        # --- CÁLCULOS SEGÚN NUEVOS REQUERIMIENTOS ---
                        # Mejora 3: Venta Diaria Teórica Objetiva (Plan / 30)
                        venta_diaria_calculo = plan_mes_h / DIAS_TOTALES
                        stock_min_req = venta_diaria_calculo * dias_restantes
                        
                        # Mejora 1: Avance Vta. (K + R)
                        total_avance_kr = avance_k + avance_r
                        
                        # Datos para diagnóstico de agotado (K + Q)
                        diagnostico_vta_actual_kq = avance_k + otra_vta_q

                        # --- VISUALIZACIÓN DE MÉTRICAS (Stacked para celular) ---
                        st.divider()
                        st.subheader("Métricas Clave del Producto")
                        
                        m1, m2 = st.columns(2)
                        with m1:
                            st.metric("Plan Demanda (H)", f"{int(plan_mes_h):,}")
                            # Mejora 1: Visualización del nuevo cálculo
                            st.metric("Avance Vta. (K+R)", f"{int(total_avance_kr):,}")
                            # Mejora 3: Visualización de la nueva métrica
                            st.metric("Venta Diaria Teórica (H/30)", f"{venta_diaria_calculo:.2f}")

                        with m2:
                            st.metric("%V Mes Actual (M)", f"{porc_vta_m:.2%}" if not pd.isna(porc_vta_m) else "0.00%")
                            st.metric("Stock CEDI (Col S)", f"{int(stock_cedi_s):,}" if not pd.isna(stock_cedi_s) else "0")

                        # --- ALERTAS DE QUIEBRE Y CAUSA RAÍZ ---
                        if stock_cedi_s < stock_min_req:
                            faltante = stock_min_req - stock_cedi_s
                            
                            # Construcción del mensaje de error con diagnóstico
                            mensaje_error = f"🚨 **QUIEBRE:** Faltan {faltante:,.2f} uds. para los {dias_restantes} días restantes."
                            
                            # Mejora 2: Diagnóstico Causa Raíz
                            if diagnostico_vta_actual_kq > plan_mes_h:
                                # Condición 2.A: Sobreventa
                                diagnostico_causa = "\n\n**Causa de agotado:** Sobreventa (Venta total acumulada supera el plan de demanda)."
                            else:
                                # Condición 2.B: Otro agotado (Registrado en BJ)
                                diagnostico_causa = f"\n\n**Causa de agotado (BJ):** {texto_causa_bj}"
                            
                            st.error(mensaje_error + diagnostico_causa)
                        else:
                            st.success(f"✅ **STOCK OK:** Tienes cobertura suficiente para cerrar el mes.")

    except Exception as e:
        st.error(f"Error crítico al leer los datos de '{NOMBRE_ARCHIVO}'. Detalles técnicos: {e}")
else:
    st.info(f"El archivo '{NOMBRE_ARCHIVO}' no se encuentra en el repositorio. Por favor, súbelo.")
