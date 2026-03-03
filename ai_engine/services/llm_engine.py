"""
services/llm_engine.py — Motor LLM con speculative decoding (TensorRT-LLM).
GTR-PUCP CDN Educativa Offline

Estrategia de generación:
  - En Jetson (CUDA disponible + TRT-LLM instalado):
      Speculative decoding: draft model (1B INT4) propone gamma tokens,
      target model (8B INT4) los valida en paralelo → 2.5-3× más rápido.
  - En PC sin TRT-LLM (modo desarrollo):
      Fallback a transformers (AutoModelForCausalLM) si está disponible,
      o a generación de placeholder si no hay ningún modelo cargado.

Ver docs/ai-search-engine-plan.md §6 para detalles de speculative decoding.
"""
from __future__ import annotations
import asyncio
import logging
from typing import AsyncIterator, Optional

from ai_engine.config import settings

logger = logging.getLogger(__name__)

# Tokens de parada comunes para señalizar fin de respuesta
_STOP_TOKENS = ["<|end|>", "<|endoftext|>", "<|im_end|>", "</s>", "[EOS]"]


class LLMEngine:
    """
    Wrapper sobre TensorRT-LLM con speculative decoding.
    Fallback a transformers cuando TRT-LLM no está disponible (desarrollo).
    """

    def __init__(self):
        self.is_ready:      bool = False
        self._draft                  = None   # TRT-LLM draft runner (1B INT4)
        self._target                 = None   # TRT-LLM target runner (8B INT4)
        self._hf_model               = None   # Fallback: HuggingFace model
        self._hf_tokenizer           = None   # Fallback: HuggingFace tokenizer
        self._mode:         str  = "none"     # "trtllm" | "hf" | "none"

    # ── Inicialización ─────────────────────────────────────────────────────────

    async def init(self) -> None:
        """
        Carga los modelos LLM. Intenta TRT-LLM primero; si no está disponible,
        intenta cargar un modelo HF ligero como fallback de desarrollo.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_sync)

    def _init_sync(self) -> None:
        """Carga síncrona ejecutada en un executor para no bloquear el event loop."""

        # ── Intento 1: TensorRT-LLM ────────────────────────────────────────
        if self._try_load_trtllm():
            self._mode    = "trtllm"
            self.is_ready = True
            return

        # ── Intento 2: Transformers (fallback para desarrollo) ─────────────
        if self._try_load_hf():
            self._mode    = "hf"
            self.is_ready = True
            return

        # ── Sin modelo disponible ──────────────────────────────────────────
        logger.warning(
            "LLMEngine: ni TRT-LLM ni transformers disponibles. "
            "Usando respuestas de placeholder. Instalar transformers para desarrollo."
        )
        self._mode    = "none"
        self.is_ready = True   # Marcamos ready para no bloquear — generate_stream hace fallback

    def _try_load_trtllm(self) -> bool:
        """Carga los runners TRT-LLM. Retorna True si tuvo éxito."""
        try:
            from tensorrt_llm.runtime import ModelRunnerCpp  # type: ignore
            logger.info("Cargando TRT-LLM draft model desde %s ...", settings.DRAFT_MODEL_DIR)
            self._draft = ModelRunnerCpp.from_dir(
                engine_dir=settings.DRAFT_MODEL_DIR,
                rank=0,
                max_batch_size=1,
            )
            logger.info("Cargando TRT-LLM target model desde %s ...", settings.TARGET_MODEL_DIR)
            self._target = ModelRunnerCpp.from_dir(
                engine_dir=settings.TARGET_MODEL_DIR,
                rank=0,
                max_batch_size=1,
            )
            logger.info(
                "✓ TRT-LLM listo — speculative: %s γ=%d",
                settings.SPECULATIVE_DECODING,
                settings.SPECULATIVE_GAMMA,
            )
            return True
        except ImportError:
            logger.info("TRT-LLM no instalado — continuando con fallback")
            return False
        except Exception as exc:
            logger.warning("Error cargando TRT-LLM: %s", exc)
            return False

    def _try_load_hf(self) -> bool:
        """
        Intenta cargar un modelo ligero de HuggingFace para desarrollo en PC.
        Usa el TARGET_MODEL_DIR si apunta a un directorio local HF,
        o un modelo genérico pequeño si no existe el directorio.
        """
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM   # type: ignore

            # Intentar cargar desde el directorio del target si existe
            import os
            model_path = settings.TARGET_MODEL_DIR
            if not os.path.isdir(model_path):
                # En PC de desarrollo, si no hay modelo local, no forzar descarga
                logger.info("HF fallback: TARGET_MODEL_DIR no existe (%s) — sin HF model", model_path)
                return False

            device = "cuda" if torch.cuda.is_available() else "cpu"
            # bfloat16 funciona en CPU moderno (Intel Xeon/Alder Lake+) y reduce memoria a la mitad
            dtype = torch.float16 if device == "cuda" else torch.bfloat16
            logger.info("Cargando HF model desde %s en %s (dtype=%s)...", model_path, device, dtype)
            self._hf_tokenizer = AutoTokenizer.from_pretrained(model_path)
            self._hf_model = AutoModelForCausalLM.from_pretrained(
                model_path,
                dtype=dtype,
                device_map=device,
                low_cpu_mem_usage=True,
            )
            self._hf_model.eval()
            logger.info("✓ HF model cargado en %s", device)
            return True
        except ImportError:
            logger.info("transformers no instalado — sin HF fallback")
            return False
        except Exception as exc:
            logger.warning("Error cargando HF model: %s", exc)
            return False

    # ── Generación de texto ────────────────────────────────────────────────────

    async def generate_stream(
        self,
        prompt:     str,
        gamma:      Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Genera texto en modo streaming (token a token).

        Args:
            prompt: Prompt completo (system + context + query).
            gamma:  Tokens por paso especulativos; None usa settings.SPECULATIVE_GAMMA.

        Yields:
            str — tokens individuales o fragmentos de texto.
        """
        if not self.is_ready:
            raise RuntimeError("LLM engine no inicializado — llamar a init() primero")

        effective_gamma = gamma if gamma is not None else settings.SPECULATIVE_GAMMA

        if self._mode == "trtllm":
            async for tok in self._stream_trtllm(prompt, effective_gamma):
                yield tok
        elif self._mode == "hf":
            async for tok in self._stream_hf(prompt):
                yield tok
        else:
            # Sin modelo: respuesta de placeholder
            async for tok in self._stream_placeholder(prompt):
                yield tok

    async def _stream_trtllm(self, prompt: str, gamma: int) -> AsyncIterator[str]:
        """Generación con TensorRT-LLM usando speculative decoding."""
        loop = asyncio.get_event_loop()
        # TRT-LLM no es async nativo; ejecutamos el decode en un executor
        # y enviamos tokens a una queue que el caller consume
        queue: asyncio.Queue = asyncio.Queue()

        def _decode_worker():
            """Ejecutado en executor. Pone tokens en la queue."""
            try:
                import torch
                from tensorrt_llm.runtime import SamplingConfig   # type: ignore

                # Tokenizar el prompt
                tokenizer = self._target.tokenizer  # type: ignore
                input_ids = tokenizer.encode(prompt, return_tensors="pt")

                sampling_cfg = SamplingConfig(
                    end_id=tokenizer.eos_token_id,
                    pad_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                    max_new_tokens=settings.MAX_GENERATION_TOKENS,
                    temperature=0.7,
                    top_p=0.9,
                )

                if settings.SPECULATIVE_DECODING and self._draft is not None:
                    # Speculative decoding: draft propone, target valida
                    # gamma dinámico desde thermal_manager si se pasa explícitamente
                    output_ids = self._target.generate(   # type: ignore
                        input_ids,
                        sampling_config=sampling_cfg,
                        draft_runner=self._draft,
                        num_draft_tokens=gamma,
                    )
                else:
                    output_ids = self._target.generate(input_ids, sampling_config=sampling_cfg)  # type: ignore

                # Decodificar token a token y poner en la cola
                input_len = input_ids.shape[-1]
                generated = output_ids[0][input_len:]
                for tok_id in generated:
                    tok_str = tokenizer.decode([tok_id], skip_special_tokens=True)
                    if tok_str:
                        loop.call_soon_threadsafe(queue.put_nowait, tok_str)
            except Exception as exc:
                logger.error("Error en TRT-LLM decode: %s", exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)   # sentinel

        loop.run_in_executor(None, _decode_worker)

        while True:
            tok = await queue.get()
            if tok is None:
                break
            # Filtrar tokens de fin de secuencia
            if any(stop in tok for stop in _STOP_TOKENS):
                break
            yield tok

    async def _stream_hf(self, prompt: str) -> AsyncIterator[str]:
        """Generación con HuggingFace transformers (fallback de desarrollo)."""
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _hf_worker():
            try:
                import torch
                from transformers import TextIteratorStreamer   # type: ignore
                import threading

                inputs = self._hf_tokenizer(   # type: ignore
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=settings.MAX_CONTEXT_TOKENS,
                ).to(self._hf_model.device)   # type: ignore

                streamer = TextIteratorStreamer(
                    self._hf_tokenizer,   # type: ignore
                    skip_prompt=True,
                    skip_special_tokens=True,
                )

                gen_kwargs = {
                    **inputs,
                    "max_new_tokens": settings.MAX_GENERATION_TOKENS,
                    "temperature":    0.7,
                    "do_sample":      True,
                    "top_p":          0.9,
                    "streamer":       streamer,
                }

                thread = threading.Thread(
                    target=self._hf_model.generate,   # type: ignore
                    kwargs=gen_kwargs,
                )
                thread.start()

                for text_chunk in streamer:
                    if text_chunk:
                        loop.call_soon_threadsafe(queue.put_nowait, text_chunk)

                thread.join()
            except Exception as exc:
                logger.error("Error en HF generate: %s", exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        loop.run_in_executor(None, _hf_worker)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            if any(stop in chunk for stop in _STOP_TOKENS):
                break
            yield chunk

    async def _stream_placeholder(self, prompt: str) -> AsyncIterator[str]:
        """
        Generador de placeholder para cuando no hay ningún modelo disponible.
        Produce un mensaje informativo en lugar de silencio.
        Solo se activa en modo desarrollo sin modelo local configurado.
        """
        logger.debug("LLM placeholder activado — sin modelo disponible")
        text = (
            "ℹ️ El motor de IA no tiene un modelo de lenguaje cargado en este entorno. "
            "Para pruebas de desarrollo usa el servidor mock (`mock_main.py`). "
            "En la Jetson, los modelos TRT-LLM se cargan automáticamente al iniciar."
        )
        for word in text.split():
            yield word + " "
            await asyncio.sleep(0.03)

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    async def shutdown(self) -> None:
        """Libera recursos (llamado al cerrar el servidor)."""
        self._draft     = None
        self._target    = None
        self._hf_model  = None
        self._hf_tokenizer = None
        self.is_ready   = False
        self._mode      = "none"
        logger.info("LLM engine descargado")


llm_engine = LLMEngine()
