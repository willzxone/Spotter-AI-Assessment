import type { ProcedureInput, ProcedureOutput, ProcedurePath } from './api.gen'

/**
 * The codes in the API's error envelope (backend `core/errors.py`), plus
 * `NETWORK` for when no readable response came back at all.
 */
export type RpcErrorCode =
  | 'BAD_REQUEST'
  | 'VALIDATION_FAILED'
  | 'NOT_FOUND'
  | 'RATE_LIMITED'
  | 'UPSTREAM_UNAVAILABLE'
  | 'SERVICE_DISABLED'
  | 'INTERNAL'
  | 'NETWORK'

export interface RpcIssue {
  path: string
  message: string
}

/** Worth retrying unchanged: the request was fine, something between us and the data was not. */
const TRANSIENT: ReadonlySet<RpcErrorCode> = new Set([
  'NETWORK',
  'UPSTREAM_UNAVAILABLE',
])

export class RpcError extends Error {
  readonly code: RpcErrorCode
  /** HTTP status, or 0 when the request never got a response. */
  readonly status: number
  readonly data: Readonly<Record<string, unknown>>
  readonly requestId: string | null

  constructor(
    code: RpcErrorCode,
    message: string,
    status: number,
    data: Record<string, unknown> = {},
    requestId: string | null = null,
  ) {
    super(message)
    this.name = 'RpcError'
    this.code = code
    this.status = status
    this.data = data
    this.requestId = requestId
  }

  get transient(): boolean {
    return TRANSIENT.has(this.code)
  }

  /** Per-field problems from a `VALIDATION_FAILED` response. */
  get issues(): RpcIssue[] {
    const issues = this.data.issues
    return Array.isArray(issues) ? issues.filter(isIssue) : []
  }
}

function isIssue(value: unknown): value is RpcIssue {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as RpcIssue).path === 'string' &&
    typeof (value as RpcIssue).message === 'string'
  )
}

interface Envelope {
  error: {
    code: RpcErrorCode
    message: string
    data?: Record<string, unknown>
    requestId?: string
  }
}

function isEnvelope(body: unknown): body is Envelope {
  if (typeof body !== 'object' || body === null || !('error' in body)) {
    return false
  }
  // `'error' in body` already narrowed `body` to `{ error: unknown }`.
  const error = body.error
  return (
    typeof error === 'object' &&
    error !== null &&
    typeof (error as Envelope['error']).code === 'string' &&
    typeof (error as Envelope['error']).message === 'string'
  )
}

const UNREACHABLE =
  "Can't reach the server. Check your connection and try again."

interface CallOptions {
  signal?: AbortSignal
}

/**
 * Call one procedure. Every procedure is `POST /rpc/<path>` with a JSON body and
 * answers either its output or the error envelope, which is thrown as an `RpcError`.
 */
export async function rpc<TPath extends ProcedurePath>(
  path: TPath,
  input: ProcedureInput<TPath>,
  { signal }: CallOptions = {},
): Promise<ProcedureOutput<TPath>> {
  let response: Response
  try {
    response = await fetch(`/rpc/${path}`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: input === undefined ? undefined : JSON.stringify(input),
      signal,
    })
  } catch (error) {
    // An abort is the caller's doing (TanStack Query cancelling a stale request), not a failure.
    if (signal?.aborted) throw error
    throw new RpcError('NETWORK', UNREACHABLE, 0)
  }

  const body: unknown = await response.json().catch(() => null)
  if (response.ok) return body as ProcedureOutput<TPath>

  if (isEnvelope(body)) {
    const { code, message, data, requestId } = body.error
    throw new RpcError(code, message, response.status, data, requestId ?? null)
  }
  // A proxy or gateway answered instead of the API.
  throw new RpcError(
    response.status >= 500 ? 'UPSTREAM_UNAVAILABLE' : 'NETWORK',
    response.status >= 500
      ? 'The server is unavailable right now. Try again in a moment.'
      : UNREACHABLE,
    response.status,
  )
}

/** A query key for a procedure call: the path, then its input. */
export function rpcKey<TPath extends ProcedurePath>(
  path: TPath,
  input: ProcedureInput<TPath> | null,
) {
  return ['rpc', path, input] as const
}

/** A sentence for the user, whatever was thrown. */
export function errorMessage(error: unknown): string {
  if (error instanceof RpcError) return error.message
  return 'Something went wrong. Try again.'
}
