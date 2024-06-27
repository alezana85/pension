import pandas as pd
import numpy as np
from PyPDF2 import PdfReader
from tabula import read_pdf
from datetime import datetime, timedelta


# Leer archivos csv
df_sm = pd.read_csv('pension\sm_uma.csv')
df_cuantia = pd.read_csv('pension\cuantia_basica.csv')
df_porcentajes = pd.read_csv('pension\porcentajes_de_pension.csv')

# si la fecha del dia hoy es primero de enero de cualquier año pedir un input para colocar el año, salario minimo y uma en df_sm
if pd.Timestamp.now().month == 1 and pd.Timestamp.now().day == 1:
    year = input('Ingrese el año: ')
    sm = input('Ingrese el salario minimo: ')
    uma = input('Ingrese el valor de la UMA: ')
    df_sm = df_sm.append({'year': year, 'salario_minimo': sm, 'uma': uma}, ignore_index=True)

# si la fecha del dia de hoy es primero de febrero de cualquier año pedir input para reemplazar la ultima uma que se ingreso
if pd.Timestamp.now().month == 2 and pd.Timestamp.now().day == 1:
    uma = input('Ingrese el valor de la UMA: ')
    df_sm['uma'].iloc[-1] = uma

# Ruta del archivo pdf
archivo_pdf = 'pension\semanas.pdf'

# Inicializar el DataFrame principal donde se almacenarán todas las tablas relevantes
df = pd.DataFrame()
df2 = pd.DataFrame()

# Leer el numero de paginas del pdf
reader = PdfReader(archivo_pdf)
n_paginas = len(reader.pages)

# Iterar sobre cada pagina del pdf
for i in range(n_paginas):
    # Leer la tabla de la pagina i
    tabla = read_pdf(archivo_pdf, pages=i+1)

    # Iterar sobre cada tabla de la pagina i
    for j in range(len(tabla)):
        # Palabras deseadas en la tabla
        palabras_deseables = ['Tipo de movimiento', 'Fecha de movimiento', 'Salario Base']
        # Verificar si la tabla contiene las palabras deseadas sin importar en que posicion se encuentren en el pdf y buscar de manera esctricta aunque las palabras deseables no sean encabezados pero solo mantener los datos que se enceuntren debajo de las palabras deseadas
        if all(palabra in tabla[j].values for palabra in palabras_deseables):
            # Si la tabla contiene las palabras deseadas, agregar los datos de abajo a la tabla principal
            df = pd.concat([df, tabla[j]], ignore_index=True)


# Iterar a través de cada página del PDF
for pagina in range(1, n_paginas + 1):
    # Leer tablas de la página actual
    tablas = read_pdf(archivo_pdf, pages=pagina, multiple_tables=True, pandas_options={'header': 0})
    # Iterar sobre cada tabla encontrada
    for datos in tablas:
        # Verificar si la tabla contiene los encabezados deseados
        encabezados_deseados = {'Tipo de movimiento', 'Fecha de movimiento', 'Salario Base'}
        if encabezados_deseados.issubset(set(datos.columns)):
            # Si la tabla contiene los encabezados, añadirla al DataFrame principal
            df2 = pd.concat([df2, datos], ignore_index=True)

# Eliminar encabezado de df y poner como encabezado la primera fila
df.columns = df.iloc[0]
df = df[1:]
# Eliminar del df las filas que contienen la palabra  'Tipo de movimiento'
df = df[~df['Tipo de movimiento'].str.contains('Tipo de movimiento')]
# Union de los dos dataframes
df = pd.concat([df, df2], ignore_index=True)
# Eliminar el signo de pesos de la columna 'Salario Base' para convertirlo en float
df['Salario Base'] = df['Salario Base'].str.replace('$', '').str.replace(',', '').astype(float)
# convertir la columna 'Fecha de movimiento' a datetime
df['Fecha de movimiento'] = pd.to_datetime(df['Fecha de movimiento'], dayfirst=True)
# Ordenar el dataframe por la columna 'Fecha de movimiento' en orden ascendente
df = df.sort_values(by='Fecha de movimiento', ascending=True).reset_index(drop=True)

# Crear una nueva tabla para sacar las semanas cotizadas
df_semanas = pd.DataFrame(columns=['Fecha de Inicio', 'Fecha de Fin', 'Salario Registrado', 'Semanas Cotizadas', 'Resultado'])
df_semanas = []

# Variables auxiliares para mantener el estado
fecha_inicio = None
fecha_fin = None
salario = None

# Iterar sobre el DataFrame original para construir df_semanas
for index, row in df.iterrows():
    tipo_movimiento = row['Tipo de movimiento']
    fecha_movimiento = row['Fecha de movimiento']
    salario_base = row['Salario Base']

    if tipo_movimiento == 'REINGRESO':
        if fecha_inicio is not None:
            # Guardar la fila actual y reiniciar variables para nueva entrada REINGRESO
            df_semanas.append({
                'Fecha Inicio': fecha_inicio.strftime('%d/%m/%Y'),
                'Fecha Fin': fecha_fin.strftime('%d/%m/%Y') if fecha_fin else '',  # Manejo de fecha_fin None
                'Salario': salario
            })
        
        fecha_inicio = fecha_movimiento
        salario = salario_base

    elif tipo_movimiento == 'BAJA':
        fecha_fin = fecha_movimiento
        salario = salario_base
        df_semanas.append({
            'Fecha Inicio': fecha_inicio.strftime('%d/%m/%Y'),
            'Fecha Fin': fecha_fin.strftime('%d/%m/%Y'),
            'Salario': salario
        })
        fecha_inicio = None
        fecha_fin = None
        salario = None

    elif tipo_movimiento == 'MODIFICACION DE SALARIO':
        if fecha_inicio is not None:
            fecha_fin = fecha_movimiento - pd.Timedelta(days=1)
            df_semanas.append({
                'Fecha Inicio': fecha_inicio.strftime('%d/%m/%Y'),
                'Fecha Fin': fecha_fin.strftime('%d/%m/%Y') if fecha_fin else '',  # Manejo de fecha_fin None
                'Salario': salario
            })
            fecha_inicio = fecha_movimiento
            salario = salario_base
        else:
            fecha_inicio = fecha_movimiento
            salario = salario_base

# Añadir la última entrada después de terminar el loop si hay un REINGRESO sin BAJA posterior
if fecha_inicio is not None:
    df_semanas.append({
        'Fecha Inicio': fecha_inicio.strftime('%d/%m/%Y'),
        'Fecha Fin': fecha_movimiento.strftime('%d/%m/%Y') if fecha_movimiento else '',  # Manejo de fecha_movimiento None
        'Salario': salario
    })

# Convertir la lista de diccionarios en un DataFrame
df_semanas = pd.DataFrame(df_semanas)

# Reemplazar cadenas vacías por NaN en la columna 'Fecha Fin'
df_semanas['Fecha Fin'] = df_semanas['Fecha Fin'].replace('', np.nan)

# Ahora, eliminar filas donde 'Fecha Fin' es NaN
df_semanas = df_semanas.dropna(subset=['Fecha Fin'])

# Convertir las columnas 'Fecha Inicio' y 'Fecha Fin' a datetime
df_semanas['Fecha Inicio'] = pd.to_datetime(df_semanas['Fecha Inicio'], dayfirst=True)
df_semanas['Fecha Fin'] = pd.to_datetime(df_semanas['Fecha Fin'], dayfirst=True)

# Ordenar el DataFrame por 'Fecha Fin' en orden descendente y restablecer el índice
df_semanas = df_semanas.sort_values(by='Fecha Fin', ascending=False).reset_index(drop=True)

# Calcular las semanas cotizadas dando el resultado con decimales en float
df_semanas['Semanas Cotizadas'] = (df_semanas['Fecha Fin'] - df_semanas['Fecha Inicio']).dt.days / 7
df_semanas['Semanas Cotizadas'] = df_semanas['Semanas Cotizadas'].astype(float)

# Eliminar filas con valores negativos en 'Semanas Cotizadas'
df_semanas = df_semanas[df_semanas['Semanas Cotizadas'] >= 0]

# Calcular el resultado
df_semanas['Resultado'] = df_semanas['Salario'] * df_semanas['Semanas Cotizadas']

# Buscar la suma de las semanas cotizadas hasta donde me de 250 semanas si se pasa de 250 semanas se toman hasta antes de que de 250 semanas y se suman los salarios de esas semanas
semanas_acumuladas = 0
salario_promedio = 0
for index, row in df_semanas.iterrows():
    semanas_acumuladas += row['Semanas Cotizadas']
    if semanas_acumuladas <= 250:
        salario_promedio += row['Resultado']
    else:
        salario_promedio += row['Resultado'] - (semanas_acumuladas - 250) * row['Salario']
        break

# Calcular el salario promedio
salario_promedio = salario_promedio / 250

# Solicitar al usuario que se ingrese un fecha
fecha_de_calculo = input('Ingrese la fecha de calculo de la pension (formato dd/mm/aaaa): ')
# Convertir la fecha de calculo en formato datetime
fecha_de_calculo = pd.to_datetime(fecha_de_calculo, format=r'%d/%m/%Y')

# Solicitar al usuario la fecha de nacimiento del pensionado
fecha_de_nacimiento = input('Ingrese la fecha de nacimiento del pensionado (formato dd/mm/aaaa): ')
# Convertir la fecha de nacimiento en formato datetime
fecha_de_nacimiento = pd.to_datetime(fecha_de_nacimiento, format=r'%d/%m/%Y')

# Solicitar al usuario la edad a la que quiere pensionarse
while True:
    edad_de_pension = input('Ingrese la edad a la que se quiere pensionar (solo dos digitos): ')
    if edad_de_pension.isdigit() and len(edad_de_pension) == 2:
        break
    else:
        print('Por favor solo ingrese 2 digitos enteros')
# Convertir la edad_de_pension a int
edad_de_pension = int(edad_de_pension)

# Solicitar al usuario el numero de semanas cotizadas actuales
semanas_cotizadas = input('Ingrese el numero de semanas cotizadas actuales: ')
# Convertir las semanas_cotizadas a int
semanas_cotizadas = int(semanas_cotizadas)

# Solicitar al usuario el numero de semanas cotizadas a recuperar
semanas_a_recuperar = input('Ingrese el numero de semanas cotizadas a recuperar: ')
# Convertir las semanas_a_recuperar a int
semanas_a_recuperar = int(semanas_a_recuperar)

# Solicitar al usuario su situacion laboral
situacion_laboral = input('¿Planea seguir laborando (si/no)?: ').lower()
if situacion_laboral == 'si':
    situacion_laboral = True
    if situacion_laboral == True:
        semanas_a_laborar = input('Ingrese el numero de semanas que seguira cotizando: ')
elif situacion_laboral == 'no':
    situacion_laboral = False
else:
    print('Por favor solo ingrese "si" o "no"')


# Solicitar al usuario su situacion marital
situacion_marital = input('¿Tiene Esposo(a) o Concubino(a)?: ').lower()
if situacion_marital == 'si':
    situacion_marital = True
elif situacion_marital == 'no':
    situacion_marital = False
else:
    print('Por favor solo ingrese "si" o "no"')

# Solicitar al usuario el numero de hijos menores de 16 años
hijos_16 = input('¿Cuantos hijos menores de 16 años tiene?: ')
# Convertir hijos_16 a int
hijos_16 = int(hijos_16)

# Solicitar al usuario el numero de hijos menores de 25 que sean Estudiantes
hijos_25 = input('¿Cuantos hijos menores de 25 años que sigan estudiando tiene?: ')
# Convertir hijos_25 a int
hijos_25 = int(hijos_25)

# Solicitar al usuario si tiene padres que dependan economicamente y cuantos
padres = input('¿Cuntos padres dependen economicamente de usted?: ')
if padres.isdigit():
    padres = int(padres)
    if padres <= 2:
        pass
else:
    print('Por favor ingrese un numero menor a 2')

# Calcular edad actual del pensionado
fecha_actual = pd.Timestamp.now()
edad_actual = (fecha_actual - fecha_de_nacimiento) / pd.Timedelta(days=365.25)
edad_actual = int(edad_actual)

# Calcular las semanas cotizadas a calcular
if situacion_laboral == True:
    total_de_semanas = int(semanas_cotizadas) + int(semanas_a_recuperar) + int(semanas_a_laborar)
else:
    total_de_semanas = int(semanas_cotizadas) + int(semanas_a_recuperar)

# Calcular fecha para el tramite de pension
fecha_de_tramite = fecha_de_nacimiento + timedelta(days=365 * edad_de_pension + 1)

# FACTORES PARA DETERMINAR LA PENSION
# Extraer el año de fecha_de_calculo
year = fecha_de_calculo.year
uma = df_sm.loc[df_sm['year'] == year, 'uma'].values[0]
sm = df_sm.loc[df_sm['year'] == year, 'salario_minimo'].values[0]

# Determinar el salario e umas
salario_en_umas = salario_promedio / uma

# Incremento por decreto del 20/12/2001
incremento_por_decreto = 1.11

# Determinar la cuantia basica de pension
cuantia_basica = df_cuantia.loc[(df_cuantia['DE'] <= salario_en_umas) & (df_cuantia['A'] >= salario_en_umas), '% CUANTIA BASICA'].iloc[0]
cuantia_diaria = salario_promedio * cuantia_basica
cuantia_anual = cuantia_diaria * 365 * incremento_por_decreto

# Determinar la cuantia de incrementos anuales
incremento_cuantia = df_cuantia.loc[(df_cuantia['DE'] <= salario_en_umas) & (df_cuantia['A'] >= salario_en_umas), '% INCREMENTOS ANUALES'].iloc[0]
incremento_diario = salario_promedio * incremento_cuantia
incremento_anual = incremento_diario * 365
n_incremento_anual = (total_de_semanas - 500) / 52
total_incremento_anual = salario_promedio * incremento_cuantia * 365 * incremento_por_decreto * n_incremento_anual

cuantia_total_de_pension = cuantia_anual + total_incremento_anual

# Calcular el monto de la cuantia total segun la edad a la que se va a pensionar
cuantia_total = cuantia_total_de_pension * df_porcentajes.loc[df_porcentajes['Edad'] == edad_de_pension, 'Porcentaje'].values[0]

# ASIGNACIONES FAMILIARES
# Asignacion por matrimonio o concubinato
asignacion_mat = 0.15
total_por_mat = []
if situacion_marital == True:
    total_por_mat = (cuantia_total * asignacion_mat)
else:
    total_por_mat = 0

# Asignaciones por hijos
asignacion_por_hijos = 0.10
n_de_hijos = hijos_16 + hijos_25
total_por_hijos = []
if n_de_hijos > 0:
    total_por_hijos = (cuantia_total * asignacion_por_hijos * n_de_hijos)
else:
    total_por_hijos = 0

# Asignacion por padres
asignacion_por_padres = 0.10
total_por_padres = []
if situacion_marital == False & n_de_hijos == 0 & padres > 0:
    total_por_padres = (cuantia_total * asignacion_por_padres * padres)
else:
    total_por_padres = 0

# Ayuda por soledad
asignacion_soledad = []
if situacion_marital == False & n_de_hijos == 0 & padres == 0 or padres == 1:
    asignacion_soledad = 0.10
else:
    asignacion_soledad = 0.15
total_soledad = []
if situacion_marital == False & n_de_hijos == 0 & padres == 0 or padres == 1:
    total_soledad = (cuantia_total * asignacion_soledad)
else:
    total_soledad = 0

# Sumar la cuantia_total con las asignaciones familiares
pension_anual = cuantia_total + total_por_mat + total_por_hijos + total_por_padres + total_soledad

# Calcular si aplica la pension minima garantizada
pension_minima = sm * 365 * 1.11
total_pension = []
if pension_anual < pension_minima:
    total_pension = pension_minima
else:
    total_pension = pension_anual

pension_mensual = total_pension / 12

# Impimir pension mensual
print(f'Su pensión mensual es de ${pension_mensual:,.2f}')

# Imprimir fehca a la que se puede tramitar la pension
print(f'La fecha en la que puede tramitar su pensión es el {fecha_de_tramite.strftime("%d/%m/%Y")}')
