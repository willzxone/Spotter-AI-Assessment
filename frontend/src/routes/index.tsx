import { createFileRoute } from '@tanstack/react-router'
import { PlannerPage } from '@/features/trips'

export const Route = createFileRoute('/')({
  component: PlannerPage,
})
