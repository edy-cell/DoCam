## DocuScan U

Recuperación inteligente de documentos fotografiados

## INFORMACIÓN DEL ESTUDIANTE

| Nombre completo: | Jhonny Omar Pascal Chamba Iván Renan Quishpe Olmedo Edison Rivaldo López Portillo |
| --- | --- |
| Carrera: | Ciencias de la Computación |
| Asignatura: | Procesamiento de imágenes |
| Docente: | Ing. Vantroy Jimenes |
| Semestre / Nivel: | 6º semestre – PAO 2026 |
| Fecha de entrega: | 29 / 10 / 2026 |

## 1. PLANTEAMIENTO DEL PROBLEMA

En universidades, oficinas administrativas y archivos es común digitalizar formularios, actas y oficios con la cámara del celular, porque no siempre hay un escáner a mano. Esas fotos casi siempre traen defectos:

- Sombras e iluminación desigual, causadas por la luz del ambiente o por la mano de quien fotografía.

- Texto inclinado respecto a la horizontal.

- Distorsión de perspectiva, porque la cámara no queda paralela a la hoja.

- Bajo contraste, por papel amarillento, tinta tenue o cámaras de baja calidad.

- Ruido: granulado, arrugas y manchas.


Estos defectos dificultan la lectura, aumentan el tamaño de los archivos y bajan la exactitud del OCR (Reconocimiento Óptico de Caracteres). Sin un OCR confiable, el contenido no se puede buscar ni procesar de forma automática.

Pregunta central: ¿cuánto mejora un preprocesamiento automático de imágenes la legibilidad de documentos fotografiados y la exactitud del reconocimiento de caracteres?

## 2. OBJETIVO GENERAL

Desarrollar en Python una herramienta de procesamiento digital de imágenes que convierta fotografías de documentos en imágenes legibles y aptas para archivo digital.

## OBJETIVOS ESPECÍFICOS

- \- Transformar las fotografías

- \- Detectar los bordes del documento y corregir la perspectiva para obtener una vista frontal de la hoja.

- \- Convertir la imagen a escala de grises y aplicar CLAHE para mejorar el contraste local.

- \- Filtrar el ruido con un filtro gaussiano, de mediana o bilateral, y quedarse con el que mejor conserve los bordes del texto.

- \- Aplicar umbralización adaptativa para separar el texto del fondo y quitar las sombras.

- \- Medir el ángulo de inclinación del texto y corregirlo.

- \- Medir la legibilidad

- \- Calcular el contraste, la nitidez, el histograma y la relación señal/ruido de la imagen original y de la procesada.

- \- Mostrar el documento original y el procesado lado a lado, junto con sus histogramas.

- \- Medir el efecto sobre el OCR

- \- Integrar Tesseract y calcular el CER y el WER del texto extraído antes y después del procesamiento, tomando un texto de referencia como base.


- \- Comparar el CER y el WER de cada configuración (sin procesar, solo CLAHE, solo umbralización y flujo completo) para saber qué etapa mejora más la exactitud del OCR.

## 3. ALCANCE

Entrada. Fotografías de documentos en JPG o PNG (formularios, actas, oficios).

Procesamiento. Corrección de perspectiva, escala de grises, CLAHE, filtrado de ruido, umbralización adaptativa y corrección de inclinación.

Interfaz. Una aplicación sencilla (Tkinter, Streamlit o línea de comandos) con vista lado a lado.

Evaluación visual. Histogramas, contraste, nitidez y comparación de imágenes.

OCR. Tesseract mediante pytesseract, con CER y WER calculados contra un texto de referencia.

Salida. Imagen procesada en PNG o PDF y un reporte de métricas.

Herramientas. Python, OpenCV, NumPy, Matplotlib, scikit-image y pytesseract.

## FUERA DEL ALCANCE

Manuscritos complejos, sellos superpuestos y documentos no rectangulares.

Reconocimiento de estructura: tablas, campos de formulario y firmas.

Documentos muy dañados, rotos, muy doblados o con zonas ilegibles.

Redes neuronales profundas. El proyecto usa visión clásica.

Sistemas de gestión documental o bases de datos institucionales.

Procesamiento de video en tiempo real.

Supuestos

El documento aparece completo en la foto y se distingue del fondo.

El texto es impreso y está en español.

La resolución mínima recomendada es de 1000 × 1400 px.a


## 4. JUSTIFICACIÓN

Práctica. Digitalizar con el celular evita comprar escáneres y mejora la calidad de los archivos que ya existen.

Técnica. Une varias técnicas clásicas de visión por computadora en un solo flujo de trabajo.

Académica. Permite medir qué aporta cada etapa al OCR. Por ejemplo, se puede comparar el CER de la imagen sin procesar, con solo CLAHE, con solo umbralización y con el flujo completo.

## 5. LINK GITHUB

[https://github.com/edy-cell/DoCam](https://github.com/edy-cell/DoCam)
