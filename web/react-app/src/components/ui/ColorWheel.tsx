import { HsvColorPicker } from 'react-colorful';

interface ColorWheelProps {
  hue: number;
  saturation: number;
  value: number;
  width?: number;
  height?: number;
  onColorChange: (hsv: { h: number; s: number; v: number }) => void;
}

/** HSV picker: the controller's LEDs take hue/saturation/value, not HSL. */
export function ColorWheel({
  hue,
  saturation,
  value,
  width = 200,
  height = 200,
  onColorChange,
}: ColorWheelProps) {
  return (
    <div className="color-wheel-container" style={{ width, height }}>
      <HsvColorPicker
        color={{ h: hue, s: saturation, v: value }}
        onChange={(color) =>
          onColorChange({
            h: Math.round(color.h),
            s: Math.round(color.s),
            v: Math.round(color.v),
          })
        }
      />
    </div>
  );
}
