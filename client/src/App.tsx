import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full">
        <h1 className="text-4xl font-bold text-center text-indigo-600 mb-6">
          CDN Offline
        </h1>
        <p className="text-gray-600 text-center mb-8">
          Sistema de distribución de contenido educativo
        </p>
        <div className="space-y-4">
          <button 
            onClick={() => setCount((count) => count + 1)}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-6 rounded-lg transition duration-200 shadow-md hover:shadow-lg"
          >
            Contador: {count}
          </button>
          <div className="text-center text-sm text-gray-500">
            ✅ Tailwind CSS configurado correctamente
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

