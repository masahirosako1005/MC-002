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

export function Scene({ kind = 'gate', className = '' }: { kind?: SpotKind; className?: string }) {
  return (
    <svg
      className={`scene scene-${kind} ${className}`}
      viewBox="0 0 420 280"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="314" cy="72" r="34" fill="#d5aa70" opacity=".55" />
      <path d="M0 175 65 114 115 150 196 91 272 155 340 111 420 171V280H0Z" fill="#c7cec0" />
      <path d="M0 189 91 158 170 187 277 144 420 184v96H0Z" fill="#a7b8aa" />
      <path d="M0 215c89-22 138 29 216 7 90-26 156-8 204 16v42H0Z" fill="#608e90" />
      {[235, 250, 266].map((y, i) => (
        <path
          key={y}
          d={`M${20 + i * 7} ${y}q50-9 100 0t100 0t100 0t100 0`}
          stroke="#d7e1d6"
          opacity=".7"
        />
      ))}
      {kind === 'gate' && (
        <>
          <path d="m57 214 294-14 8 16-304 14Z" fill="#e0d9c4" />
          <path d="M114 206V90h17v116m164-7V90h17v109" fill="#263f42" />
          <path d="M101 97h221v12H101zM110 81h202v10H110z" fill="#354c48" />
          <path d="M135 115h157v70H135z" fill="#476762" />
          <path
            d="M140 120h147m-147 14h147m-147 14h147m-147 14h147m-147 14h147"
            stroke="#829387"
            strokeWidth="2"
          />
          <path d="M202 59h15v145h-15z" fill="#d8c8a3" />
          <circle cx="210" cy="65" r="20" stroke="#263f42" strokeWidth="5" />
          <path d="M210 45v40m-20-20h40" stroke="#263f42" strokeWidth="3" />
          <path
            d="M150 199v27m34-26v25m44-25v23m37-22v22"
            stroke="#b9d0c5"
            strokeWidth="8"
            opacity=".7"
          />
        </>
      )}
      {kind === 'shrine' && (
        <>
          <path d="m160 280 35-106h24l59 106" fill="#e2d5b9" />
          <path d="M133 104h12v123h-12m143-123h12v123h-12" fill="#a54e38" />
          <path d="M115 91q96 19 194 0l-3 15q-94 15-188 0ZM122 127h178v10H122Z" fill="#a54e38" />
          <path d="M192 108v21h9v-20m27-1v21h9v-20" fill="#a54e38" />
          <path d="M210 118v28m-7-5 7 7 7-7" stroke="#d8c7a1" strokeWidth="3" />
          <path d="M43 218V92m16 126V75m281 151V93m20 136V72" stroke="#405b49" strokeWidth="10" />
          <path
            d="M10 127 43 58l33 69Zm27-23L60 37l31 77Zm275 34 29-83 33 83Zm21-23 28-81 37 81Z"
            fill="#55715a"
          />
        </>
      )}
      {kind === 'coast' && (
        <>
          <path d="M0 216c120-43 106 25 199 28 79 3 124-8 221 23v13H0Z" fill="#e0cfab" />
          <path d="m270 222 20-12 54 2-22 12z" fill="#aa5139" />
          <path d="M296 211v-80l-41 64h40" fill="#f3e9ce" />
          <path d="M300 141v55h35z" fill="#d7b989" />
          <path
            d="m89 235 19-30m-6 35 15-27m-23 22-17-17m29 18 20-17"
            stroke="#6c8063"
            strokeWidth="3"
          />
          <path d="m46 252 12-12 13 12m79 12 6-9 10 9" stroke="#b19f7d" strokeWidth="2" />
        </>
      )}
      {kind === 'conference' && (
        <>
          <path d="M92 215V119l120-49 118 49v96z" fill="#e6dfc9" />
          <path d="m78 123 134-60 134 60" stroke="#3d5653" strokeWidth="8" />
          {[111, 151, 231, 271].map((x) => (
            <path key={x} d={`M${x} 134h24v53h-24z`} fill="#6e928f" />
          ))}
          <path d="M193 134h37v81h-37z" fill="#405f5e" />
          <path d="M81 215h263v10H81z" fill="#d7ccb5" />
        </>
      )}
      <path d="m30 60 8-3 6 8m227-39 9-3 6 7m-52 12 7-2 5 5" stroke="#6b7969" strokeWidth="2" />
      <path d="m348 179 12-20 8 13 12-2-7 16 10 9-17 2-5 17-8-17-18-3 13-8Z" fill="#b86644" />
      <path d="m63 177 8-13 5 8 8-1-5 10 7 6-11 1-4 11-5-11-11-2 8-5Z" fill="#c4884c" />
    </svg>
  );
}

export function CityMap() {
  return (
    <svg
      className="city-map"
      viewBox="0 0 580 260"
      role="img"
      aria-label="街の見取り図。会議場から水門へ、北に桜社、東に四季の海があります。経路案内ではありません。"
    >
      <rect width="580" height="260" fill="#ebe8dc" />
      <path
        d="M0 44q121 90 214 40T580 64M0 188q95-72 218-23t362 11"
        fill="none"
        stroke="#dbd7c9"
        strokeWidth="16"
      />
      <path
        d="M139-20q-24 94 76 173t66 130M380-10q-89 148 14 290"
        fill="none"
        stroke="#faf7ed"
        strokeWidth="13"
      />
      <path d="M401-20q-38 100 39 163t49 140h91V-20Z" fill="#b4cdca" />
      <path d="M413 0q-37 98 42 155t42 105" fill="none" stroke="#8eb6b5" strokeWidth="2" />
      <path
        d="M127 197 244 124 295 58M244 124l217 63"
        fill="none"
        stroke="#bb674e"
        strokeWidth="2"
        strokeDasharray="4 6"
      />
      <g fill="#c7cfba">
        <ellipse cx="298" cy="42" rx="42" ry="23" />
        <ellipse cx="76" cy="88" rx="51" ry="29" />
        <ellipse cx="349" cy="208" rx="44" ry="25" />
      </g>
      <g fill="#193c44" stroke="#f9f6eb" strokeWidth="3">
        <circle cx="127" cy="197" r="7" />
        <circle cx="244" cy="124" r="7" />
        <circle cx="295" cy="58" r="7" />
        <circle cx="461" cy="187" r="7" />
      </g>
      <g fill="#264646" fontSize="13" fontFamily="sans-serif">
        <text x="72" y="227">
          国際会議場
        </text>
        <text x="207" y="105">
          水門
        </text>
        <text x="313" y="63">
          桜社
        </text>
        <text x="477" y="193">
          四季の海
        </text>
        <text x="26" y="29" fontSize="10" letterSpacing="3">
          街の見取り図
        </text>
      </g>
      <path d="m546 23-5 13h10z" fill="#264646" />
      <text x="542" y="18" fill="#264646" fontSize="9">
        N
      </text>
    </svg>
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
