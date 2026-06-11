export function generateStaticParams() {
  return [{ username: '_' }]
}

export default function DossierLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
