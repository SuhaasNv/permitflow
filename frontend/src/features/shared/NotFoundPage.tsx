import { Logo } from './Logo'
import { NotFoundPanel } from './states'

/** Any address the route table does not know: a page of its own, with an h1 and a way back. */
export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col bg-surface text-text">
      <header className="border-b border-line">
        <div className="mx-auto flex h-[72px] max-w-[1440px] items-center px-5 sm:px-10">
          <Logo />
        </div>
      </header>
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-lg px-4 py-10 outline-none">
        <NotFoundPanel
          titleAs="h1"
          backTo="/"
          backLabel="Back to PermitFlow"
          title="Page not found"
          description="There is nothing at this address. Check the link, or start from the front page."
        />
      </main>
    </div>
  )
}
