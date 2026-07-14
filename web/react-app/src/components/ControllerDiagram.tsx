import type { CSSProperties, KeyboardEvent } from 'react';
import {
  CONTROLLER_BUTTON_ZONES,
  CONTROLLER_VIEWBOX,
  getFaceColor,
  type ControllerZone,
} from './controllerZones';

interface ControllerDiagramProps {
  selectedButton?: string;
  mappings?: Record<string, string>;
  onButtonClick: (buttonId: string) => void;
  activeButtons?: ReadonlySet<string>;
  /** Show all hit zones permanently — for calibration screenshots */
  showAllZones?: boolean;
}

function zoneClasses(
  zone: ControllerZone,
  showAllZones: boolean,
  isSelected: boolean,
  isMapped: boolean,
  isActive: boolean,
) {
  return [
    zone.rear ? 'controller-zone__hit--rear' : 'controller-zone__hit',
    zone.face ? 'controller-zone__hit--face' : '',
    showAllZones ? 'controller-zone__hit--calibrate' : '',
    isSelected ? 'controller-zone__hit--selected' : '',
    isMapped ? 'controller-zone__hit--mapped' : '',
    isActive ? 'controller-zone__hit--active' : '',
  ]
    .filter(Boolean)
    .join(' ');
}

function ZoneHit({
  zone,
  className,
  style,
  onClick,
  isSelected,
}: {
  zone: ControllerZone;
  className: string;
  style?: CSSProperties;
  onClick: () => void;
  isSelected: boolean;
}) {
  const common = {
    className,
    style,
    onClick,
    role: 'button' as const,
    tabIndex: 0,
    'aria-label': `${zone.label} button`,
    'aria-pressed': isSelected,
    onKeyDown: (e: KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick();
      }
    },
  };

  if (zone.rear) {
    return (
      <rect
        x={zone.cx - zone.r}
        y={zone.cy - zone.r}
        width={zone.r * 2}
        height={zone.r * 2}
        rx={4}
        {...common}
      />
    );
  }

  return <circle cx={zone.cx} cy={zone.cy} r={zone.r} {...common} />;
}

export function ControllerDiagram({
  selectedButton,
  mappings = {},
  onButtonClick,
  activeButtons = new Set(),
  showAllZones = false,
}: ControllerDiagramProps) {
  const { width, height } = CONTROLLER_VIEWBOX;

  return (
    <div className={`controller-diagram ${showAllZones ? 'controller-diagram--calibrate' : ''}`}>
      <img
        src="/static/svg/controller.svg"
        alt="GameSir Tarantula Pro"
        className="controller-diagram__image"
        draggable={false}
      />
      <svg
        className="controller-diagram__overlay"
        viewBox={`0 0 ${width} ${height}`}
        aria-label="Controller button map"
      >
        {CONTROLLER_BUTTON_ZONES.map((zone) => {
          const isSelected = selectedButton === zone.id;
          const isMapped = Boolean(mappings[zone.id]);
          const isActive = activeButtons.has(zone.id);
          const faceColor = zone.face ? getFaceColor(zone.id) : undefined;
          const showLabel = zone.rear || showAllZones || isSelected || isMapped || isActive;

          return (
            <g key={zone.id} className="controller-zone">
              <ZoneHit
                zone={zone}
                className={zoneClasses(zone, showAllZones, isSelected, isMapped, isActive)}
                style={faceColor ? ({ '--face-color': faceColor } as CSSProperties) : undefined}
                onClick={() => onButtonClick(zone.id)}
                isSelected={isSelected}
              />
              {showLabel && (
                <>
                  {showAllZones && !zone.rear && (
                    <>
                      <line
                        x1={zone.cx - zone.r}
                        y1={zone.cy}
                        x2={zone.cx + zone.r}
                        y2={zone.cy}
                        className="controller-zone__crosshair"
                        pointerEvents="none"
                      />
                      <line
                        x1={zone.cx}
                        y1={zone.cy - zone.r}
                        x2={zone.cx}
                        y2={zone.cy + zone.r}
                        className="controller-zone__crosshair"
                        pointerEvents="none"
                      />
                    </>
                  )}
                  <text
                    x={zone.cx}
                    y={zone.cy}
                    className="controller-zone__label"
                    textAnchor="middle"
                    dominantBaseline="central"
                    pointerEvents="none"
                  >
                    {showAllZones ? zone.id : zone.label}
                  </text>
                  {showAllZones && (
                    <text
                      x={zone.cx}
                      y={zone.cy + zone.r + 10}
                      className="controller-zone__coords"
                      textAnchor="middle"
                      pointerEvents="none"
                    >
                      {`${zone.cx}, ${zone.cy} r${zone.r}`}
                    </text>
                  )}
                </>
              )}
              {isMapped && (
                <title>{`${zone.label} → ${mappings[zone.id]}`}</title>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
