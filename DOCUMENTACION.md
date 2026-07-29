# GestionCM — Documentación del sistema

Documento de referencia para futuras consultas o retomar el desarrollo. Describe el
estado del sistema al **29 de julio de 2026**. Para las decisiones de diseño y contexto
de por qué se hizo cada cosa, ver también `CLAUDE.md` (pensado para que Claude Code
retome el contexto del proyecto).

## 1. Qué es

Sistema de gestión para un centro médico (Clínica Los Andes): mantenedor de médicos y
boxes, asignación de médicos a boxes, agenda diaria, y visualización de ocupación de
boxes — reemplazando el manejo manual en planillas Excel.

- **Producción**: https://gestioncm.asisteme.cl
- **Repositorio**: https://github.com/alexbaier-svg/gestionCM (rama `master`)
- **Hosting**: Railway (proyecto `responsible-renewal`, servicio `web` + `Postgres`)

## 2. Stack técnico

- **Backend/Frontend**: Python 3.13 + Django 6.0, con **pantallas propias** (no Django
  Admin) como interfaz principal. El admin de Django (`/admin/`) sigue disponible como
  respaldo técnico (crear superusuarios, depurar datos), pero no es la interfaz que usan
  los usuarios finales.
- **Base de datos**: SQLite en desarrollo local. PostgreSQL en producción (Railway),
  seleccionado automáticamente según exista o no la variable de entorno `DATABASE_URL`
  (ver `config/settings.py`).
- **Librerías clave**: `django-import-export`, `openpyxl` (leer/escribir Excel),
  `dj-database-url`, `python-decouple`, `whitenoise` (estáticos), `gunicorn`.
- **Diseño visual**: CSS propio en `static/css/estilo.css` (sin framework de JS), paleta
  azul marino/azul medio/celeste/verde inspirada en la web de la clínica.

## 3. Estructura de apps Django

| App | Responsabilidad |
|---|---|
| `core` | Página principal pública, login/logout, panel de inicio (dashboard), submenú de Importaciones, administración de usuarios/roles. |
| `medicos` | Mantenedor de médicos y especialidades. |
| `boxes` | Mantenedor de boxes (por piso), asignación fija médico↔box, vista de distribución. |
| `agenda` | Bloques de agenda diaria (citas), importador de citas desde CSV, exportación web/Excel. |
| `disponibilidad` | Oferta horaria y bloqueos (ausencias) de médicos, mapa de calor de ocupación de boxes, alertas. |

## 4. Modelo de datos

- **`Medico`** (`medicos`): `nombre_completo`, `rut` (único, matchea con el sistema
  externo), `especialidades` (M2M a `Especialidad`), `telefono`, `email`, `activo`,
  `usuario` (OneToOne opcional a `auth.User`, para el rol Médico).
- **`Especialidad`** (`medicos`): solo `nombre`.
- **`Box`** (`boxes`): `nombre`, **`piso`** (1 o 2), `area` (Consulta/Imágenes/
  Procedimientos/Otro), `ubicacion`, `activo`.
  - **Piso 1** = Box 1 a 7 (trauma). **Piso 2** = Box 8 a 31 + boxes especiales (BOX
    ECOGINE, TORRE, FUERA). Ver migración `boxes/migrations/0003_backfill_piso.py`.
- **`AsignacionBox`** (`boxes`): regla fija médico → box por defecto. `dia_semana`
  opcional (0=Lunes…6=Domingo; `None` = todos los días). Un médico puede tener reglas
  distintas por día (ej. box 21 de lunes a viernes excepto jueves que es box 22).
- **`BloqueAgenda`** (`agenda`): médico, box (nullable), fecha, hora_inicio, hora_fin,
  especialidad, estado (citado/confirmado/anulado/bloqueado/atendido/otro), origen
  (importado/manual), `id_externo` (AppointmentId del sistema origen, para deduplicar
  reimportaciones).
- **`ImportacionAgenda`** (`agenda`): registro de cada archivo de citas importado
  (archivo, fecha, usuario, filas procesadas/omitidas). Solo lectura.
- **`OfertaMedico`** (`disponibilidad`): médico, día de semana, hora_inicio, hora_fin.
  Representa cuándo atiende un médico. **Se reemplaza por completo en cada
  importación** (no es un historial acumulable, es el estado vigente).
- **`BloqueoMedico`** (`disponibilidad`): igual estructura + `tipo` (Parcial/Día
  completo) + `motivo`. Representa ausencias. También se reemplaza completo en cada
  importación.

## 5. Roles y permisos

Los roles son **grupos de Django** (`auth.Group`), configurados por el comando
`configurar_roles` (ver sección 7):

- **Administrador**: acceso total — médicos, especialidades, boxes, asignaciones,
  agenda, importación de agenda/oferta/bloqueos, gestión de usuarios.
- **Recepción**: solo visualiza médicos, boxes y agenda diaria; puede exportarla. No
  puede editar ni importar.
- **Médico**: solo ve su propia agenda diaria (filtrado por el campo `Medico.usuario`).
  Ve la distribución y el mapa de calor de boxes igual que los demás roles (no son
  información sensible de pacientes).

Los permisos se verifican con `PermissionRequiredMixin` (vistas basadas en clase) o
`@permission_required(..., raise_exception=True)` combinado con `@login_required`
(vistas de función) — este orden importa: sin `@login_required` primero, un usuario
anónimo recibe 403 en vez de ser redirigido a login.

## 6. Pantallas (URLs principales)

| URL | Qué hace | Quién |
|---|---|---|
| `/` | Página pública de bienvenida + login. | Público |
| `/inicio/` | Panel con accesos según rol. | Autenticado |
| `/login/`, `/logout/` | Autenticación (vistas nativas de Django). | — |
| `/importaciones/` | Submenú con las 3 importaciones. | Según permisos |
| `/medicos/` | Listar/crear/editar/eliminar médicos. | Admin (view=Recepción) |
| `/medicos/<id>/boxes/` | Asignar/quitar boxes por defecto a un médico. | Admin |
| `/medicos/especialidades/` | CRUD de especialidades. | Admin |
| `/boxes/` | Listar/crear/editar/eliminar boxes, por piso. | Admin (view=Recepción) |
| `/boxes/distribucion/?dia=N&piso=1\|2\|todos` | Qué médico usa cada box, por día de semana y piso. | Todos los roles |
| `/agenda/?fecha=YYYY-MM-DD` | Agenda diaria: resumen por médico + detalle. | Todos (Médico solo ve la suya) |
| `/agenda/excel/?fecha=...` | Descarga Excel (2 hojas: detalle y resumen). | Todos |
| `/agenda/importar/` | Subir CSV de citas del día. | Admin |
| `/disponibilidad/mapa-calor/?dia=N&piso=1\|2\|todos` | Heatmap de ocupación de boxes 8:00-20:00. | Todos |
| `/disponibilidad/alertas/` | Bloqueos sin oferta correspondiente (posible error de carga). | Todos |
| `/disponibilidad/importar-oferta/`, `/importar-bloqueos/` | Subir los Excel de oferta/bloqueos. | Admin |
| `/usuarios/` | Crear cuentas, asignar rol, vincular médico. | Admin |
| `/admin/` | Django Admin nativo (respaldo técnico). | Superusuario |

## 7. Comandos de gestión (`manage.py <comando>`)

- **`configurar_roles`**: crea/actualiza los 3 grupos con sus permisos. Idempotente.
  Re-ejecutar cada vez que se agreguen modelos/permisos nuevos que el rol Administrador
  deba poder gestionar.
- **`cargar_medicos_excel <archivo.xlsx> [--hoja "Médicos CM"] [--dry-run]`**: carga
  inicial de médicos desde la hoja "Médicos CM" de una planilla tipo `AGENDA.xlsx`.
  Interpreta la columna BOX (números, nombres como "TORRE"/"FUERA", o reglas por día
  como `"L-MA-MI-V 21, J 22"`) y crea `Medico` + `Especialidad` + `Box` +
  `AsignacionBox`. Reporta valores ambiguos (ej. `16.29`) para revisión manual.
- **`importar_agenda <archivo.csv> [--usuario u] [--encoding utf-16-le]`**: misma
  lógica que la pantalla web `/agenda/importar/` (comparten código en
  `agenda/importador.py`), útil para cargas por línea de comandos.

## 8. Importadores de archivos externos (detalle de formato)

### Citas del día — `ExportarCitas-YYYYMMDD.csv`
- CSV en **UTF-16 (con o sin BOM)**, separado por comas, 65 columnas.
- Columnas usadas: `Profesional/Recurso`, `No. Documento Profesional` (RUT),
  `Especialidad`, `Fecha desde`, `Hora desde`, `Fecha hasta`, `Hora hasta`, `Estado`,
  `AppointmentId`.
- **No trae box** — se propone automáticamente según `AsignacionBox` del médico para
  ese día de la semana.
- Matching: por RUT primero, por nombre exacto si no hay RUT.
- **Privacidad**: se descartan explícitamente todos los datos de paciente (RUT, nombre,
  teléfono, email, dirección, fecha de nacimiento). El sistema NO almacena PHI de
  pacientes.
- Deduplicación: por `AppointmentId` (campo `id_externo`), permite reimportar el mismo
  archivo sin duplicar filas.

### Oferta — `ExportarOferta-YYYYMMDD.xlsx`
- Hojas usadas: `Ofertas` (catálogo de recursos/médicos) y `HorariosOfertas` (franjas
  horarias recurrentes por día de semana, columnas Lunes...Domingo con "X").
- **No trae RUT**, solo `NombreRecurso` en formato "Nombre Apellido" (orden distinto al
  usado en el mantenedor, que es "APELLIDO NOMBRE").
- Matching por nombre **normalizado**: mayúsculas, sin tildes, comparando el conjunto de
  palabras sin importar el orden (`disponibilidad/importador.py::_normalizar_nombre`).
- Reemplaza **todo** `OfertaMedico` existente en cada importación (no acumula).
- Filas sin match (equipos, salas, u otros profesionales no cargados en `Medico`) se
  omiten silenciosamente y se cuentan en "omitidas".

### Bloqueos — `ExportarBloqueos-YYYYMMDD.xlsx`
- Hojas usadas: `Bloqueos` (catálogo + tipo + motivo) y `HorariosBloqueos` (franjas
  recurrentes, misma estructura que Oferta).
- `Tipo`: `Partial` (bloquea solo ese horario) o `WholeDay` (bloquea el día completo).
- Mismo matching por nombre normalizado, mismo reemplazo completo en cada importación.

## 9. Lógica de negocio clave

- **Resolución de box por día**: dado un médico y un día de semana, se busca primero una
  `AsignacionBox` específica para ese día; si no existe, se usa la regla "todos los
  días" (`dia_semana=None`). Esta misma lógica se repite en tres lugares — importador de
  citas, vista de distribución, y mapa de calor — buscar `_resolver_box` /
  `_medicos_del_box_ese_dia` si hay que modificarla.
- **Mapa de calor de ocupación**: para cada box y cada franja de 30 min (8:00-20:00),
  se marca "ocupado" si el médico asignado a ese box ese día tiene una `OfertaMedico`
  que cubre la franja **y no** tiene un `BloqueoMedico` que la anule (parcial cubriendo
  la franja, o día completo).
- **Alertas de bloqueos**: un `BloqueoMedico` es sospechoso si no existe ninguna
  `OfertaMedico` para ese mismo médico y día de semana (el médico no debería tener nada
  que bloquear ese día).

## 10. Despliegue (Railway)

- **Build**: `railway.json` → `build.buildCommand` corre `collectstatic` (debe ir en el
  *build*, no en el pre-deploy, porque el pre-deploy corre en un contenedor efímero
  distinto al que finalmente sirve tráfico — los archivos generados ahí no persisten).
- **Pre-deploy**: `deploy.preDeployCommand` corre `migrate --noinput`.
- **Variables de entorno del servicio `web`**: `SECRET_KEY`, `DEBUG=False`,
  `ALLOWED_HOSTS`, `DATABASE_URL` (referencia a `Postgres.DATABASE_URL`),
  `RAILWAY_PUBLIC_DOMAIN` (referencia automática).
- **Dominio propio**: `gestioncm.asisteme.cl` vía CNAME + TXT de verificación,
  configurado en el DNS del proveedor del dominio (fuera de Railway).
- **Conectar y correr comandos contra producción sin exponer la DB públicamente todo el
  tiempo**: usar Railway CLI (`railway login`, `railway link`, `railway service web`) y
  ejecutar comandos localmente contra la base con la variable `DATABASE_PUBLIC_URL` del
  servicio Postgres (la interna `postgres.railway.internal` solo resuelve dentro de la
  red de Railway). Patrón usado durante el desarrollo:
  ```
  railway run bash -c 'export DATABASE_URL="<DATABASE_PUBLIC_URL>"; \
    export PYTHONPATH="<ruta del proyecto>"; \
    "<ruta>/.venv/Scripts/python.exe" manage.py <comando>'
  ```

## 11. Datos ya cargados en producción

- **80 médicos** reales (desde `AGENDA.xlsx`, hoja "Médicos CM"), con sus boxes por
  defecto y especialidades.
- **33 boxes** (6 en piso 1, 27 en piso 2).
- **90 asignaciones** de box por defecto.
- **157 franjas de oferta** y **3 franjas de bloqueo** (de `ExportarOferta-20260729.xlsx`
  y `ExportarBloqueos-20260729.xlsx`).
- Los archivos fuente (`AGENDA.xlsx`, `BOX.xlsx`, los `.csv` de citas, los `.xlsx` de
  oferta/bloqueos) **no se versionan** en Git — están en `.gitignore` porque traen datos
  de contacto de personal médico y/o de pacientes.

## 12. Pendientes / casos conocidos

- **Contreras Neira Paola** (RUT 173466722): su box en `AGENDA.xlsx` original era un
  valor ambiguo (`16.29`), quedó sin `AsignacionBox`. Asignar manualmente en
  `/medicos/<id>/boxes/`.
- **"Box 203"** (asociado al Dr. Beneyte Giner Luciano): probablemente un error de
  tipeo en la planilla origen (no existe físicamente un box 203). Revisar y corregir en
  `/boxes/`.
- **Cobertura de Oferta/Bloqueos parcial**: de los 80 médicos, solo ~33-41 tienen
  coincidencia en los archivos de Oferta/Bloqueos ya cargados (el resto simplemente no
  aparece en esos archivos puntuales, no es un error del sistema).
- Los formularios de "Nuevo usuario" no envían email de bienvenida ni permiten que el
  propio usuario resetee su contraseña (self-service) — hoy el reseteo lo hace el
  Administrador editando el usuario.

## 13. Cómo retomar el desarrollo

- Entorno local: `./.venv/Scripts/python.exe manage.py runserver` (usa SQLite,
  `DEBUG=True` por defecto si no hay `.env`).
- Tras cualquier cambio de modelos: `makemigrations` + `migrate` local, probar, luego
  push a `master` (Railway migra solo en producción vía `preDeployCommand`).
- Tras agregar permisos nuevos que el rol Administrador deba tener: correr
  `configurar_roles` tanto local como en producción (vía `railway run`, ver sección 10).
- Convenciones: idioma español en modelos/UI, snake_case en campos, sin comentarios
  explicativos salvo que documenten un motivo no obvio (ver `CLAUDE.md`).
