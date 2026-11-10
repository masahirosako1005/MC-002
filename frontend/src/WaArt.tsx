import type { ReactNode } from "react";

export function WoodcutArt({ priority = false }: { priority?: boolean }) {
  return (
    <img
      className="wa-woodcut-art"
      src="/art/wa/travel-woodcut-v1-480.webp"
      srcSet="/art/wa/travel-woodcut-v1-480.webp 480w, /art/wa/travel-woodcut-v1-960.webp 960w"
      sizes="(max-width: 450px) 360px, 430px"
      width={960}
      height={640}
      alt=""
      loading={priority ? "eager" : "lazy"}
      decoding="async"
    />
  );
}

/** Local vector ornaments; labels remain real text and respond to text zoom. */
export function ScrollHeading({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`wa-scroll-heading ${className}`}>
      <svg
        className="wa-scroll-outline"
        viewBox="0 0 300 66"
        preserveAspectRatio="none"
        aria-hidden="true"
        focusable="false"
      >
        <path
          className="wa-scroll-paper"
          d="M15 9Q83 5 151 9T285 8L285 57Q211 61 148 57T15 58Z"
        />
        <path
          className="wa-scroll-fold"
          d="M19 13Q99 9 151 13T280 12M19 54Q90 51 150 54T280 53"
        />
        <path className="wa-scroll-rod" d="M11 5V61M289 5V61" />
        <path
          className="wa-scroll-cap"
          d="M7 4H15V10H7ZM7 56H15V62H7ZM285 4H293V10H285ZM285 56H293V62H285Z"
        />
        <path className="wa-scroll-seam" d="M15 9V58M285 8V57" />
      </svg>
      {children}
    </div>
  );
}

export function SealMark({
  children,
  className = "",
  decorative = false,
}: {
  children: ReactNode;
  className?: string;
  decorative?: boolean;
}) {
  return (
    <span
      className={`wa-seal ${className}`}
      aria-hidden={decorative || undefined}
    >
      <svg
        viewBox="0 0 60 64"
        preserveAspectRatio="none"
        aria-hidden="true"
        focusable="false"
      >
        <path d="M5 4 55 3 57 59 5 61 3 12Z" />
        <path d="M9 9 50 8 52 55 10 56 8 17M13 5 42 4M5 48 6 58M56 13 57 42" />
      </svg>
      <span>{children}</span>
    </span>
  );
}

export function JourneyDrawing({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`wa-journey-drawing ${className}`}
      viewBox="0 0 180 110"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M11 84 53 30 68 47 87 14 148 84M38 48 48 46 53 30 60 44 66 45M72 38 83 36 87 14 99 39 108 43M5 88Q31 81 59 87T119 87T174 88M3 95Q45 89 75 96T175 96" />
      <path d="M106 106Q135 94 110 83T119 64M136 72V38M123 49l13-12 14 12M126 59l10-11 12 10M20 75V59M13 66l7-8 8 8" />
      <circle cx="37" cy="20" r="9" />
      <path d="M34 2v3M19 20h3M49 7l-2 3M52 19h4" />
    </svg>
  );
}

/** An original bird-and-path emblem, unrelated to shrine seals or sacred text. */
export function TravelCrest({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`wa-travel-crest ${className}`}
      viewBox="0 0 92 100"
      aria-hidden="true"
      focusable="false"
    >
      <path
        className="crest-border"
        d="M5 5 86 3 88 94 6 96ZM10 10 81 9 82 88 11 90Z"
      />
      <path
        className="crest-bird"
        d="M44 30Q29 10 15 18L31 29 18 31Q32 39 45 34L52 39 51 29 59 25 50 24Q44 20 44 30ZM62 52Q68 35 81 38L73 48 83 50Q72 56 64 57L57 63 56 55 50 52 58 50Q61 46 62 52ZM30 70Q16 55 10 64L20 72 12 76Q25 78 31 75L38 81 38 71 44 68 36 67Q31 64 30 70Z"
      />
      <path className="crest-road" d="M45 88Q66 73 46 62T43 43Q32 35 39 15" />
      <path
        className="crest-mark"
        d="m63 75 12-1 1 12-12 1ZM67 78l5 5m0-5-5 5"
      />
    </svg>
  );
}
