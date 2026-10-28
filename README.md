# Laboratorio de Optimalidad y Sink Tree

## Archivos
- `app.py`: aplicación Streamlit.
- `requirements.txt`: dependencias.

## Instalación en Windows
1. Instala Python 3.10 o superior y marca **Add Python to PATH**.
2. Descomprime la carpeta del proyecto.
3. Abre CMD dentro de esa carpeta.
4. Ejecuta:

```bat
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

5. Abre `http://localhost:8501` si el navegador no se abre automáticamente.

## Uso
- Cambia retardo, capacidad y disponibilidad en la tabla.
- Elige la función objetivo en la barra lateral.
- Prueba las seis actividades descritas en la guía.
- Descarga los CSV desde la parte inferior de la aplicación.

## Nota sobre los datos
Los retardos de H-D, D-A, A-B, H-E, E-J, J-C, C-B, H-O, O-N y N-J se inicializan con los ejemplos de la guía cuando están disponibles. Los valores de enlaces que la guía no especifica completamente son ilustrativos y se pueden editar.
