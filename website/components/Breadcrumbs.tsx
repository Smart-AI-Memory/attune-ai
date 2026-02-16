import Link from 'next/link';
import { generateStructuredData, BreadcrumbItem } from '@/lib/metadata';

interface BreadcrumbProps {
  items: Array<{ name: string; href: string }>;
}

const BASE_URL = 'https://smartaimemory.com';

export default function Breadcrumbs({ items }: BreadcrumbProps) {
  const fullItems: BreadcrumbItem[] = [
    { name: 'Home', url: BASE_URL },
    ...items.map((item) => ({
      name: item.name,
      url: `${BASE_URL}${item.href}`,
    })),
  ];

  const structuredData = generateStructuredData('breadcrumb', {
    items: fullItems,
  });

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />
      <nav aria-label="Breadcrumb" className="text-sm text-[var(--muted)] mb-6">
        <ol className="flex items-center gap-1 flex-wrap">
          <li>
            <Link href="/" className="hover:text-[var(--primary)] transition-colors">
              Home
            </Link>
          </li>
          {items.map((item, index) => (
            <li key={item.href} className="flex items-center gap-1">
              <span aria-hidden="true">/</span>
              {index === items.length - 1 ? (
                <span aria-current="page" className="text-[var(--text-primary)]">
                  {item.name}
                </span>
              ) : (
                <Link href={item.href} className="hover:text-[var(--primary)] transition-colors">
                  {item.name}
                </Link>
              )}
            </li>
          ))}
        </ol>
      </nav>
    </>
  );
}
