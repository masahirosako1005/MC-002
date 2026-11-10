/** Exceptions can be arbitrary values; never fail while rendering an error. */
export function errorMessage(cause: unknown): string {
  return cause instanceof Error && cause.message
    ? cause.message
    : "操作を完了できませんでした。もう一度お試しください。";
}

/** Match Python/Pydantic's Unicode code point count without changing the secret. */
export function passwordLength(value: string): number {
  return Array.from(value).length;
}

export function isOneOf<T extends string>(
  value: string,
  allowed: readonly T[],
): value is T {
  return allowed.some((item) => item === value);
}

export function choiceValue<const T extends string>(
  value: string,
  allowed: readonly T[],
  current: T,
): T {
  return isOneOf(value, allowed) ? value : current;
}
