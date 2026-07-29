# GestionCM — Sistema de Gestión de Centro Médico

## Objetivo del proyecto
Sistema web para gestionar la operación diaria de un centro médico:
- Mantenedor de médicos (datos generales).
- Mantenedor de boxes (salas/consultas).
- Asignación de médicos a boxes (regla fija por médico + ajuste manual diario).
- Importación de agendas diarias exportadas desde el sistema externo de citas (CSV).
- Exportación del listado/agenda diaria: médico, horas, box.

## Stack elegido
- **Backend/Frontend**: Python 3.13 + Django (con Django Admin como base del mantenedor).
- **Import/Export**: `django-import-export` + `openpyxl` para exportar Excel/CSV/PDF de la agenda diaria.
- **Base de datos**: SQLite en desarrollo local / offline. PostgreSQL en producción (Railway).
- **Despliegue**: Railway (ya existe cuenta y proyecto). Repo Git ya existe en remoto; se inicializa localmente.
- **Autenticación**: Sistema de usuarios de Django con grupos/roles.

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

## Modelo de datos (borrador inicial)
- `Medico`: nombre, RUT, especialidad(es), datos de contacto, boxes por defecto (M2M o FK a
  regla), usuario vinculado (para rol Médico).
- `Box`: nombre/número, ubicación, área (ej. Imágenes, Consulta, Procedimientos).
- `AsignacionBox`: relación Médico ↔ Box "por defecto" (regla fija).
- `BloqueAgenda`: médico, box (nullable hasta asignar/confirmar), fecha, hora_inicio, hora_fin,
  especialidad, estado, origen (importado/manual).
- `ImportacionAgenda`: registro de cada archivo importado (fecha, usuario, cantidad de filas
  procesadas/omitidas) para trazabilidad.

## Estado del proyecto
Fase inicial: definiendo arquitectura y stack. Aún no existe código Django.

## Convenciones
- Idioma de la interfaz y del código de dominio (modelos, variables de negocio): español.
- Nombres de tablas/campos en snake_case en español (ej. `nombre_medico`, `hora_inicio`).
