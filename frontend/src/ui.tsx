import type { ReactNode } from 'react';
import type { Season, SpotKind } from './types';

export type IconName =
  | 'book'
  | 'bookmark'
  | 'compass'
  | 'arrow'
  | 'back'
  | 'check'
  | 'close'
  | 'clock'
  | 'trophy'
  | 'trash'
  | 'plus'
  | 'minus'
  | 'hint'
  | 'gate'
  | 'shrine'
  | 'coast'
  | 'conference'
  | 'leaf';
const paths: Record<IconName, ReactNode> = {
  book: (
    <>
      <path d="M3 4h6c2 0 3 1 3 3 0-2 1-3 3-3h6v16h-6c-2 0-3 1-3 1s-1-1-3-1H3z" />
      <path d="M12 7v14" />
    </>
  ),
  bookmark: <path d="M6 3h12v18l-6-4-6 4z" />,
  compass: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m16 8-3 5-5 3 3-5z" />
    </>
  ),
  arrow: <path d="M4 12h15m-5-5 5 5-5 5" />,
  back: <path d="M20 12H5m5-5-5 5 5 5" />,
  check: <path d="m5 12 4 4L19 6" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 6v6l4 2" />
    </>
  ),
  trophy: (
    <>
      <path d="M7 3h10v7a5 5 0 0 1-10 0zM7 5H3v3c0 3 2 4 5 4m9-7h4v3c0 3-2 4-5 4M12 15v6m-4 0h8" />
    </>
  ),
  trash: (
    <>
      <path d="M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7" />
    </>
  ),
  plus: <path d="M5 12h14M12 5v14" />,
  minus: <path d="M5 12h14" />,
  hint: (
    <>
      <path d="M9 18h6m-6 3h6M8 14a6 6 0 1 1 8 0l-1 2H9z" />
    </>
  ),
  gate: (
    <>
      <path d="M3 5h18M6 3v18m12-18v18M3 19h18M9 9h6v7H9zM12 5v4" />
    </>
  ),
  shrine: (
    <>
      <path d="M3 4q9 4 18 0M4 9h16M7 6v15m10-15v15M10 8V6m4 2V6" />
    </>
  ),
  coast: (
    <>
      <path d="M2 13q3-5 7 0t7 0q3-5 6 0M2 19q3-5 7 0t7 0q3-5 6 0" />
      <circle cx="16" cy="5" r="2" />
    </>
  ),
  conference: (
    <>
      <path d="M4 21V8l8-5 8 5v13M2 21h20M8 10v2m4-2v2m4-2v2M8 16v2m8-2v2m-4-2v5" />
    </>
  ),
  leaf: (
    <>
      <path d="M19 3C3 2 1 17 10 18c9 1 9-10 9-15zM5 21l10-12" />
    </>
  ),
};
export function Icon({ name, className = '' }: { name: IconName; className?: string }) {
  return (
    <svg
      className={`icon ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

export function Scene({
  kind = 'gate',
  season,
  className = '',
  priority = false,
  sizes = '(max-width: 760px) 100vw, 700px',
}: {
  kind?: SpotKind;
  season: Season;
  className?: string;
  priority?: boolean;
  sizes?: string;
}) {
  const source = kind === 'gate' ? `scene-gate-${season}-v2` : `scene-${kind}-v2`;
  return (
    <img
      className={`scene scene-${kind} scene-season-${season} ${className}`}
      src={`/art/${source}.webp`}
      srcSet={`/art/${source}-small.webp 640w, /art/${source}.webp 1280w`}
      sizes={sizes}
      alt=""
      width="1536"
      height="1024"
      loading={priority ? 'eager' : 'lazy'}
      fetchPriority={priority ? 'high' : 'auto'}
      decoding="async"
      draggable={false}
    />
  );
}

export function CityMap() {
  return (
    <div
      className="city-map"
      role="img"
      aria-label="街の見取り図。会議場から水門へ、北に桜社、東に四季の海があります。経路案内ではありません。"
    >
      <img
        className="city-overview"
        src="/art/city-overview-v2.webp"
        srcSet="/art/city-overview-v2-small.webp 640w, /art/city-overview-v2.webp 1280w"
        sizes="(max-width: 760px) 100vw, 700px"
        alt=""
        width="1448"
        height="1086"
        loading="lazy"
        decoding="async"
        draggable={false}
      />
      <svg className="city-connections" viewBox="0 0 580 435" fill="none" aria-hidden="true">
        <path d="M128 331 244 209 296 96M244 209l220 104" stroke="#f7f3e8" strokeWidth="7" />
        <path
          d="M128 331 244 209 296 96M244 209l220 104"
          stroke="#9b4935"
          strokeWidth="2"
          strokeDasharray="5 7"
        />
      </svg>
      <span className="city-map-caption" aria-hidden="true">
        街の見取り図
      </span>
      <span className="city-north" aria-hidden="true">
        ↑ N
      </span>
      <span className="city-location city-location-conference" aria-hidden="true">
        <Icon name="conference" />
        国際会議場
      </span>
      <span className="city-location city-location-gate" aria-hidden="true">
        <Icon name="gate" />
        水門
      </span>
      <span className="city-location city-location-shrine" aria-hidden="true">
        <Icon name="shrine" />
        桜社
      </span>
      <span className="city-location city-location-coast" aria-hidden="true">
        <Icon name="coast" />
        四季の海
      </span>
    </div>
  );
}
export function SeasonSeal({
  season,
  earned = false,
}: {
  season: Season | 'all';
  earned?: boolean;
}) {
  const symbols: Record<Season | 'all', ReactNode> = {
    all: (
      <>
        <path d="M14 20q18 7 36 0M17 30h30M23 24v28m18-28v28M28 25v5m8-5v5" />
      </>
    ),
    spring: (
      <>
        <path d="M32 32c-24-9-8-30 0-14 8-16 24 5 0 14 24 9 8 30 0 14-8 16-24-5 0-14Z" />
        <circle cx="32" cy="32" r="4" />
      </>
    ),
    summer: (
      <>
        <circle cx="32" cy="32" r="10" />
        <path d="M32 12v7m0 26v7M12 32h7m26 0h7M18 18l5 5m18 18 5 5M18 46l5-5m18-18 5-5" />
      </>
    ),
    autumn: (
      <>
        <path d="m32 12 6 14 12-6-6 14 9 7-16 1-5 12-4-12-16-1 9-7-7-14 13 6zM32 28v23" />
      </>
    ),
    winter: (
      <>
        <path d="M32 12v40M15 22l34 20M15 42l34-20M27 16l5 5 5-5m-10 32 5-5 5 5M16 28l7-1-2-7m22 24-2-7 7-1M16 36l7 1-2 7m22-24-2 7 7 1" />
      </>
    ),
  };
  return (
    <svg
      className={`season-seal ${earned ? 'earned' : ''} season-${season}`}
      viewBox="0 0 64 64"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <circle cx="32" cy="32" r="29" />
      <circle cx="32" cy="32" r="25" strokeDasharray="1 3" />
      {symbols[season]}
    </svg>
  );
}

export function ErrorNotice({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="error-notice" role="alert">
      <p>{message}</p>
      {retry && (
        <button className="text-button" onClick={retry}>
          もう一度読み込む <Icon name="arrow" />
        </button>
      )}
    </div>
  );
}

export function Empty({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <Icon name="book" />
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
