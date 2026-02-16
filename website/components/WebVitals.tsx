'use client';

import { useReportWebVitals } from 'next/web-vitals';

export default function WebVitals() {
  useReportWebVitals((metric) => {
    if (typeof window !== 'undefined' && window.plausible) {
      window.plausible('Web Vitals', {
        props: {
          name: metric.name,
          value: Math.round(
            metric.name === 'CLS' ? metric.value * 1000 : metric.value
          ),
          rating: metric.rating,
        },
      });
    }
  });

  return null;
}
