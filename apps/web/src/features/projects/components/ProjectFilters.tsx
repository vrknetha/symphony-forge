import { Input } from '@/shared/components/Input'
import { Select } from '@/shared/components/Select'
import { docTypes } from '@/shared/types/models'

interface ProjectFiltersProps {
  onSearchChange: (value: string) => void
  onTypeChange: (value: string) => void
  search: string
  type: string
}

export function ProjectFilters({
  onSearchChange,
  onTypeChange,
  search,
  type,
}: ProjectFiltersProps) {
  return (
    <div className="flex flex-wrap gap-3">
      <Input onChange={(event) => onSearchChange(event.target.value)} placeholder="Search documents" value={search} />
      <Select onChange={(event) => onTypeChange(event.target.value)} value={type}>
        <option value="ALL">All types</option>
        {docTypes.map((docType) => (
          <option key={docType} value={docType}>
            {docType}
          </option>
        ))}
      </Select>
    </div>
  )
}
