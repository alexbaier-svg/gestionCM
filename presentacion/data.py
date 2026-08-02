"""Contenido de la presentación de la reunión semanal.

Cargado a mano por ahora (ver 'reunion semanal.pptx'). Pensado para reemplazarse más
adelante por datos calculados desde el sistema (agenda, oferta, bloqueos), sin cambiar
las plantillas de cada diapositiva.
"""

NAVY = "#1E2761"
TEAL = "#1C7293"
LILA = "#CADCFC"
GRIS = "#6B7280"
VERDE = "#1E7A34"
ROJO = "#C0392B"


def obtener_diapositivas():
    return [
        {
            "titulo": "Ocupación Infraestructura",
            "plantilla": "presentacion/diapositivas/ocupacion_infraestructura.html",
            "contexto": {
                "julio_pct": 67,
                "agosto_pct": 68,
                "ingresos": [
                    {"nombre": "Neurología Infantil", "consultas": 29},
                    {"nombre": "TMT caderas", "consultas": 24},
                ],
            },
        },
        {
            "titulo": "Oferta por Especialidad — Agosto 2026",
            "plantilla": "presentacion/diapositivas/oferta_especialidad.html",
            "contexto": {
                "periodo": "01/08/2026 – 31/08/2026",
                "filas": [
                    {"especialidad": "BRONCOPULMONAR", "bruta": "88", "efectiva": "88", "bloqueos": "0", "pct": "0%"},
                    {"especialidad": "CARDIOLOGIA", "bruta": "443", "efectiva": "434", "bloqueos": "9", "pct": "2%"},
                    {"especialidad": "CIRUGIA", "bruta": "1.391", "efectiva": "1.215", "bloqueos": "176", "pct": "12.7%"},
                    {"especialidad": "COLOPROCTOLOGO", "bruta": "232", "efectiva": "216", "bloqueos": "16", "pct": "6.9%"},
                    {"especialidad": "DERMATOLOGIA", "bruta": "72", "efectiva": "72", "bloqueos": "0", "pct": "0%"},
                    {"especialidad": "FISIATRIA", "bruta": "36", "efectiva": "27", "bloqueos": "9", "pct": "25%"},
                    {"especialidad": "GASTROENTEROLOGIA", "bruta": "338", "efectiva": "252", "bloqueos": "86", "pct": "25.4%"},
                    {"especialidad": "GINECOLOGIA", "bruta": "1.125", "efectiva": "1.046", "bloqueos": "79", "pct": "7%"},
                    {"especialidad": "INFECTOLOGIA", "bruta": "40", "efectiva": "40", "bloqueos": "0", "pct": "0%"},
                    {"especialidad": "KINESIOLOGIA", "bruta": "356", "efectiva": "356", "bloqueos": "0", "pct": "0%"},
                    {"especialidad": "MATRONA", "bruta": "152", "efectiva": "152", "bloqueos": "0", "pct": "0%"},
                    {"especialidad": "MEDICINA FAMILIAR", "bruta": "134", "efectiva": "134", "bloqueos": "0", "pct": "0%"},
                    {"especialidad": "MEDICINA GENERAL", "bruta": "2.618", "efectiva": "2.480", "bloqueos": "138", "pct": "5.3%"},
                    {"especialidad": "MEDICINA INTERNA", "bruta": "132", "efectiva": "132", "bloqueos": "0", "pct": "0%"},
                    {"especialidad": "NEFROLOGIA", "bruta": "159", "efectiva": "159", "bloqueos": "0", "pct": "0%"},
                    {"especialidad": "NEUROCIRUGIA", "bruta": "95", "efectiva": "95", "bloqueos": "0", "pct": "0%"},
                    {"especialidad": "NEUROLOGIA", "bruta": "398", "efectiva": "373", "bloqueos": "25", "pct": "6.3%"},
                    {"especialidad": "NEURORRADIOLOGIA INTERVENCIONAL", "bruta": "20", "efectiva": "20", "bloqueos": "0", "pct": "0%"},
                    {"especialidad": "NUTRICIONISTA", "bruta": "581", "efectiva": "545", "bloqueos": "36", "pct": "6.2%"},
                    {"especialidad": "OFTALMOLOGIA", "bruta": "132", "efectiva": "92", "bloqueos": "40", "pct": "30.3%"},
                    {"especialidad": "OTORRINOLARINGOLOGIA", "bruta": "1.319", "efectiva": "1.207", "bloqueos": "112", "pct": "8.5%"},
                    {"especialidad": "PEDIATRIA", "bruta": "573", "efectiva": "432", "bloqueos": "141", "pct": "24.6%"},
                    {"especialidad": "PSICOLOGIA", "bruta": "444", "efectiva": "396", "bloqueos": "48", "pct": "10.8%"},
                    {"especialidad": "TRAUMATOLOGIA", "bruta": "2.163", "efectiva": "1.934", "bloqueos": "229", "pct": "10.6%"},
                    {"especialidad": "UROLOGIA", "bruta": "711", "efectiva": "535", "bloqueos": "176", "pct": "24.8%"},
                ],
                "total": {"especialidad": "Total", "bruta": "13.752", "efectiva": "12.432", "bloqueos": "1.320", "pct": "9.6%"},
                "kpis": [
                    {"etiqueta": "OFERTA BRUTA TOTAL", "valor": "13.752", "color": NAVY},
                    {"etiqueta": "BLOQUEOS", "valor": "1.320", "color": ROJO},
                    {"etiqueta": "% BLOQUEOS (Target 15%)", "valor": "9.6%", "color": VERDE},
                    {"etiqueta": "ESPECIALIDAD MÁS AFECTADA", "valor": "OFTALMOLOGIA", "detalle": "30.3% de bloqueo", "color": NAVY, "detalle_color": ROJO},
                ],
            },
        },
        {
            "titulo": "Comparativo Julio vs. Agosto 2026",
            "plantilla": "presentacion/diapositivas/comparativo_mensual.html",
            "contexto": {
                "categorias": ["Oferta Bruta", "Oferta Efectiva", "Bloqueos"],
                "series": [
                    {"nombre": "Julio", "color": NAVY, "valores": [11454, 10737, 717]},
                    {"nombre": "Agosto", "color": TEAL, "valores": [13752, 12432, 1320]},
                ],
                "kpis": [
                    {"etiqueta": "% BLOQUEOS JULIO", "valor": "6.3%", "color": VERDE},
                    {"etiqueta": "% BLOQUEOS AGOSTO", "valor": "9.6%", "color": VERDE},
                ],
                "kpi_destacado": {"etiqueta": "VARIACIÓN DE BLOQUEOS", "valor": "+3.3 pts", "detalle": "Agosto vs. Julio"},
            },
        },
        {
            "titulo": "Meta vs. Venta — Julio 2025 vs. Julio 2026",
            "plantilla": "presentacion/diapositivas/meta_venta.html",
            "contexto": {
                "subtitulo": "Cumplimiento de meta comercial y variación interanual",
                "categorias": ["jul-25", "jul-26"],
                "series": [
                    {"nombre": "Meta", "color": GRIS, "valores": [8429, 9522]},
                    {"nombre": "Venta", "color": NAVY, "valores": [9655, 9253]},
                ],
                "kpis": [
                    {"etiqueta": "% SOBRE META — JUL-25", "valor": "+14.5%", "color": VERDE},
                    {"etiqueta": "% SOBRE META — JUL-26", "valor": "-2.8%", "color": ROJO},
                ],
                "kpi_destacado": {"etiqueta": "% VARIACIÓN VS. JUL-25", "valor": "-4.2%", "detalle": "Venta jul-26 vs. venta jul-25"},
            },
        },
        {
            "titulo": "Experiencia Paciente",
            "plantilla": "presentacion/diapositivas/experiencia_paciente.html",
            "contexto": {
                "grupos": [
                    {
                        "nombre": "Centro Médico Base",
                        "detalle": "Total: 124  ·  ACHS: 19  ·  No Ley: 105",
                        "series": [
                            {"etiqueta": "Total", "pct": 86, "color": NAVY},
                            {"etiqueta": "ACHS", "pct": 89, "color": TEAL},
                            {"etiqueta": "No Ley", "pct": 86, "color": LILA, "color_texto": NAVY},
                        ],
                    },
                ],
            },
        },
        {
            "titulo": "Usabilidad Autopago",
            "plantilla": "presentacion/diapositivas/usabilidad_autopago.html",
            "contexto": {
                "junio_pct": "61,95%",
                "julio_pct": "62,73%",
                "promedio_previo": "Promedio de Enero a Mayo: 56%",
                "nota": "La variación positiva responde a la gestión comercial en homologar "
                        "codificación (Banmédica).",
            },
        },
    ]
