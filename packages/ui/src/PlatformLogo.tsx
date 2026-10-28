export interface PlatformLogoProps {
  platform: 'habitissimo' | 'houzz' | 'cronoshare' | 'hogami';
  size?: 'sm' | 'md' | 'lg';
  variant?: 'inline' | 'card';
  className?: string;
}

const PLATFORM_CONFIG = {
  habitissimo: {
    logo: '/logo-habitissimo.png',
    name: 'Habitissimo',
  },
  houzz: {
    logo: '/logo-houzz.png', 
    name: 'Houzz',
  },
  cronoshare: {
    logo: '/logo-cronoshare.png',
    name: 'CronoShare',
  },
  hogami: {
    logo: '/logo-hogami.png',
    name: 'Hogami',
  },
} as const;

const SIZE_CLASSES = {
  sm: 'w-4 h-4', // 16px
  md: 'w-5 h-5', // 20px 
  lg: 'w-6 h-6', // 24px
} as const;

export function PlatformLogo({ 
  platform, 
  size = 'md', 
  variant = 'inline',
  className 
}: PlatformLogoProps) {
  const config = PLATFORM_CONFIG[platform];
  // Resolve against the app's base URL so logos work when the app is served
  // from a sub-path (e.g. the vendored /scope/app/) — root deploys get '/' = unchanged.
  const logoSrc = import.meta.env.BASE_URL + config.logo.replace(/^\//, '');

  if (variant === 'card') {
    // Card variant - for review/testimonial cards
    return (
      <div 
        className={[
          'rounded-md bg-white flex items-center justify-center flex-shrink-0 border border-black/8',
          size === 'sm' ? 'w-6 h-6' : size === 'md' ? 'w-8 h-8' : 'w-10 h-10',
          className
        ].filter(Boolean).join(' ')}
      >
        <img
          src={logoSrc}
          alt={config.name}
          className={SIZE_CLASSES[size] + ' object-contain'}
        />
      </div>
    );
  }

  // Inline variant - for buttons, etc.
  return (
    <img
      src={logoSrc}
      alt={config.name}
      className={[SIZE_CLASSES[size], 'object-contain', className].filter(Boolean).join(' ')}
    />
  );
}