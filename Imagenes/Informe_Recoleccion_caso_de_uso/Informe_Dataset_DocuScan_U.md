## Informe Técnico: Recolección del Dataset Inicial

DocuScan U – Recuperación inteligente de documentos fotografiados

## 1. Datos Generales

| Nombre completo: | Jhonny Omar Pascal Chamba Iván Renan Quishpe Olmedo Edison Rivaldo López Portillo |
| --- | --- |
| Carrera: | Ciencias de la Computación |
| Asignatura: | Procesamiento de imágenes |
| Docente: | Ing. Vantroy Jimenes |
| Semestre / Nivel: | 6º semestre – PAO 2026 |
| Fecha de entrega: | 05 / 11 / 2026 |

## 2. Objetivo Técnico

El presente informe documenta la construcción de un dataset inicial de

fotografías de documentos impresos en español (formularios, actas y oficios), concebido como banco de pruebas experimental para el sistema DocuScan U. El corpus tiene como finalidad evaluar de manera controlada y reproducible el desempeño de los algoritmos de preprocesamiento de imagen que integran el flujo de trabajo: corrección de perspectiva mediante detección de bordes y transformación homográfica, mejora del contraste local con CLAHE (Contrast Limited Adaptive Histogram Equalization), filtrado de ruido (gaussiano, de mediana y bilateral), umbralización adaptativa y corrección de inclinación.

Asimismo, el dataset permitirá cuantificar el impacto de cada etapa sobre la

exactitud del reconocimiento óptico de caracteres realizado con Tesseract OCR, mediante las métricas CER (Character Error Rate) y WER (Word Error Rate), calculadas contra un texto de referencia (ground truth) transcrito manualmente. De este modo se podrá responder la pregunta central del proyecto y determinar qué etapa aporta la mayor mejora, comparando las configuraciones: sin procesar, solo CLAHE, solo umbralización y flujo completo. Complementariamente, se calcularán métricas de calidad visual (contraste, nitidez, histograma y relación señal/ruido) sobre la imagen original y la procesada.

Métricas de error: CER = (S + D + I) / N, donde S, D e I son las sustituciones, eliminaciones e inserciones a nivel de carácter y N el número de caracteres del texto de referencia. El WER se define de forma análoga a nivel de palabra.

Calle Antisana y Av. Universitaria

Telf: (06) 2995800

infoeupec.edu.ec

www.upec.edu.ec

Tulcán - Ecuador


## 3. Especificaciones del Dataset

Las siguientes especificaciones se derivan del alcance y los supuestos

definidos en la propuesta del proyecto, y garantizan homogeneidad mínima entre las muestras sin comprometer la variabilidad necesaria para la evaluación.

| Característica | Especificación |
| --- | --- |
| Resolución mínima | 1000 × 1400 px por imagen (resolución mínima recomendada del proyecto) |
| Formatos de archivo | JPG y PNG (entrada soportada por el sistema) |
| Dispositivo de captura | Cámaras de teléfonos móviles de distintas gamas, para incluir variabilidad en calidad de sensor |
| Tipo de documento | Formularios, actas y oficios impresos con texto en español |
| Encuadre | Documento completo visible en la fotografía y diferenciable del fondo (supuesto del sistema) |
| Ground truth | Transcripción textual manual (.txt, codificación UTF-8) por cada documento fuente, requerida para el cálculo de CER y WER |
| Convención de nombres | C{clase}_{doc}_{nn}.jpg|png (p. ej., C1_acta01_03.jpg) con archivo de metadatos CSV (clase, dispositivo, condición de captura) |
| Fuera del alcance | Manuscritos complejos, sellos superpuestos, documentos no rectangulares, documentos rotos o muy doblados |

## 4. Taxonomía y Categorización

Con el fin de aislar el efecto de cada técnica de preprocesamiento, las

imágenes se organizan en cuatro clases según el tipo de defecto dominante. Cada documento fuente se fotografía en todas las clases, lo que permite comparaciones pareadas.

| Clase | Categoría | Descripción y condiciones de captura | Técnica evaluada |
| --- | --- | --- | --- |
| Clase 0 | Control / Baseline | Fotografía frontal, paralela a la hoja, con iluminación uniforme y papel en buen estado. Establece el CER/WER de referencia. | Línea base (sin procesar) y Av. Universitaria Calle Antisana Telf: (06) 2995800 infoeupec.edu.ec |

www.upec.edu.ec

Tulcán - Ecuador


| Clase | Categoría | Descripción y condiciones de captura | Técnica evaluada |   |
| --- | --- | --- | --- | --- |
| Clase 1 | Anomalías de iluminación / sombras | Iluminación desigual, sombras proyectadas por la mano o el dispositivo, reflejos y bajo contraste por tinta tenue o papel amarillento. | CLAHE y umbralización adaptativa |   |
| Clase 2 | Distorsión geométrica / inclinación | Cámara no paralela a la hoja (distorsión de perspectiva) y texto rotado respecto a la horizontal. | Corrección de perspectiva y de inclinación |   |
| Clase 3 | Ruido / degradación del papel | Granulado por sensor de baja calidad, arrugas, manchas y desgaste del papel. | Filtros gaussiano, de mediana y bilateral |   |

## 5. Retos Técnicos y Explicación

La recolección del dataset presenta una dificultad metodológica central:

inducir defectos de forma natural y controlada sin perder realismo. Un defecto simulado digitalmente (por ejemplo, un gradiente sintético de iluminación) no reproduce la complejidad del proceso físico de formación de la imagen, por lo que los resultados podrían sobrestimar el desempeño de los algoritmos. Por ello, se prioriza la captura real, lo que conlleva los siguientes retos:

- Iluminación no uniforme reproducible. Las sombras reales dependen de la posición de la fuente de luz, la mano del fotógrafo y la geometría del entorno. Replicar la misma condición en capturas sucesivas es difícil, lo que introduce varianza no deseada entre muestras.

- Prueba de la umbralización adaptativa. A diferencia de la umbralización global (p. ej., Otsu), que asume un histograma bimodal, la umbralización adaptativa calcula el umbral por vecindad local (media o gaussiana). Para evidenciar su ventaja, las muestras deben contener gradientes de iluminación suaves y sombras con bordes difusos o duros, de modo que un umbral global falle y el adaptativo se desempeñe mejor. Si las sombras son demasiado débiles, ambos métodos coinciden y la comparación pierde validez; si son extremas, se pierde información textual y ningún método la recupera.

- Sensibilidad a los parámetros. El tamaño de bloque y la constante de sustracción del umbral adaptativo dependen de la resolución y del tamaño del texto. El dataset debe incluir variabilidad suficiente de escala para detectar sobreajuste de parámetros. Calle Antisana y Av. Universitaria Telf: infoeupec.edu.ec

www.upec.edu.ec


•

Distorsión geométrica controlada.

Los ángulos de captura y de inclinación

EDUCAMOS PARA TRANSFORMAR EL MUNDO

deben cubrir un rango representativo (por ejemplo, rotaciones moderadas y perspectivas oblicuas) sin que el documento salga del encuadre ni se pierdan sus bordes, condición necesaria para la detección de contornos y la homografía.

- Interacción entre defectos. En condiciones reales los defectos coexisten (sombra más inclinación). Se acordó que cada clase tenga un defecto dominante y se reserve un subconjunto de imágenes combinadas para validar el flujo completo.

- Ground truth y validez del OCR. El cálculo de CER y WER exige transcripciones exactas; cualquier error en la referencia contamina la métrica. Además, la diferencia de resolución entre dispositivos afecta directamente a Tesseract, por lo que debe registrarse como variable de control.

- Tamaño reducido del corpus. Al tratarse de un dataset inicial, la potencia estadística es limitada; los resultados se interpretarán como evidencia exploratoria y no como conclusiones generalizables.

## 6. Análisis de Casos de Uso

## 6.1 Actores

- Usuario Administrativo (actor principal). Persona de una universidad, oficina o archivo que digitaliza formularios, actas y oficios con la cámara del celular. Inicia el flujo, configura el preprocesamiento, revisa los resultados y exporta el documento.

- Tesseract OCR (actor externo). Motor de reconocimiento óptico de caracteres, integrado mediante pytesseract. Es un sistema secundario que recibe la imagen procesada y devuelve el texto extraído, sobre el cual se calculan CER y WER.

## 6.2 Casos de uso principales

| Caso de uso | Descripción |
| --- | --- |
| Cargar fotografía | El Usuario Administrativo selecciona una imagen JPG o PNG. El sistema valida el formato y la resolución mínima (1000 × 1400 px) y la muestra como imagen original. |
| Preprocesar imagen | Caso de uso compuesto que ejecuta el flujo de mejora de la imagen. Incluye (<<include>>) tres subcasos: Corregir perspectiva, Filtros/CLAHE y Umbralización. |
| Corregir perspectiva | Detecta los bordes y el contorno del documento y aplica una transformación de perspectiva para obtener una vista frontal de la hoja; además mide y corrige el ángulo de inclinación del texto. y Av. Universitaria Calle Antisana |

Telf: (06) 2995800

www.upec.edu.ec


|   | Caso de uso | Descripción |   |
| --- | --- | --- | --- |
|   | Filtros / CLAHE | Convierte la imagen a escala de grises, aplica CLAHE para mejorar el contraste local y filtra el ruido con el filtro (gaussiano, de mediana o bilateral) que mejor conserve los bordes del texto. |   |
|   | Umbralización | Aplica umbralización adaptativa para separar el texto del fondo y eliminar sombras, generando la imagen binaria final. |   |
|   | Evaluar legibilidad | Calcula contraste, nitidez, histograma y relación señal/ruido de la imagen original y de la procesada, y las presenta lado a lado junto con sus histogramas. |   |
|   | Extraer texto | Envía la imagen a Tesseract OCR (actor externo), recibe el texto extraído y calcula CER y WER frente al texto de referencia para cada configuración (sin procesar, solo CLAHE, solo umbralización y flujo completo). |   |
|   | Exportar documento | Genera la imagen procesada en formato PNG o PDF y un reporte de métricas. |   |

## 6.3 Relaciones del modelo

El caso de uso Preprocesar imagen se descompone mediante relaciones

<<include>> en Corregir perspectiva, Filtros/CLAHE y Umbralización, ya que las tres etapas forman parte obligatoria del flujo completo. Los casos Evaluar legibilidad y Extraer texto dependen de que exista una imagen preprocesada, por lo que incluyen a Preprocesar imagen. Tesseract OCR participa únicamente en Extraer texto, como actor externo secundario.

## 6.4 Diagrama de casos de uso (código Mermaid)

Mermaid no dispone de una sintaxis nativa de diagramas UML de casos de

uso; por ello, el modelo se representa con un diagrama de flujo (flowchart) que emula la notación: actores como nodos redondeados, casos de uso como óvalos dentro del límite del sistema y relaciones <<include>> como flechas punteadas. El código puede visualizarse en mermaid.live o en cualquier editor compatible con Mermaid.

## flowchart LR

%% Actores

UA([Usuario Administrativo])

OCR([Tesseract OCR])

%% Sistema DocuScan U

subgraph SYS[Sistema DocuScan U]

direction TB

UC1(Cargar fotografía)

UC2(Preprocesar imagen)

UC2a(Corregir perspectiva)

UC2b(Aplicar filtros y CLAHE)

UC2c(Aplicar umbralización adaptativa)

UC3(Evaluar legibilidad)

UC4(Extraer texto)


UC5(Exportar documento)

end

## %% Asociaciones de actores

- UA --- UC1

- UA --- UC2

- UA --- UC3

- UA --- UC4

- UA --- UC5

OCR --- UC4

## %% Relaciones include

- UC2 -.->|include| UC2a

- UC2 -.->|include| UC2b

- UC2 -.->|include| UC2c

- UC3 -.->|include| UC2

- UC4 -.->|include| UC2

Calle Antisana y Av. Universitaria

Telf: (06) 2995800 infoeupec.edu.ec www.upec.edu.ec Tulcán - Ecuador
