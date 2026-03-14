# Guía: Descargar modelos desde Hugging Face

Esta guía explica cómo descargar los modelos de lenguaje al SSD usando la CLI `hf` que ya está instalada en el entorno virtual del proyecto.

---

## Requisitos previos

```bash
# Activar el entorno virtual del proyecto
source /home/jleon/2026/PUCP/GTR/CDN/ai_env/bin/activate

# Verificar que hf está disponible
hf --version   # debe mostrar huggingface_hub 1.5.0 o superior
```

---

## Paso 1 — Iniciar sesión en Hugging Face

```bash
hf login
```

Se te pedirá un token. Obténlo en:  
**https://huggingface.co/settings/tokens** → *New token* → tipo **Read** → copiar y pegar.

El token se guarda en `~/.cache/huggingface/token` y no hace falta repetir este paso.

---

## Paso 2 — Descargar Phi-3.5-mini-instruct (modelo activo)

```bash
hf download microsoft/Phi-3.5-mini-instruct \
  --local-dir /mnt/ssd/models/hf_models/Phi-3.5-mini-instruct
```

- Tamaño: ~7.2 GB (bf16)
- Si la descarga se interrumpe: **vuelve a ejecutar el mismo comando** — `hf download` reanuda automáticamente desde donde se quedó.

---

## Paso 3 — Descargar Llama-3.2-1B-Instruct (modelo draft / ligero)

> **Importante:** Llama requiere aceptar los términos de uso de Meta antes de poder descargarlo.  
> Ve a **https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct** → botón *"Agree and access repository"* → espera la aprobación (suele ser inmediata).

```bash
hf download meta-llama/Llama-3.2-1B-Instruct \
  --local-dir /mnt/ssd/models/hf_models/Llama-3.2-1B-Instruct
```

- Tamaño: ~2.5 GB

---

## Paso 4 — Actualizar `.env`

Si los modelos se descargan en una ruta distinta, actualiza el archivo `.env` en la raíz del proyecto:

```env
TARGET_MODEL_DIR=/mnt/ssd/models/hf_models/Phi-3.5-mini-instruct
DRAFT_MODEL_DIR=/mnt/ssd/models/hf_models/Llama-3.2-1B-Instruct
```

---

## Verificar la descarga

```bash
# Ver tamaño de cada modelo
du -sh /mnt/ssd/models/hf_models/Phi-3.5-mini-instruct
du -sh /mnt/ssd/models/hf_models/Llama-3.2-1B-Instruct

# Ver espacio libre en el SSD
df -h /mnt/ssd
```

---

## Sintaxis alternativa (si `hf` da problemas)

```bash
# Con huggingface-cli (equivalente)
huggingface-cli download microsoft/Phi-3.5-mini-instruct \
  --local-dir /mnt/ssd/models/hf_models/Phi-3.5-mini-instruct

# O directamente con Python
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='microsoft/Phi-3.5-mini-instruct',
    local_dir='/mnt/ssd/models/hf_models/Phi-3.5-mini-instruct'
)
"
```

---

## Solución de problemas

| Síntoma | Causa | Solución |
|---|---|---|
| `401 Unauthorized` | Token inválido o expirado | `hf logout && hf login` con token nuevo |
| `Repository not found` (Llama) | Términos de uso no aceptados | Ir a la página del modelo en HF y aceptar |
| Descarga lenta o cortada | Conexión inestable | Volver a ejecutar el mismo comando (reanuda) |
| `No space left on device` | SSD lleno | `df -h /mnt/ssd` — liberar espacio primero |
| `hf: command not found` | Entorno no activado | `source ai_env/bin/activate` |
| Modelo no carga en el servidor | Ruta incorrecta en `.env` | Verificar con `ls $TARGET_MODEL_DIR/config.json` |

---

## Modelos probados en este proyecto

| Modelo | Tamaño | Uso | Estado |
|---|---|---|---|
| `microsoft/Phi-3.5-mini-instruct` | 7.2 GB | Motor LLM principal | ✅ En producción |
| `meta-llama/Llama-3.2-1B-Instruct` | 2.5 GB | Draft / respaldo ligero | ✅ Descargado |
