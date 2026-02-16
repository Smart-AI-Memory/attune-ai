'use client';

/**
 * @deprecated This component is deprecated as of January 28, 2026.
 * Attune AI is now fully open source under Apache 2.0.
 * No payments or license purchases are required.
 * This component is kept for historical purposes only.
 */

import { useState } from 'react';

interface CheckoutButtonProps {
  priceId: string;
  mode?: 'payment' | 'subscription';
  buttonText: string;
  className?: string;
  disabled?: boolean;
}

export default function CheckoutButton({
  priceId,
  mode = 'payment',
  buttonText,
  className = 'btn btn-primary w-full',
  disabled = false,
}: CheckoutButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCheckout = async () => {
    if (!priceId || priceId.startsWith('price_...')) {
      setError('Payment not yet configured. Please check back soon.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/stripe/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          priceId,
          mode,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Checkout failed');
      }

      // Redirect to Stripe Checkout
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setLoading(false);
    }
  };

  return (
    <div>
      <button
        onClick={handleCheckout}
        disabled={disabled || loading}
        className={`${className} ${loading ? 'opacity-70 cursor-wait' : ''}`}
      >
        {loading ? 'Loading...' : buttonText}
      </button>
      {error && (
        <p className="text-red-500 text-sm mt-2 text-center">{error}</p>
      )}
    </div>
  );
}
