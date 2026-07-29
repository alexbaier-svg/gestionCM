# GestionCM — Sistema de Gestión de Centro Médico

## Objetivo del proyecto
Sistema web para gestionar la operación diaria de un centro médico:
- Mantenedor de médicos (datos generales).
- Mantenedor de boxes (salas/consultas).
- Asignación de médicos a boxes (regla fija por médico + ajuste manual diario).
- Importación de agendas diarias exportadas desde el sistema externo de citas (CSV).
- Exportación del listado/agenda diaria: médico, horas, box.

## Stack elegido
- **Backend/Frontend**: Python 3.13 + Django, con **pantallas propias simples** (templates +
  vistas a medida) como interfaz principal — no el Django Admin crudo. Se decidió así porque el
  usuario final no es técnico; el admin de Django expone demasiados tecnicismos (filtros,
  listas crudas, formularios genéricos). El admin (`/admin/`) se mantiene solo como herramienta
  de respaldo para el superusuario (crear cuentas, asignar grupos, depurar datos).
- **Import/Export**: `django-import-export` + `openpyxl` para importar/exportar Excel/CSV de la
  agenda diaria.
- **Base de datos**: SQLite en desarrollo local / offline. PostgreSQL en producción (Railway).
- **Despliegue**: Railway, ya configurado y en producción en `https://gestioncm.asisteme.cl`
  (dominio propio verificado, deploy automático desde GitHub en cada push a `master`).
  `railway.json` define `build.buildCommand` (collectstatic, debe ir en build porque
  preDeployCommand corre en un contenedor efímero distinto al que sirve tráfico) y
  `deploy.preDeployCommand` (migrate).
- **Autenticación**: Sistema de usuarios de Django con grupos/roles.

## Diseño de la interfaz (decisión con el usuario)
- **Página principal** (`/`, pública, sin login): solo bienvenida + botón de iniciar sesión. No
  expone médicos, boxes ni horarios sin autenticarse (son datos de negocio sensibles, aunque no
  sean PHI de pacientes).
- Tras iniciar sesión: un panel simple con accesos a Médicos, Boxes, Distribución y Agenda
  diaria, según el rol del usuario.
- **Gestión de Médicos y Boxes**: pantallas propias (listar/crear/editar/eliminar) con solo los
  campos relevantes y lenguaje claro — nada de terminología técnica de Django.
- **Boxes por piso**: los boxes se organizan en **Piso 1** (Box 1 a 7, trauma) y **Piso 2**
  (Box 8 a 31, incluye áreas Pediatría/Oftalmología/Ginecología/Urología/Otorrino y "Box
  Ecogine"), reflejando la distribución real del centro (visto en `BOX.xlsx`).
- **Visualización de distribución**: vista de solo lectura agrupada por piso, mostrando cada box
  y su(s) médico(s) asignado(s). Sin drag & drop — se evaluó y se descartó por complejidad
  innecesaria para el objetivo de "simple y limpio".
- **Agenda diaria**: vista web simple (lista médico + horas + box para una fecha, pensada para
  imprimir) y también descarga en Excel — ambos formatos, no uno solo.

## Roles de usuario
- **Administrador**: gestiona médicos, boxes, asignaciones e importación de agendas. Acceso total.
- **Recepción/Secretaría**: solo visualiza y exporta la agenda diaria, sin editar médicos/boxes.
- **Médico**: consulta únicamente su propia agenda (filtrado por usuario vinculado a su registro de médico).

## Importación de agendas (archivo externo)
Origen: export de citas de un sistema clínico externo (ej. `ExportarCitas-YYYYMMDD.csv`).

**Detalles técnicos del archivo observados:**
- Codificación **UTF-16**, separado por comas, con 65 columnas.
- Columnas relevantes: `Profesional/Recurso`, `No. Documento Profesional`, `Especialidad`,
  `Servicio`, `Área`, `Fecha desde`, `Hora desde`, `Fecha hasta`, `Hora hasta`, `Estado`.
- **No trae columna de Box** — la asignación a box es responsabilidad de este sistema, no del
  archivo importado.
- El campo `Profesional/Recurso` mezcla médicos (ej. "Roberto Maestre Bravo") y
  recursos/equipos (ej. "Scanner Los Andes", "Resonador Los Andes"). Al importar, solo se
  procesan filas donde el recurso corresponde a un médico registrado en el mantenedor
  (matching por RUT en `No. Documento Profesional` cuando esté disponible, o por nombre).

**Privacidad (decisión tomada con el usuario):** el archivo trae datos de pacientes (RUT,
nombre, teléfono, email, dirección, fecha de nacimiento). **Se descartan explícitamente al
importar** — el sistema NO almacena PHI de pacientes, solo médico + especialidad + fecha/hora +
estado de la cita. Esto es intencional por privacidad/cumplimiento; no agregar campos de
paciente sin que el usuario lo pida explícitamente.

## Lógica de asignación de box
Modelo **mixto**, acordado con el usuario:
1. Cada médico tiene uno o más boxes "por defecto" configurados en su ficha (regla fija).
2. Al importar una agenda diaria, el sistema propone automáticamente el box según esa regla.
3. El administrador puede reasignar manualmente el box de un bloque específico si hay conflicto
   de horario o disponibilidad (ej. dos médicos con el mismo box por defecto a la misma hora).

## Modelo de datos
- `Medico`: nombre, RUT, especialidad(es), datos de contacto, usuario vinculado (para rol
  Médico).
- `Box`: nombre/número, **piso** (1 o 2), ubicación, área (ej. Imágenes, Consulta,
  Procedimientos).
- `AsignacionBox`: relación Médico ↔ Box "por defecto" (regla fija), con día de semana opcional
  (nulo = todos los días).
- `BloqueAgenda`: médico, box (nullable hasta asignar/confirmar), fecha, hora_inicio, hora_fin,
  especialidad, estado, origen (importado/manual), id_externo (para deduplicar reimportaciones).
- `ImportacionAgenda`: registro de cada archivo importado (fecha, usuario, cantidad de filas
  procesadas/omitidas) para trazabilidad.

## Datos reales ya cargados en producción
- 80 médicos reales (cargados desde `AGENDA.xlsx`, hoja "Médicos CM", vía el comando
  `cargar_medicos_excel`), con sus boxes por defecto ya asignados (incluye reglas por día de
  semana). Pendiente de revisión manual: Contreras Neira Paola (RUT 173466722) tenía un valor de
  box ambiguo en la planilla original y quedó sin asignar.
- Los archivos fuente (`AGENDA.xlsx`, `BOX.xlsx`, los CSV de citas) **no se versionan** — están
  en `.gitignore` porque traen datos de contacto del personal médico y/o de pacientes.

## Estado del proyecto
En producción, con datos reales cargados. Interfaz en transición: del admin de Django crudo
hacia pantallas propias simples (ver "Diseño de la interfaz" arriba).

## Convenciones
- Idioma de la interfaz y del código de dominio (modelos, variables de negocio): español.
- Nombres de tablas/campos en snake_case en español (ej. `nombre_medico`, `hora_inicio`).
