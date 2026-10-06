# Reunión semanal/mensual — contexto para retomar en otro equipo

Este archivo existe para que una sesión de Claude Code/Antigravity en **otro
computador** (sin el historial de chat de este equipo) pueda retomar el trabajo de
construir las reuniones de "Reunión semanal" sin perder contexto. Léelo primero antes
de tocar nada de `presentacion/` o `disponibilidad/`.

## 0. Cómo dejar el otro equipo listo (una sola vez)

1. Clonar el repo: `git clone https://github.com/alexbaier-svg/gestionCM.git`
2. Crear entorno virtual e instalar dependencias:
   ```
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```
3. Autenticarse en Railway (NO copiar claves a mano — queda ligado a la cuenta):
   ```
   railway login
   railway link      # elegir el proyecto "responsible-renewal", servicio "web"
   ```
4. Para correr comandos contra producción, obtener la URL pública de la base **en el
   momento** (no guardarla en ningún archivo):
   ```
   railway variables --service Postgres --json
   ```
   Buscar `DATABASE_PUBLIC_URL` (la interna `postgres.railway.internal` no resuelve
   fuera de la red de Railway). Usarla así, solo en memoria de la sesión de la terminal:
   ```
   DATABASE_URL="<DATABASE_PUBLIC_URL>" DJANGO_SETTINGS_MODULE=config.settings \
     python manage.py shell -c "..."
   ```
5. Local (SQLite) sirve solo para **desarrollo de código** (importador, plantillas,
   modelos): `python manage.py migrate` + `python manage.py runserver`. No contiene
   reuniones ni datos reales, y no es necesario copiarlos desde producción (ver sección 2).

**Nunca** commitear `DATABASE_URL`, contraseñas de Postgres, ni `SECRET_KEY` al repo —
están en `.gitignore` (`.env*`) a propósito. Si alguna vez quedan en un script de
`scratchpad`, ese directorio es temporal y fuera del repo, no se sube a git.

## 1. Qué es el sistema de "Reunión semanal"

App `presentacion/`. Modelos:
- `Reunion(fecha unique, titulo)` — una reunión por fecha.
- `Diapositiva(reunion FK, orden, titulo, plantilla, contexto JSONField)` — cada
  diapositiva referencia una plantilla HTML genérica en
  `presentacion/templates/presentacion/diapositivas/` y le pasa datos vía `contexto`.

No hay UI de edición: las reuniones se construyen/corrigen con scripts Python corridos
vía `manage.py shell -c "..."` (ver patrón más abajo) **directamente contra el Postgres
de producción**, que es la **única fuente de verdad** de las reuniones. No se mantiene
una copia local de reuniones ni de datos reales (decisión del 06/10/2026): evita tener
dos bases que se desalineen y no trae a disco/OneDrive datos de contacto del personal
médico.

Relaciones útiles: `Reunion.diapositivas` (related_name; no `diapositiva_set`).

## 2. Patrón de trabajo para construir/corregir una reunión

1. **Leer primero** el estado actual en producción (solo lectura): `Reunion` por fecha y
   el `contexto` de la diapositiva a tocar.
2. Escribir un script Python autocontenido en el scratchpad de la sesión (no en el
   repo) que haga el cálculo o cree/actualice `Reunion`/`Diapositiva`. Modificar solo
   las claves necesarias del `contexto`, sin reemplazarlo completo.
3. Correrlo contra producción (con `DATABASE_URL` apuntando a `DATABASE_PUBLIC_URL`,
   solo en memoria de la terminal) y verificar el `contexto` guardado:
   ```
   DATABASE_URL="<DATABASE_PUBLIC_URL>" DJANGO_SETTINGS_MODULE=config.settings \
     python manage.py shell -c "exec(open(r'RUTA_SCRATCHPAD\script.py', encoding='utf-8').read())"
   ```
4. Local solo se usa para probar **cambios de código** (plantillas, importador). Si la
   plantilla cambia, hay commit + push a `master` para que Railway la despliegue.

Notas: `railway link` queda asociado a la carpeta; si en una terminal aparece "No linked
project found", repetir `railway link` (proyecto `responsible-renewal`, entorno
`production`, servicio `web`).

## 3. Estructura estándar de una reunión semanal

Tomando como referencia la reunión del 25/08/2026 (fijada como estándar), el orden de
diapositivas es:
1. Ocupación Infraestructura (`ocupacion_infraestructura.html`) — % ocupación por mes,
   lista de ingresos de médicos nuevos si aplica.
2. Oferta por Especialidad — semana actual (`oferta_especialidad.html`).
3. Comparativo Bloqueos Semanas (`comparativo_mensual.html`) — semana actual vs.
   anterior.
4. Meta del mes en curso (`meta_agosto.html` — el nombre de archivo quedó así pero se
   usa para cualquier mes) — tabla de ventas semanales + meta + consultas diarias
   necesarias.
5. Comparativo Venta año contra año (`meta_venta.html`) — venta acumulada a la fecha,
   año actual vs. año anterior.
6. Experiencia Paciente (`experiencia_paciente.html`) — Total/ACHS/No Ley, acumulado
   mes.
7. Usabilidad Autopago (`usabilidad_autopago_semanal.html`) — **serie histórica
   semanal + promedio** (nunca reemplazar por un solo dato: siempre agregar la semana
   nueva a la lista `stats` existente y recalcular el promedio).

### Cierre de mes

Mismo esquema pero: Oferta por Especialidad es del **mes completo** (proyección al
cierre, no solo la semana), se agrega Comparativo Oferta/Bloqueos mes vs. mes anterior,
y la sección de Metas pasa a mostrar venta **real final** del mes (no parcial).

## 4. Lógica de cálculo de Oferta/Bloqueos — bugs ya corregidos (no repetir)

Todo vive en `disponibilidad/importador.py`. **Tres bugs reales** se encontraron y
corrigieron en esta app durante el desarrollo — quedan documentados porque si alguien
"simplifica" el importador sin saber esto, los vuelve a introducir:

1. **Matching por nombre exacto fallaba** con variantes de nombre (agregar/quitar un
   segundo nombre). Se resolvió con `_ResolvedorMedicos`: usa primero
   `Medico.id_recurso_oferta` (ID numérico estable del sistema externo, aprendido y
   guardado la primera vez que el nombre calza), luego nombre exacto normalizado, luego
   subconjunto de palabras si resuelve sin ambigüedad.
2. **Vigencia de Oferta ignorada**: un mismo médico puede tener varias filas de
   "oferta" en el archivo con rangos `Validodesde`/`Validohasta` distintos (plantillas
   de semanas distintas, incluso futuras) — sumarlas todas duplica su disponibilidad.
   Se filtra por si una fecha de referencia cae dentro del rango.
3. **Vigencia de Bloqueos mal calculada** (el más grave, corregido último): a
   diferencia de Oferta, cada fila de Bloqueos tiene un rango acotado al evento puntual
   (una licencia de un día, una cirugía de una tarde), no una plantilla de semanas. Hay
   además **tres tipos**: `Partial` (recurrente, desglosado en la hoja
   `HorariosBloqueos`), `WholeDay` y `Range` (día/hora puntual, **sin fila en
   `HorariosBloqueos`** — el propio rango `Validodesde`/`Validohasta`, con hora
   incluida, ES el período bloqueado). Los tipos `WholeDay`/`Range` se estaban
   descartando por completo. Ahora se filtra por **traslape de rango** con toda la
   semana que se está importando (no por si una sola fecha cae dentro), y se generan
   bloqueos día por día a partir del propio rango cuando no hay horario desglosado.

Si una semana muestra "pocos bloqueos" y no tiene sentido, **sospechar primero de este
tercer punto** antes de asumir que los datos están bien.

## 5. Checklist — qué pedirle al usuario antes de armar la reunión

**Siempre:**
- Archivos `ExportarOferta-YYYYMMDD.xlsx` y `ExportarBloqueos-YYYYMMDD.xlsx` subidos
  por el importador del sitio (no por script salvo que el usuario no tenga acceso al
  sitio en ese momento).

**Cada semana:**
- Experiencia Paciente (Total / ACHS / No Ley, acumulado del mes).
- % Usabilidad Autopago de la semana.
- Venta de la semana (para la tabla de Metas).

**Cada mes (cierre):**
- Venta real final del mes y del mismo mes año anterior.
- Meta del mes siguiente, venta más alta del mismo mes año anterior, consultas diarias
  necesarias para la meta.
- % Ocupación Infraestructura del mes siguiente (y si hay ingresos/egresos de médicos
  que informar).

## 6. Pendientes conocidos (a la fecha de este documento)

- **~33 nombres de médicos** aparecen bloqueados en los archivos de Bloqueos pero no
  existen en el mantenedor `Medico` (ej. Andrés Jorquera Escanilla, Fernando Riquelme
  Pereira, Glenda Cedeño Medina, Joaquín Cristi Pereira, entre otros). El usuario
  decidió explícitam, al 05/10/2026, **no agregarlos** ("estos no corresponden") —
  seguir calculando solo con los médicos ya cargados a menos que el usuario pida lo
  contrario.
- Revisar el caso de **Fisiatría al 100% de bloqueo** en la semana del 5-10 de octubre
  (puede ser legítimo — un solo médico con un bloqueo de día completo — pero vale la
  pena confirmarlo con el usuario si se repite).
- Ver también la sección "Pendientes" de `DOCUMENTACION.md` para temas del resto del
  sistema (no específicos de reuniones).
