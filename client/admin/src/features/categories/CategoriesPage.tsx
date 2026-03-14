import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/apiClient'

interface Category {
  id: string
  name: string
  slug: string
  description: string | null
  parent_id: string | null
  icon: string | null
  color: string | null
  display_order: number
  is_active: boolean
  level?: number
}

interface CategoriesResponse {
  success: boolean
  data: Category[]
}

export default function CategoriesPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['categoriesTree'],
    queryFn: () =>
      apiClient
        .get<CategoriesResponse>('/api/categories/tree')
        .then(r => r.data.data),
  })

  const items = data ?? []
  const roots = items.filter(c => c.parent_id === null)
  const childrenOf = (parentId: string) => items.filter(c => c.parent_id === parentId)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500">
          {isLoading ? 'Cargando...' : `${items.length} categorías (${roots.length} áreas, ${items.length - roots.length} sub-categorías)`}
        </span>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        {isError && (
          <div className="flex flex-col items-center justify-center py-16 text-center p-6">
            <p className="text-sm font-semibold text-slate-600">Error al cargar categorías</p>
          </div>
        )}
        {!isLoading && !isError && (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-5 py-3">Categoría</th>
                <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Slug</th>
                <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-4 py-3">Descripción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {roots.map(root => (
                <>
                  {/* Root row */}
                  <tr key={root.id} className="bg-slate-50/60">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        {root.icon && <span className="text-base" role="img">{root.icon}</span>}
                        <span className="font-semibold text-slate-800 text-sm">{root.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400 font-mono">{root.slug}</td>
                    <td className="px-4 py-3 text-xs text-slate-500 max-w-xs">
                      <span className="line-clamp-1">{root.description ?? '—'}</span>
                    </td>
                  </tr>
                  {/* Child rows */}
                  {childrenOf(root.id).map(child => (
                    <tr key={child.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-5 py-2.5">
                        <div className="flex items-center gap-2 pl-5 border-l-2 border-slate-200 ml-2">
                          <span className="text-xs font-medium text-slate-700">{child.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-400 font-mono">{child.slug}</td>
                      <td className="px-4 py-2.5 text-xs text-slate-500 max-w-xs">
                        <span className="line-clamp-1">{child.description ?? '—'}</span>
                      </td>
                    </tr>
                  ))}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
