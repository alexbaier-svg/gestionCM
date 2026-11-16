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
5. Experiencia Paciente (`experiencia_paciente.html`) — Total/ACHS/No Ley, acumulado
   mes.
6. Usabilidad Autopago (`usabilidad_autopago_semanal.html`) — **serie histórica
   semanal + promedio** (nunca reemplazar por un solo dato: siempre agregar la semana
   nueva a la lista `stats` existente y recalcular el promedio).

El **Comparativo Venta año contra año** (`meta_venta.html`) NO va en las reuniones
semanales: solo en las de cierre de mes (decisión del usuario, 18/10/2026).

### Formato de números y etiquetas (decisión del usuario, 16/11/2026)

- **Decimales con coma, miles con punto** (formato chileno): `6,6%`, `26,1% de bloqueo`,
  `-0,6 pts`, `3.208`. Las plantillas muestran el `contexto` tal cual (strings), así que
  el formato se escribe al armar la reunión, no lo pone la plantilla.
  **Ojo:** el comando `actualizar_reunion` todavía escribe los % y los "pts" con punto
  (`_pct` y los f-strings de `kpis`/`kpi_destacado`); revisar/corregir a mano después de
  correrlo hasta que se ajuste el comando.
- Rangos de fechas en etiquetas como días, no "semanas": `ACUMULADO NOVIEMBRE (DEL 2 AL
  21 NOV)`, no `(SEMANAS 2 AL 21)`.

### Cálculo de "Consultas diarias necesarias" (diapositiva de Meta)

`(meta del mes − suma de ventas semanales cargadas) ÷ días hábiles lunes a viernes que
quedan en el mes, contando desde el lunes de la semana de la reunión`, redondeado.
Ej. reunión 16/11/2026: (9.562 − 4.527) ÷ 11 = 458. `venta_total` debe ser siempre la
suma de `ventas_semanales`. Confirmar con el usuario la venta de la semana antes de
cargarla (en la reunión del 16/11 se cargó un valor errado y hubo que corregirlo).

### Usabilidad Autopago: el dato llega con desfase

El % de la semana recién terminada suele no estar disponible el día de la reunión: es
normal que la serie llegue atrasada (en la reunión del 16/11 llegaba hasta 2–7 nov y
faltaba 9–14 nov). No inventar ni arrastrar el dato: agregar la semana faltante cuando el
usuario lo entregue (ver también la nota de pendientes: la de noviembre puede llegar a
fin de mes).

### Cierre de mes

Mismo esquema, más el Comparativo Venta año contra año (venta del mes vs. mismo mes del
año anterior), pero: Oferta por Especialidad es del **mes completo** (proyección al
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

4. **Vigencia de Oferta por día, no por semana** (corregido 11/2026): la vigencia
   `Validodesde`/`Validohasta` se evalúa para la fecha concreta de cada día de la
   semana (`inicio_semana + día`), no solo para el lunes. Si no, un médico que atiende
   un solo día queda fuera de la semana.
5. **Semana de la importación**: la semana se asigna según el día en que se importa
   (domingo → lunes siguiente). Un archivo no se puede separar por semana: el del 28/09
   incluye 1–3 oct.
6. **Cuidado con alias**: en `importador.py` la función de `calculos` se importa como
   `lunes_de_semana` porque una variable local `inicio_semana` la tapó y provocó un
   error 500 al importar. No volver a nombrar así una variable local.

### Historial y menú "Oferta médicos"

- Cada importación de oferta/bloqueos regraba `OfertaDiaria` (ver `DOCUMENTACION.md`).
  El menú `/disponibilidad/oferta-medicos/` lee de ahí. El historial de un mes refleja
  el plantel de médicos **vigente al momento de la última importación** de cada semana.
- Los importadores aceptan `solo_calcular=True`: devuelven las filas sin escribir las
  tablas vigentes. Úsalo en scripts para recalcular semanas de otro periodo (proyección
  del mes, comparativos) sin pisar la oferta actual. Para el historial de una semana
  se llama a `calculos.guardar_historial_semana(lunes, ofertas=..., bloqueos=...)`.
- Cuando se agrega o quita un médico del plantel, hay que **reimportar** oferta y
  bloqueos y luego recalcular las reuniones afectadas (la del cierre de mes con la
  proyección y la semanal en curso). Para eso hay dos comandos en el repo:
  1. `recalcular_oferta_mes` (`disponibilidad`): calcula el mes semana por semana y por
     especialidad desde los Excel (rutas locales; los `.xlsx` no se versionan) y deja un
     JSON. Con `--guardar-historial` regraba `OfertaDiaria`. Con `--solo-lunes` recalcula
     una semana con otros archivos (ej. comparar con una semana ya cerrada usando los
     archivos de esa fecha) y `--salida` mezcla con el JSON existente.
  2. `actualizar_reunion` (`presentacion`): escribe esos números en las diapositivas
     (semanal: 2, 3 y 4; cierre: 6 y 7). Ver el encabezado de cada archivo.

  Ejemplo completo (noviembre 2026):
  ```
  DATABASE_URL="<DATABASE_PUBLIC_URL>" DJANGO_SETTINGS_MODULE=config.settings python manage.py recalcular_oferta_mes --mes 2026-11 --oferta ExportarOferta-20261110.xlsx --bloqueos ExportarBloqueos-20261109.xlsx --salida semanas_nov.json --guardar-historial
  DATABASE_URL="<DATABASE_PUBLIC_URL>" DJANGO_SETTINGS_MODULE=config.settings python manage.py actualizar_reunion --semanas semanas_nov.json --semanal 2026-11-09 --semana-anterior 2026-11-02 --cierre 2026-11-02 --mes-anterior-oferta 14200 --mes-anterior-bloqueos 1389
  ```
  Ojo: `semanas_nov.json` y los Excel quedan en tu carpeta local (no se suben a git).
  Los 14.200/1.389 son la oferta/bloqueos de octubre usados como mes anterior.
- Criterio de cálculo: solo servicios "Consulta*" cuentan como oferta (los
  "Procedimiento"/Dolor no); sábado incluido; % bloqueos = bloqueos / oferta bruta;
  meta de bloqueos 15%.

### Plantel de médicos incluidos en el cálculo (decisiones del usuario, 11/2026)

- Se incluyen solo los médicos registrados en el mantenedor y `activo=True`. Agregados
  recientemente: Sampayo, cirujanos vasculares, Barra y Bizama, Lucas López, nutriólogos
  y psicólogos, Carlos Domínguez, Marco Antonio Oñate, Kenny Ramos Perozo.
- Excluidos a pedido: Camila López Netle, Camila Águila, Felipe Ahumada, Ayelen Palacios,
  Victoria Benavente, Bettina Schmith, Patricia Riquelme, Sofía Catalán, Héctor Figueroa
  (ecografista), Enid. Sebastián Soto es Gastroenterología (no Medicina Interna).
- **RUT provisorios**: varios médicos nuevos se crearon con RUT `SIN-RUT-xxxx` porque el
  campo es obligatorio y único. Pendiente que el usuario entregue los RUT reales
  (Sampayo, Arancibia, Salgado, Cassina, Barra Friz, López Ponce de León, Domínguez
  Varas, Bobadilla, Sandoval Arellano, Oñate, Ramos Perozo) y confirme el segundo
  apellido de Oñate.

### Integración con Sked24 (explorada 15/11/2026, sin resultado)

El sistema externo de citas es Sked24. Su API nueva (`https://proxy1.sked24api.io/v1`
y `/v2`) usa el encabezado `Ocp-Apim-Subscription-Key` (clave de suscripción) y
`Authorization: Bearer <ApiKey>`. Prueba hecha: la clave de suscripción es válida
(sin ella da 401), pero `/v1/Resources` y otros endpoints devuelven 500 con cualquier
Bearer y `/v2/*` da 404; no se conocen las rutas reales (Swagger solo en QA). Pendiente:
pedir a soporte de Sked24 la lista de endpoints y revisar el error 500. **Las claves
NO están en el repo ni en este archivo**; si se retoma, guardarlas como variables de
entorno (Railway / local) y regenerarlas, porque se compartieron en un chat.

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

- **Usabilidad Autopago de noviembre**: el usuario la entrega al final del mes. Falta
  también el dato de 1–3 oct.
- **Reuniones creadas hasta ahora**: 12/10, 19/10, 26/10, cierre de octubre (02/11, con
  proyección de noviembre) y 09/11. La siguiente es la semana del 16 al 21 de noviembre.
- Plantilla `meta_agosto.html`: el título del gráfico es `titulo_grafico` y por defecto
  "Meta" (no fijar el mes en el título).

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
