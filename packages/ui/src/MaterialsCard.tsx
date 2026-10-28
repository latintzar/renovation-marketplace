import ApplePayButtonLib from 'apple-pay-button';
import GooglePayButton from '@google-pay/button-react';

interface MaterialsCardProps {
  /** Card holder name to display */
  cardHolder?: string;
  /** Card number to display (masked) */
  cardNumber?: string;
  /** Whether to show the split explanation below */
  showSplit?: boolean;
  /** Whether to show Apple/Google Pay buttons */
  showPayButtons?: boolean;
  /** Custom class name */
  className?: string;
}

export const MaterialsCard: React.FC<MaterialsCardProps> = ({ 
  cardHolder = 'J. MITCHELL',
  cardNumber = '•••• •••• •••• 4821',
  showSplit = true,
  showPayButtons = true,
  className = '' 
}) => {
  return (
    <div className={`w-full max-w-[380px] flex flex-col gap-4 ${className}`}>
      <div className="w-full h-[240px] rounded-md p-[22px_26px] bg-cream shadow-[0_2px_0_rgba(0,0,0,.06),0_10px_36px_rgba(0,0,0,.24),inset_0_0_0_1px_rgba(0,0,0,.07)] relative overflow-hidden isolate flex flex-col justify-between box-border">
        {/* Warm grain texture */}
        <div 
          className="absolute inset-0 z-0 opacity-[.022] pointer-events-none"
          style={{
            backgroundImage: "none",
            backgroundSize: '128px'
          }}
        />
        
        {/* Soft terra highlight top-left */}
        <div 
          className="absolute -top-[60px] -left-[50px] w-[260px] h-[260px] rounded-full z-0 pointer-events-none"
          style={{
            background: 'radial-gradient(circle,rgba(218,101,77,.08) 0%,transparent 70%)'
          }}
        />

        {/* TOP: Leo wordmark + EMV contactless symbol */}
        <div className="relative z-10 flex items-start justify-between">
          <div>
            <img src="/brand/leo-charcoal.svg" alt="Leo" height={22} style={{ width: 'auto' }} draggable={false} />
            <div className="text-[9px] font-bold tracking-[.13em] uppercase text-muted mt-1">Materials Card</div>
          </div>
          
          {/* EMV contactless: 4 concentric arcs */}
          <svg width="20" height="26" viewBox="0 0 20 26" fill="none" className="opacity-50" aria-hidden="true">
            <path d="M2.5 10 A3.9 3.9 0 0 1 2.5 16" stroke="#1C1917" strokeWidth="2.5" strokeLinecap="round"/>
            <path d="M5.5 7 A7.8 7.8 0 0 1 5.5 19" stroke="#1C1917" strokeWidth="2.5" strokeLinecap="round"/>
            <path d="M8.5 4 A11.7 11.7 0 0 1 8.5 22" stroke="#1C1917" strokeWidth="2.5" strokeLinecap="round"/>
            <path d="M11.5 1 A15.7 15.7 0 0 1 11.5 25" stroke="#1C1917" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
        </div>

        {/* MIDDLE: Chip */}
        <div className="relative z-10">
          <div 
            className="w-[46px] h-[34px] rounded-sm shadow-[0_1px_4px_rgba(0,0,0,.2)] relative overflow-hidden"
            style={{
              background: 'linear-gradient(145deg,#E8C96B 0%,#C8A020 35%,#E0B84A 55%,#B89020 80%,#D4A030 100%)'
            }}
          >
            <div 
              className="absolute inset-0 rounded-inherit"
              style={{
                background: 'repeating-linear-gradient(0deg,transparent,transparent 8px,rgba(0,0,0,.04) 8px,rgba(0,0,0,.04) 9px),repeating-linear-gradient(90deg,transparent,transparent 10px,rgba(0,0,0,.04) 10px,rgba(0,0,0,.04) 11px)'
              }}
            />
            <div className="absolute top-1/2 left-0 right-0 h-px bg-black/10 -translate-y-1/2" />
            <div className="absolute left-1/2 top-1 bottom-1 w-px bg-black/[.08] -translate-x-1/2" />
          </div>
        </div>

        {/* BOTTOM: card number + name/expiry/Mastercard */}
        <div className="relative z-10">
          <div className="text-[15px] font-medium tracking-[.26em] text-stone mb-3 font-mono">{cardNumber}</div>
          <div className="flex items-end justify-between gap-[10px]">
            <div className="flex-1 min-w-0">
              <div className="text-[9px] tracking-[.09em] uppercase text-muted mb-[3px]">Card Holder</div>
              <div className="text-[13px] font-semibold text-ink tracking-[.05em] uppercase">{cardHolder}</div>
            </div>
            <div>
              <div className="text-[9px] tracking-[.09em] uppercase text-muted mb-[3px]">Expires</div>
              <div className="text-[13px] font-semibold text-ink tracking-[.05em]">03/28</div>
            </div>
            {/* Mastercard overlapping circles */}
            <div className="flex items-center flex-shrink-0">
              <div className="w-8 h-8 rounded-full bg-[#EB001B] opacity-90"></div>
              <div className="w-8 h-8 rounded-full bg-[#F79E1B] opacity-90 -ml-3 mix-blend-multiply"></div>
            </div>
          </div>
        </div>
      </div>

        {/* Apple Pay / Google Pay — official components */}
        {showPayButtons && (
          <div className="grid grid-cols-2 gap-[10px] w-full">
            <ApplePayButtonLib
              type="plain"
              buttonStyle="black"
              locale="en-US"
              onClick={() => {}}
              style={{ width: '100%', height: '44px', borderRadius: '8px' }}
            />
            <GooglePayButton
              environment="TEST"
              buttonType="plain"
              buttonColor="black"
              buttonSizeMode="fill"
              paymentRequest={{
                apiVersion: 2,
                apiVersionMinor: 0,
                allowedPaymentMethods: [{
                  type: 'CARD',
                  parameters: {
                    allowedAuthMethods: ['PAN_ONLY', 'CRYPTOGRAM_3DS'],
                    allowedCardNetworks: ['MASTERCARD', 'VISA'],
                  },
                  tokenizationSpecification: {
                    type: 'PAYMENT_GATEWAY',
                    parameters: { gateway: 'example', gatewayMerchantId: 'example' },
                  },
                }],
                merchantInfo: { merchantId: '01234567890123456789', merchantName: 'Leo' },
                transactionInfo: {
                  totalPriceStatus: 'FINAL',
                  totalPrice: '0.00',
                  currencyCode: 'EUR',
                  countryCode: 'ES',
                },
              }}
              style={{ width: '100%', height: '44px' }}
            />
          </div>
        )}

      {/* Payment History */}
      {showPayButtons && (
        <div className="bg-[var(--card-solid)] border border-[var(--border)] rounded-[var(--r)] overflow-hidden">
          <div className="p-3 border-b border-[var(--border)]">
            <div className="text-[10px] font-bold uppercase text-[var(--muted)] tracking-[.06em] mb-1">Recent Purchases</div>
          </div>
          <div className="divide-y divide-[var(--border)]">
            <div className="p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-[var(--teal-lt)] flex items-center justify-center">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--teal)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 9h18v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9Z"/>
                    <path d="m3 9 2.45-4.9A2 2 0 0 1 7.24 3h9.52a2 2 0 0 1 1.8 1.1L21 9"/>
                    <path d="M12 3v6"/>
                  </svg>
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-[var(--ink)]">Leroy Merlin</div>
                  <div className="text-[9px] text-[var(--muted)]">Today, 14:23</div>
                </div>
              </div>
              <div className="text-[11px] font-semibold text-[var(--ink)]">€84.50</div>
            </div>
            <div className="p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-[var(--terra-lt)] flex items-center justify-center">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--terra)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h1"/>
                    <path d="M16 3h1a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-1"/>
                    <path d="m7 12 5 5 5-5"/>
                  </svg>
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-[var(--ink)]">Brico Depot</div>
                  <div className="text-[9px] text-[var(--muted)]">Yesterday, 09:15</div>
                </div>
              </div>
              <div className="text-[11px] font-semibold text-[var(--ink)]">€156.30</div>
            </div>
          </div>
        </div>
      )}

      {/* Split explanation: Materials vs Labor & Overhead */}
      {showSplit && (
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-[var(--card-solid)] border border-[var(--border)] rounded-[var(--r)] p-3 text-center">
            <div className="text-[10px] font-bold uppercase text-[var(--muted)] tracking-[.06em] mb-1">Materials</div>
            <div className="text-[11px] text-[var(--stone)] leading-snug">Leo Card → Suppliers only</div>
          </div>
          <div className="bg-[var(--card-solid)] border border-[var(--border)] rounded-[var(--r)] p-3 text-center">
            <div className="text-[10px] font-bold uppercase text-[var(--muted)] tracking-[.06em] mb-1">Labor & Overhead</div>
            <div className="text-[11px] text-[var(--stone)] leading-snug">Secure escrow → Released on approval</div>
          </div>
        </div>
      )}
    </div>
  );
};