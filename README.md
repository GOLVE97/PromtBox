# PromptBox

Biblioteca personal de prompts para Windows. Guarda las instrucciones localmente, organízalas por categorías, busca en su contenido y conserva favoritos.

## Funciones

- Crear, editar y eliminar prompts.
- Organizar prompts en categorías personalizadas, incluidas categorías vacías.
- Buscar por título, contenido o etiquetas.
- Marcar favoritos y copiarlos al portapapeles.
- Importar y exportar respaldos JSON, con prompts y categorías.
- Elegir tema claro, oscuro o automático.
- Guardar los prompts en una base SQLite local.

## Instalar la versión portable

1. Descarga y extrae `PromptBox-1.0.0-Windows-x64-portable.zip`.
2. Abre `PromptBox.exe`.

El ejecutable no requiere que Python esté instalado. Es una aplicación portable: no instala un servicio ni se actualiza automáticamente. El ejecutable de esta versión no está firmado, así que Windows puede mostrar una advertencia de SmartScreen.

## Datos y privacidad

La base de datos y las preferencias se guardan en:

```text
%USERPROFILE%\AppData\Local\PromptBox
```

PromptBox no sube el contenido de la biblioteca. Usa **Exportar** para crear un respaldo JSON que puedas guardar o importar en otro perfil. Los respaldos nuevos también incluyen categorías vacías; los respaldos anteriores que solo contienen prompts siguen siendo compatibles.

## Ejecutar desde el código fuente

1. Instala Python 3.12 o posterior.
2. Clona o descarga este repositorio.
3. Ejecuta `run.bat`.

## Pruebas y compilación

Ejecuta las pruebas con:

```text
python -m unittest discover -s tests -v
```

Para generar el ejecutable en Windows, ejecuta `build.bat`. Si PyInstaller no está instalado en el Python activo, el script lo instala y luego lo invoca como módulo para no depender de que `pyinstaller.exe` esté en `PATH`. El resultado queda en `dist\PromptBox.exe`.

El flujo **Build and test Windows app** de GitHub Actions ejecuta las pruebas antes de compilar y conserva el ejecutable como artefacto durante 30 días.

## Estado de la versión

Versión 1.0.0 en preparación. El paquete generado es un ZIP portable de Windows x64; no es un instalador firmado ni un paquete MSIX de Microsoft Store. TinyDock (`tinydock.pro`) publica fichas de proyectos y enlaza las descargas externamente: no aloja ni distribuye ejecutables. La ficha de PromptBox debe apuntar a un enlace público estable para el ZIP, como el activo de un release de GitHub. El paquete todavía no tiene ese enlace y no se ha enviado la ficha.
