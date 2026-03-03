import { useState, useRef, useCallback } from 'react'

type RecorderState = 'idle' | 'recording' | 'processing' | 'error'

export function useVoiceRecorder(onResult: (query: string) => void) {
  const [recorderState, setRecorderState] = useState<RecorderState>('idle')
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef        = useRef<Blob[]>([])

  const start = useCallback(async () => {
    if (recorderState === 'recording') return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Preferir webm/opus (Chrome/Firefox); fallback a ogg
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/ogg;codecs=opus'

      const recorder = new MediaRecorder(stream, { mimeType })
      chunksRef.current = []

      recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }

      recorder.onstop = async () => {
        // Detener todas las pistas del stream
        stream.getTracks().forEach(t => t.stop())
        setRecorderState('processing')

        try {
          const blob     = new Blob(chunksRef.current, { type: mimeType })
          const formData = new FormData()
          formData.append('audio', blob, 'query.webm')

          const token = localStorage.getItem('cdn_token') ?? ''
          const res = await fetch('/api/ai/voice-search', {
            method:  'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body:    formData,
          })

          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          const data = await res.json() as { query_transcribed: string }
          onResult(data.query_transcribed)
        } catch {
          setRecorderState('error')
          return
        }
        setRecorderState('idle')
      }

      recorder.start()
      mediaRecorderRef.current = recorder
      setRecorderState('recording')
    } catch {
      setRecorderState('error')
    }
  }, [recorderState, onResult])

  const stop = useCallback(() => {
    mediaRecorderRef.current?.stop()
  }, [])

  return { recorderState, start, stop }
}
