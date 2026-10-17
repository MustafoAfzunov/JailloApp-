export default function Icon({ name, fill = false, size = 24, className = '' }) {
  return (
    <span className={`material-symbols-outlined ${fill ? 'fill' : ''} ${className}`} style={{ fontSize: size }} aria-hidden="true">
      {name}
    </span>
  )
}
