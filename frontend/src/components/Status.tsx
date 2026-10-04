export function ErrorMessage({ message }: { message?: string }) {
  return message ? <p className="error-message" role="alert">{message}</p> : null
}

export function LoadingIndicator({ text }: { text: string }) {
  return <p className="loading-message" role="status"><span className="loading-dot" aria-hidden="true" />{text}</p>
}
