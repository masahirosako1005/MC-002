import { useId } from 'react';

/** Original keepsakes: their shape stays visible before acquisition; text conveys status. */
export function TrophyArt({ motif, earned = false }: { motif: string; earned?: boolean }) {
  const uid = useId().replaceAll(':', '');
  const seasonal = ['spring', 'summer', 'autumn', 'winter'].includes(motif);
  const accent =
    motif === 'spring' || motif === 'sakura'
      ? '#bd7b83'
      : motif === 'autumn'
        ? '#ad5a3b'
        : motif === 'winter'
          ? '#699aa5'
          : '#5d8a78';
  return (
    <svg
      className={`trophy-art ${earned ? 'is-earned' : 'is-waiting'}`}
      viewBox="0 0 180 180"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient
          id={`${uid}-brass`}
          x1="40"
          y1="20"
          x2="135"
          y2="160"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#e9d9a9" />
          <stop offset=".5" stopColor="#b18b4e" />
          <stop offset="1" stopColor="#e0c38b" />
        </linearGradient>
        <linearGradient
          id={`${uid}-glass`}
          x1="50"
          y1="35"
          x2="120"
          y2="150"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#e7f1e9" />
          <stop offset="1" stopColor="#7ba6a2" />
        </linearGradient>
      </defs>
      <ellipse cx="90" cy="155" rx="47" ry="7" fill="#5f6657" opacity=".12" />
      <g stroke="#405e55" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {(motif === 'watergate' || motif === 'mastery') && (
          <>
            {motif === 'mastery' && (
              <>
                <circle cx="91" cy="48" r="28" stroke="#b08d53" strokeWidth="5" />
                <path d="m99 68 31 69 13-6-6-13-9 4-5-10 9-4-16-37" fill={`url(#${uid}-brass)`} />
                <path d="m76 69-26 64 13 6 7-15-8-4 5-10 8 3 16-38" fill={`url(#${uid}-brass)`} />
              </>
            )}
            <path
              d="M89 26c-19 0-31 13-31 29 0 14 9 25 23 29v62h23v-13H94v-13h12v-13H94V84c14-3 24-15 24-29 0-17-12-29-29-29Z"
              fill={`url(#${uid}-brass)`}
            />
            <path d="M77 47h24v22H77zM72 44h34M84 44v25m10-25v25" />
            <path d="M86 91v44" stroke="#f2e7c7" />
          </>
        )}
        {motif === 'sakura' && (
          <>
            <path
              d="M89 43c-31-18-21-38-7-25 13-14 25-1 8 25m0 0c28-18 42-3 20 8"
              stroke="#a9676d"
            />
            <path d="m58 52 32-12 32 12 11 91q-43 19-86 0Z" fill="#dfb7ad" />
            <path d="m60 61 30-10 30 10 7 75q-37 14-74 0Z" stroke="#f5e7cc" strokeWidth="3" />
            <path
              d="M90 104c-28-7-20-30-4-16-4-25 22-25 16-3 23-11 31 13 8 17 14 18-7 29-17 11-13 20-31 2-13-9Z"
              fill="#f6e9cc"
              stroke="#ae7774"
            />
            <circle cx="94" cy="101" r="4" fill="#b48a4d" />
          </>
        )}
        {motif === 'coast' && (
          <>
            <path
              d="M89 141C26 119 29 72 47 63c0-22 27-32 42-16 17-15 43-5 44 16 21 8 24 57-44 78Z"
              fill="#dfc49d"
            />
            <path d="M89 140 48 67m41 73L67 53m22 87V47m0 93 22-87m-22 87 43-73" stroke="#a48760" />
            <path d="m75 143 14-4 15 4-6 10H81Z" fill="#f1e1c4" />
            <path d="M56 85q10-5 15 0m31 11q10-5 17 0" stroke="#f7edda" strokeWidth="4" />
          </>
        )}
        {(motif === 'conference' || motif === 'conference-detour') && (
          <>
            <path d="m36 47 103-8 7 100-103 8Z" fill="#f2e5c7" />
            <path d="m45 57 85-7 6 81-85 7Z" stroke="#b7975e" />
            <path
              d="m65 95 23-23 25 19M69 94v24l42-4V91M79 96v12m20-14v12m-10-17v26"
              stroke="#627d70"
              strokeWidth="3"
            />
            <path d="m62 64 54-4" stroke="#bc9060" />
            {motif === 'conference-detour' && (
              <>
                <path d="M91 129q22 27 48-4" stroke="#aa573e" strokeWidth="4" />
                <path d="m127 124 13-3-3 13" stroke="#aa573e" strokeWidth="4" />
              </>
            )}
          </>
        )}
        {seasonal && (
          <>
            <path d="M68 27h44v18l13 16v77q-35 17-70 0V61l13-16Z" fill={`url(#${uid}-glass)`} />
            <path d="M66 25h48v13H66Z" fill={`url(#${uid}-brass)`} />
            <path
              d="M56 112q19-12 35 0t33 0v25q-34 16-68 0Z"
              fill={accent}
              opacity=".65"
              stroke="none"
            />
            <path d="M65 120q22-9 47 0m-47 10q23-9 47 0" stroke="#f0f0d8" />
            <path d="M64 68v35" stroke="#f8f4df" strokeWidth="5" />
            {motif === 'spring' && (
              <path
                d="M91 82c-23-9-10-27 0-11 10-16 23 2 0 11 23 9 10 27 0 11-10 16-23-2 0-11Z"
                fill="#dab0b4"
                stroke="#9c6b76"
              />
            )}
            {motif === 'summer' && (
              <>
                <circle cx="91" cy="83" r="14" fill="#d6b15f" />
                <path
                  d="M91 61v6m0 32v6M69 83h6m32 0h6m-38-16 5 5m23 23 5 5m0-33-5 5m-23 23-5 5"
                  stroke="#b68e45"
                />
              </>
            )}
            {motif === 'autumn' && (
              <path
                d="m91 60 6 16 14-7-6 16 10 8-18 2-6 13-4-13-18-2 10-8-6-16 14 7Z"
                fill="#be7654"
                stroke="#9e573e"
              />
            )}
            {motif === 'winter' && (
              <>
                <path d="M80 69h24l4 31H76Z" fill="#e3cf93" />
                <path d="M92 63v40m-13-26h26M78 94h28" stroke="#a58754" />
                <path d="m113 58 3 5-3 5-3-5z" fill="#f5f0dc" />
              </>
            )}
          </>
        )}
        {motif === 'return' && (
          <>
            <path d="M37 130V98q53-68 106 0v32H37Z" fill="#cfb88a" />
            <path d="M57 130v-23q33-42 66 0v23" fill="#8cad9d" />
            <path
              d="M36 98q54-66 108 0M45 89v22m18-39v27m18-35v26m18-26v26m18-18v27m18-10v22"
              stroke="#786c50"
              strokeWidth="3"
            />
            <path d="M32 139q22-10 42 0t42 0t33 0" stroke="#618e92" />
            <path d="M58 47q31-26 60 1m-3-13 7 17-19-2" stroke="#ad6545" strokeWidth="3" />
          </>
        )}
        {motif === 'coast-seasons' && (
          <>
            <path d="m46 41 85-6 8 108-85 6Z" fill="#426d69" />
            <path d="m58 40 7 107" stroke="#d0b77e" strokeWidth="3" />
            <path d="m72 58 45-3 4 64-45 3Z" fill="#e9dfc2" />
            <circle cx="91" cy="76" r="9" fill="#caab66" stroke="none" />
            <path
              d="M77 96q10-10 21-1t21 0m-40 12q10-10 20-1t20 0"
              stroke="#5e969a"
              strokeWidth="3"
            />
            <path d="m102 141 2 18 7-5 8 4-2-18" fill="#bc7053" />
          </>
        )}
      </g>
      {earned && (
        <g fill="#b5914b">
          <path d="m143 42 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z" />
          <circle cx="38" cy="56" r="2" />
        </g>
      )}
    </svg>
  );
}
