interface Props {
  id: string
  message?: string
}

export function FieldError({ id, message }: Props) {
  if (!message) return null
  return (
    <p id={id} role="alert" className="text-destructive text-xs">
      {message}
    </p>
  )
}
