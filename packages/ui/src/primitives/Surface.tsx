import { forwardRef, type ComponentPropsWithRef, type ElementType, type ReactNode } from 'react';

const VARIANT_CLASSES = {
  flat:   'bg-white border border-border',
  lifted: 'bg-white border border-border shadow-sm',
  raised: 'bg-white shadow-[0_-4px_20px_rgba(0,0,0,0.12)]',
} as const;

const ROUNDED_CLASSES = {
  xs:   'rounded-xs',
  sm:   'rounded-sm',
  md:   'rounded-md',
  lg:   'rounded-lg',
  xl:   'rounded-xl',
  pill: 'rounded-full',
  none: 'rounded-none',
} as const;

const PADDING_CLASSES = {
  none: '',
  sm:   'p-3',
  md:   'p-4',
  lg:   'p-6',
} as const;

export type SurfaceVariant = keyof typeof VARIANT_CLASSES;
export type SurfaceRounded = keyof typeof ROUNDED_CLASSES;
export type SurfacePadding = keyof typeof PADDING_CLASSES;

export interface SurfaceProps extends Omit<ComponentPropsWithRef<'div'>, 'children'> {
  variant?: SurfaceVariant;
  rounded?: SurfaceRounded;
  padding?: SurfacePadding;
  as?: ElementType;
  children?: ReactNode;
}

export const Surface = forwardRef<HTMLDivElement, SurfaceProps>(
  ({ variant = 'flat', rounded = 'sm', padding = 'md', as: Tag = 'div', className, children, ...rest }, ref) => {
    const classes = [
      VARIANT_CLASSES[variant],
      ROUNDED_CLASSES[rounded],
      PADDING_CLASSES[padding],
      className,
    ].filter(Boolean).join(' ');

    return (
      <Tag ref={ref} className={classes} {...rest}>
        {children}
      </Tag>
    );
  }
);

Surface.displayName = 'Surface';
