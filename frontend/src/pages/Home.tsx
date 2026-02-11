import { useQuery } from '@tanstack/react-query'
import api from '../services/api'

function Home() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await api.get('/health')
      return response.data
    },
  })

  return (
    <div className="container mx-auto px-4 py-8">
      <header className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">
          Equity Research Agent
        </h1>
        <p className="text-gray-600 mt-2">
          AI-powered equity research and analysis platform
        </p>
      </header>

      <main className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-semibold mb-4">System Status</h2>
        {isLoading && <p className="text-gray-600">Connecting to backend...</p>}
        {error && (
          <p className="text-red-600">Error connecting to backend</p>
        )}
        {data && (
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 bg-green-500 rounded-full"></div>
            <p className="text-green-700 font-medium">Backend: {data.status}</p>
          </div>
        )}
      </main>
    </div>
  )
}

export default Home
