import { useVoiceRecorder } from '../../hooks/useVoiceRecorder'

interface Props {
  onResult: (query: string) => void
  disabled: boolean
}

export default function VoiceButton({ onResult, disabled }: Props) {
  const { recorderState, start, stop } = useVoiceRecorder(onResult)

  const isRecording   = recorderState === 'recording'
  const isProcessing  = recorderState === 'processing'

  function handleClick() {
    if (isRecording) stop()
    else start()
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled || isProcessing}
      aria-label={isRecording ? 'Detener grabación' : 'Búsqueda por voz'}
      title={isRecording ? 'Detener grabación' : 'Habla tu consulta'}
      className={[
        'flex h-9 w-9 items-center justify-center rounded-xl transition',
        isRecording
          ? 'animate-pulse bg-red-500 text-white'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
        (disabled || isProcessing) ? 'opacity-40 cursor-not-allowed' : '',
      ].join(' ')}
    >
      {isProcessing ? (
        /* Spinner */
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="10" strokeOpacity={0.3} />
          <path d="M12 2a10 10 0 0 1 10 10" />
        </svg>
      ) : (
        /* Micrófono */
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="2" width="6" height="12" rx="3" />
          <path d="M5 10a7 7 0 0 0 14 0" />
          <line x1="12" y1="19" x2="12" y2="22" />
          <line x1="9"  y1="22" x2="15" y2="22" />
        </svg>
      )}
    </button>
  )
}
