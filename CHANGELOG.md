# Historial de cambios

## 1.0.0 — 2026-11-12
- Evitadas categorías duplicadas por diferencias de mayúsculas, incluso al renombrar o escribir una categoría en el editor.
- Persisten las categorías vacías y se pueden incluir en los respaldos JSON.
- Los respaldos validan los datos antes de importar, conservan la biblioteca ante archivos inválidos y siguen aceptando el formato anterior.
- Las preferencias se validan al iniciar y se escriben mediante reemplazo atómico para reducir el riesgo de archivos incompletos.
- Corregido `build.bat` para ejecutar PyInstaller como módulo de Python y generar un ejecutable portable de Windows.

## 0.5.0
- Implementadas las siete vistas de PromptBox.
- Añadida navegación híbrida con menú lateral y barra superior.
- Añadidos temas claro, oscuro y automático con preferencia persistente.
- Añadidos favoritos y etiquetas con migración SQLite no destructiva.
- Añadida administración de categorías.
- Mejorada la importación/exportación JSON con confirmación y validación.
- Añadida pantalla Acerca de.
- Conservados los datos existentes de la biblioteca.
