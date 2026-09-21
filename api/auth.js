// Finclator panel access: email registration → owner approval → magic-link sign-in → signed session cookie.
//
// Users live in one private Vercel Blob (users.json). Tokens are HMAC-SHA256 over "purpose|email|exp" with
// SESSION_SECRET, so nothing but the user list needs storage. Endpoints (rewritten from /auth/<action>):
//   POST /auth/request   {email}         → registers or re-requests; mails the owner an approve link; mails the user a receipt
//   GET  /auth/approve   ?t=<token>      → owner-only link from the approval mail; marks approved, mails the user a sign-in link
//   GET  /auth/deny      ?t=<token>      → owner-only; marks denied
//   POST /auth/login     {email}         → approved user asks for a fresh sign-in link
//   GET  /auth/verify    ?t=<token>      → consumes a sign-in link, sets the session cookie, redirects to /panel
//   GET  /auth/logout                    → clears cookie
//   GET  /auth/me                        → {email, role} or 401 (used by the panel gate and the nav)
//   GET  /auth/users                     → owner-only JSON of all users
// Env: SESSION_SECRET, OWNER_EMAIL, RESEND_API_KEY, MAIL_FROM (e.g. "Finclator <panel@finclator.com>"),
//      SITE_URL (https://finclator.com), BLOB_READ_WRITE_TOKEN (set by the Blob store link).
import { createHmac, timingSafeEqual } from "node:crypto";
import { get, put } from "@vercel/blob";
import { Resend } from "resend";

const SECRET = process.env.SESSION_SECRET || "";
const OWNER = (process.env.OWNER_EMAIL || "").toLowerCase();
const SITE = (process.env.SITE_URL || "https://finclator.com").replace(/\/$/, "");
const FROM = process.env.MAIL_FROM || "Finclator <onboarding@resend.dev>";
const USERS_KEY = "users.json";
const SESSION_DAYS = 30;
const LINK_MINUTES = 30;
const APPROVE_DAYS = 14;

const json = (res, code, body, extra = {}) => {
  res.statusCode = code;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  for (const [k, v] of Object.entries(extra)) res.setHeader(k, v);
  res.end(JSON.stringify(body));
};
const redirect = (res, to, extra = {}) => {
  res.statusCode = 302;
  res.setHeader("Location", to);
  res.setHeader("Cache-Control", "no-store");
  for (const [k, v] of Object.entries(extra)) res.setHeader(k, v);
  res.end();
};
const b64 = (s) => Buffer.from(s).toString("base64url");
const unb64 = (s) => Buffer.from(s, "base64url").toString();
const sign = (s) => createHmac("sha256", SECRET).update(s).digest("base64url");
const safeEq = (a, b) => a.length === b.length && timingSafeEqual(Buffer.from(a), Buffer.from(b));

function makeToken(purpose, email, ttlMs) {
  const payload = `${purpose}|${email}|${Date.now() + ttlMs}`;
  return `${b64(payload)}.${sign(payload)}`;
}
function readToken(token, purpose) {
  if (!token || !token.includes(".")) return null;
  const [p, sig] = token.split(".");
  let payload;
  try { payload = unb64(p); } catch { return null; }
  if (!safeEq(sign(payload), sig)) return null;
  const [pur, email, exp] = payload.split("|");
  if (pur !== purpose || Number(exp) < Date.now()) return null;
  return email;
}

const cookieOf = (req) => Object.fromEntries((req.headers.cookie || "").split(";").map((c) => c.trim().split("=").map(decodeURIComponent)).filter((kv) => kv[0]));
const sessionCookie = (token) => `fc_session=${encodeURIComponent(token)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${SESSION_DAYS * 86400}`;
const clearCookie = () => "fc_session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0";

export function sessionEmail(req) {
  return readToken(cookieOf(req).fc_session, "session");
}

async function loadUsers() {
  try {
    const r = await get(USERS_KEY, { access: "private", useCache: false });
    if (!r || !r.stream) return {};
    return JSON.parse(await new Response(r.stream).text()) || {};
  } catch {
    return {};
  }
}
const saveUsers = (u) => put(USERS_KEY, JSON.stringify(u, null, 1), { access: "private", addRandomSuffix: false, allowOverwrite: true, contentType: "application/json" });

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const normEmail = (e) => String(e || "").trim().toLowerCase();

async function mail(to, subject, html) {
  if (!process.env.RESEND_API_KEY) throw new Error("RESEND_API_KEY not set");
  const resend = new Resend(process.env.RESEND_API_KEY);
  const r = await resend.emails.send({ from: FROM, to, subject, html });
  if (r.error) throw new Error(r.error.message || "mail failed");
}
const shell = (title, body) => `<!doctype html><body style="font:16px/1.5 -apple-system,Segoe UI,sans-serif;color:#1a1a1a;max-width:520px;margin:32px auto;padding:0 20px">
<p style="font-weight:600;letter-spacing:.02em;color:#6b6b6b;font-size:13px">FINCLATOR</p><h2 style="font-size:20px;margin:0 0 12px">${title}</h2>${body}
<p style="color:#8a8a8a;font-size:13px;margin-top:28px">You are receiving this because an access request was made for the Finclator panel with this address. If that was not you, ignore this message.</p></body>`;
const btn = (href, label) => `<p style="margin:20px 0"><a href="${href}" style="background:#1a1a1a;color:#fff;text-decoration:none;padding:11px 18px;border-radius:6px;display:inline-block;font-weight:600">${label}</a></p><p style="font-size:13px;color:#8a8a8a;word-break:break-all">${href}</p>`;

async function readBody(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks).toString();
  try { return JSON.parse(raw || "{}"); } catch { return Object.fromEntries(new URLSearchParams(raw)); }
}

export default async function handler(req, res) {
  if (!SECRET || !OWNER) return json(res, 500, { error: "server not configured (SESSION_SECRET / OWNER_EMAIL)" });
  const url = new URL(req.url, SITE);
  const action = url.searchParams.get("action") || url.pathname.split("/").pop();
  const now = new Date().toISOString();

  try {
    if (action === "me") {
      const email = sessionEmail(req);
      if (!email) return json(res, 401, { error: "not signed in" });
      const users = await loadUsers();
      const u = users[email];
      if (email !== OWNER && (!u || u.status !== "approved")) return json(res, 403, { error: "not approved" }, { "Set-Cookie": clearCookie() });
      return json(res, 200, { email, role: email === OWNER ? "owner" : "member" });
    }

    if (action === "logout") return redirect(res, "/", { "Set-Cookie": clearCookie() });

    if (action === "request" && req.method === "POST") {
      const { email: raw, name = "", note = "" } = await readBody(req);
      const email = normEmail(raw);
      if (!EMAIL_RE.test(email)) return json(res, 400, { error: "That doesn't look like an email address." });
      const users = await loadUsers();
      const existing = users[email];
      if (email === OWNER || (existing && existing.status === "approved")) {
        // already in: just send a sign-in link
        await mail(email, "Your Finclator sign-in link", shell("Sign in to the panel",
          `<p>This link signs you in for ${SESSION_DAYS} days on this device. It expires in ${LINK_MINUTES} minutes.</p>` +
          btn(`${SITE}/auth/verify?t=${makeToken("login", email, LINK_MINUTES * 60e3)}`, "Sign in")));
        return json(res, 200, { status: "approved", message: "You already have access — a sign-in link is on its way." });
      }
      if (existing && existing.status === "denied") return json(res, 200, { status: "pending", message: "Request received. You'll get an email if access is granted." });
      users[email] = { email, name: String(name).slice(0, 80), note: String(note).slice(0, 300), status: "pending",
        requested_at: existing?.requested_at || now, requests: (existing?.requests || 0) + 1 };
      await saveUsers(users);
      const approve = `${SITE}/auth/approve?t=${makeToken("approve", email, APPROVE_DAYS * 864e5)}`;
      const deny = `${SITE}/auth/deny?t=${makeToken("deny", email, APPROVE_DAYS * 864e5)}`;
      await mail(OWNER, `Finclator access request: ${email}`, shell("Someone wants in",
        `<p><b>${email}</b>${name ? ` (${String(name).replace(/[<>]/g, "")})` : ""}</p>` +
        (note ? `<p style="white-space:pre-wrap;background:#f4f4f4;padding:10px 12px;border-radius:6px">${String(note).replace(/[<>]/g, "")}</p>` : "") +
        btn(approve, "Approve") + `<p><a href="${deny}" style="color:#8a8a8a">Deny</a></p>`));
      await mail(email, "Finclator: request received", shell("Request received",
        `<p>Thanks — access to the Finclator panel is granted by hand. You'll get a sign-in link by email once it's approved.</p>`));
      return json(res, 200, { status: "pending", message: "Request received. You'll get an email once it's approved." });
    }

    if (action === "login" && req.method === "POST") {
      const { email: raw } = await readBody(req);
      const email = normEmail(raw);
      if (!EMAIL_RE.test(email)) return json(res, 400, { error: "That doesn't look like an email address." });
      const users = await loadUsers();
      const ok = email === OWNER || users[email]?.status === "approved";
      if (ok) {
        await mail(email, "Your Finclator sign-in link", shell("Sign in to the panel",
          `<p>This link signs you in for ${SESSION_DAYS} days on this device. It expires in ${LINK_MINUTES} minutes.</p>` +
          btn(`${SITE}/auth/verify?t=${makeToken("login", email, LINK_MINUTES * 60e3)}`, "Sign in")));
      }
      // same answer either way: never reveal who is on the list
      return json(res, 200, { message: "If that address has access, a sign-in link is on its way." });
    }

    if (action === "approve" || action === "deny") {
      const email = readToken(url.searchParams.get("t"), action);
      if (!email) return json(res, 400, { error: "This link is invalid or has expired." });
      const users = await loadUsers();
      users[email] = { ...(users[email] || { email }), status: action === "approve" ? "approved" : "denied", decided_at: now };
      await saveUsers(users);
      if (action === "approve") {
        await mail(email, "Finclator: access granted", shell("You're in",
          `<p>Your access to the Finclator panel was approved. Sign in with the link below (valid ${LINK_MINUTES} minutes); afterwards you can request a fresh link any time from <a href="${SITE}/login">${SITE.replace("https://", "")}/login</a>.</p>` +
          btn(`${SITE}/auth/verify?t=${makeToken("login", email, LINK_MINUTES * 60e3)}`, "Sign in")));
      }
      res.statusCode = 200;
      res.setHeader("Content-Type", "text/html; charset=utf-8");
      return res.end(shell(action === "approve" ? "Approved" : "Denied", `<p><b>${email}</b> is now <b>${action === "approve" ? "approved" : "denied"}</b>.</p><p><a href="${SITE}/panel">Open the panel</a></p>`));
    }

    if (action === "verify") {
      const email = readToken(url.searchParams.get("t"), "login");
      if (!email) return redirect(res, "/login?e=expired");
      const users = await loadUsers();
      if (email !== OWNER && users[email]?.status !== "approved") return redirect(res, "/login?e=denied");
      if (users[email]) { users[email].last_login = now; await saveUsers(users); }
      return redirect(res, "/panel", { "Set-Cookie": sessionCookie(makeToken("session", email, SESSION_DAYS * 864e5)) });
    }

    if (action === "users") {
      if (sessionEmail(req) !== OWNER) return json(res, 403, { error: "owner only" });
      return json(res, 200, await loadUsers());
    }

    return json(res, 404, { error: "unknown action" });
  } catch (err) {
    console.error(action, err);
    return json(res, 500, { error: err.message || "server error" });
  }
}
