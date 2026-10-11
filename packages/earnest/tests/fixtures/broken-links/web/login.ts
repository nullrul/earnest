// Sign-in messages for the auth service.

// [impl->req~lockout-notice~1]
export function notice(minutes: number): string {
  return `Try again in ${minutes} minutes.`;
}

/* [impl->req~audit-log~1] */
export function audit(member: string): string {
  return `${member} signed in.`;
}

// [impl->req~lockout-notice]
export function banner(): string {
  return "Too many attempts // wait a minute.";
}
