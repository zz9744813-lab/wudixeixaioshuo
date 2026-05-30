import React from 'react';
import * as LucideIcons from 'lucide-react';

const DEFAULT_SIZE = 18;
const DEFAULT_STROKE = 1.75;

export function Icon({ name, size = DEFAULT_SIZE, strokeWidth = DEFAULT_STROKE, color, className = '', ...props }) {
  const Comp = LucideIcons[name];
  if (!Comp) return null;
  return (
    <Comp
      size={size}
      strokeWidth={strokeWidth}
      color={color}
      className={className}
      {...props}
    />
  );
}

export default Icon;
