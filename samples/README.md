# 🧩 Muestras de Código de Producción (samples/)

Esta carpeta contiene módulos reales extraídos sin modificaciones del repositorio privado **Portfolio_lab** (~104.000 LOC, 247 módulos) para ilustrar el estilo de código, tipado, documentación, concurrencia y rigor contra sesgos cuantitativos sin exponer los factores propietarios:

| Archivo | Ruta original en Portfolio_lab | Qué demuestra |
| :--- | :--- | :--- |
| [conftest.py](conftest.py) | 	ests/conftest.py | **Ingeniería de QA:** Redirección del entorno HOME/USERPROFILE antes de importar módulos y verificación por huella al finalizar la sesión de ~2.000 tests para garantizar cero efectos secundarios en la base de datos real del usuario. |
| [red.py](fred.py) | utils/fred.py | **Higiene Anti-Look-Ahead (*Point-in-Time*):** Descarga de series macroeconómicas de la Reserva Federal (FRED) desplazando la fecha de referencia al día exacto de su publicación oficial (_fecha_publicacion=True). |
| [cache.py](cache.py) | utils/cache.py | **Concurrencia y Persistencia:** SmartCache sobre SQLite *thread-safe* con expiración adaptativa según horario de cierre de mercado estadounidense (16:30 ET). |
| [etiquetas_validacion.py](etiquetas_validacion.py) | ui/etiquetas_validacion.py | **Honestidad Estadística:** Clasificación auditable de cada estrategia según su estadístico *t* fuera de muestra tras costes y corrección de sesgo de supervivencia. |
| [ci.yml](ci.yml) | .github/workflows/ci.yml | **CI/CD:** Ejecución automatizada de la suite de tests y cobertura en matriz Python 3.11 / 3.12 con cancelación de ejecuciones concurrentes. |