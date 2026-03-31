import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Control de Stock", page_icon="📦", layout="wide")
st.title("📊 Análisis de Quiebre de Stock")

archivo = st.file_uploader("Cargar Reporte de Stock", type=["xlsx"])

if archivo:
    try:
        # 1️⃣ EXTRAER FECHA (Celda G2)
        df_fecha = pd.read_excel(archivo, sheet_name="PRINCIPAL", header=None, nrows=2, usecols="G")
        fecha_g2 = df_fecha.iloc[1, 0]
        dia_actual = fecha_g2.day if isinstance(fecha_g2, datetime) else 1
        
        DIAS_TOTALES = 30
        dias_restantes = DIAS_TOTALES - dia_actual + 1
        
        # 2️⃣ PROCESAR DATOS
        df_raw = pd.read_excel(archivo, sheet_name="PRINCIPAL", header=None)
        fila_encabezado = next(i for i, row in df_raw.iterrows() if "CÓDIGO" in row.values or "CODIGO" in row.values)
        
        df = pd.read_excel(archivo, sheet_name="PRINCIPAL", skiprows=fila_encabezado)
        df.columns = df.columns.astype(str).str.strip()
        
        # Identificación de columnas por posición y nombre
        col_cod = next((c for c in df.columns if c.upper() in ['CÓDIGO', 'CODIGO']), 'CÓDIGO')
        col_desc = next((c for c in df.columns if c.upper() in ['DESCRIPCIÓN', 'DESCRIPCION']), 'DESCRIPCIÓN')
        
        # Mapeo directo por letras de Excel:
        # Columna M -> Índice 12 | Columna S -> Índice 18
        df['PORCENTAJE_M'] = pd.to_numeric(df.iloc[:, 12], errors='coerce')
        df['STOCK_S'] = pd.to_numeric(df.iloc[:, 18], errors='coerce')

        # 3️⃣ BUSCADOR DINÁMICO (Ingreso de texto)
        df = df.dropna(subset=[col_cod])
        df['Busqueda'] = df[col_cod].astype(str) + " - " + df[col_desc].astype(str)
        
        entrada_usuario = st.text_input("Escribe el CÓDIGO o la DESCRIPCIÓN:")

        if entrada_usuario:
            # Filtramos coincidencias
            coincidencias = df[df['Busqueda'].str.contains(entrada_usuario, case=False, na=False)]
            
            if len(coincidencias) == 0:
                st.warning("No se encontraron productos.")
            elif len(coincidencias) > 1:
                # Si hay varias, pedimos elegir una de la lista filtrada
                seleccion = st.selectbox("Se encontraron varios resultados. Selecciona el correcto:", coincidencias['Busqueda'])
                res = coincidencias[coincidencias['Busqueda'] == seleccion].iloc[0]
                mostrar_analisis = True
            else:
                # Si solo hay una, la seleccionamos directo
                res = coincidencias.iloc[0]
                mostrar_analisis = True
            
            if 'mostrar_analisis' in locals():
                # 4️⃣ CÁLCULOS
                pd_mes = pd.to_numeric(res.get('Plan de demanda', 0), errors='coerce')
                vta_actual = pd.to_numeric(res.get('Avance Vta.', 0), errors='coerce')
                stock_cedi = res['STOCK_S']
                porc_vta = res['PORCENTAJE_M']
                
                if pd_mes <= 0 or pd.isna(pd_mes):
                    st.warning(f"⚪ {res[col_desc]}: Producto descontinuado")
                else:
                    vta_diaria_obj = pd_mes / DIAS_TOTALES
                    stock_min_req = vta_diaria_obj * dias_restantes
                    
                    # 5️⃣ VISUALIZACIÓN
                    st.divider()
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Plan de Demanda", f"{int(pd_mes):,}")
                    c2.metric("Avance Vta.", f"{int(vta_actual):,}")
                    
                    # Formato centésimo para porcentaje (0.1234 -> 12.34%)
                    c3.metric("%V Mes Actual (Col M)", f"{porc_vta:.2%}" if not pd.isna(porc_vta) else "0.00%")
                    c4.metric("Stock CEDI (Col S)", f"{int(stock_cedi):,}" if not pd.isna(stock_cedi) else "0")

                    if stock_cedi < stock_min_req:
                        faltante = stock_min_req - stock_cedi
                        st.error(f"🚨 **QUIEBRE:** Faltan {faltante:,.2f} uds. para los {dias_restantes} días restantes.")
                    else:
                        st.success(f"✅ **STOCK OK:** Tienes cobertura para cerrar el mes.")

    except Exception as e:
        st.error(f"Error: {e}")