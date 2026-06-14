import { HslColorPicker } from 'react-colorful';

interface ColorWheelProps {
  hue: number;
  saturation: number;
  lightness: number;
  width?: number;
  height?: number;
  onColorChange: (hsl: { h: number; s: number; l: number }) => void;
}

export function ColorWheel({
  hue,
  saturation,
  lightness,
  width = 200,
  height = 200,
  onColorChange,
}: ColorWheelProps) {
  return (
    <div className="color-wheel-container" style={{ width, height }}>
      <HslColorPicker
        color={{ h: hue, s: saturation, l: lightness }}
        onChange={(color) =>
          onColorChange({
            h: Math.round(color.h),
            s: Math.round(color.s),
            l: Math.round(color.l),
          })
        }
      />
    </div>
  );
}
